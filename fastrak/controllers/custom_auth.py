from odoo.http import request
from odoo.service import security
import base64
import odoo
import json
import werkzeug.wrappers
import traceback
import functools

import logging
import sys

logging.basicConfig(level=logging.DEBUG)
_logger = logging.getLogger(__name__)

# 2xx Success
CODE__success = 200
CODE__created = 201
CODE__accepted = 202
CODE__ok_no_content = 204
# 4xx Client Errors
CODE__server_rejects = (400, "Server rejected", "Welcome to macondo!")
CODE__invalid_auth_header = (401, "Invalid header", "Token auth header is not valid")
CODE__no_user_auth = (401, "Authentication", "Your token could not be authenticated.")
CODE__user_no_perm = (403, "Permissions", "%s")
CODE__method_blocked = (
    403,
    "Blocked Method",
    "This method is not whitelisted on this model.",
)

CODE__db_not_found = (404, "Db not found", "Welcome to macondo!")
CODE__canned_ctx_not_found = (
    404,
    "Canned context not found",
    "The requested canned context is not configured on this model",
)

CODE__obj_not_found = (
    404,
    "Object not found",
    "This object is not available on this instance.",
)

CODE__res_not_found = (404, "Resource not found", "There is no resource with this id.")
CODE__act_not_executed = (
    409,
    "Action not executed",
    "The requested action was not executed.",
)
# 5xx Server errors
CODE__invalid_method = (501, "Invalid Method", "This method is not implemented.")
CODE__invalid_spec = (
    501,
    "Invalid Field Spec",
    "The field spec supplied is not valid.",
)
# If API Workers are enforced, but non is available (switched off)
CODE__no_api_worker = (
    503,
    "API worker sleeping",
    "The API worker is currently not at work.",
)

DATABASE_NAME = 'fastrak_db'


def get_raise_exception_checker():
    # TODO: still needs env here
    env = {}
    res = False
    try:
        res = env['ir.config_parameter'].sudo().get_param('', False)
    except Exception as e:
        print("E: ", e)
        pass
    return res


class HTTPException(werkzeug.exceptions.HTTPException):
    raise_exception = get_raise_exception_checker()
    if not raise_exception:
        sys.tracebacklimit = 0


def error_response(status, error, error_description):
    """Error responses wrapper.
    :param int status: The error code.
    :param str error: The error summary.
    :param str error_description: The error description.
    :returns: The werkzeug `response object`_.
    :rtype: werkzeug.wrappers.Response
    .. _response object:
        http://werkzeug.pocoo.org/docs/0.14/wrappers/#module-werkzeug.wrappers
    """
    print("ERROR RESPONSE CALLED -*-*-*-*-*-*-*-")
    print(status, error, error_description)
    return werkzeug.wrappers.Response(
        status=status,
        content_type="application/json; charset=utf-8",
        response=json.dumps({"error": error, "error_description": error_description}),
    )


# Create openapi.log record
def create_log_record(**kwargs):
    # test_mode = request.registry.test_cr
    # don't create log in test mode as it's impossible in case of error in sql
    # request (we cannot use second cursor and we cannot use aborted
    # transaction)
    # if not test_mode:
    #     with odoo.registry(request.session.db).cursor() as cr:
    # use new to save data even in case of an error in the old cursor
    # env = odoo.api.Environment(cr, request.session.uid, {})
    return _create_log_record(**kwargs)


def _sanitize_headers(user_request, user_name=None):
    """
    Remove Authorization token from the headers to be displayed
    :param user_request:
    :return:
    """
    headers = ''
    try:
        for k, v in user_request.headers:
            if k == 'Authorization':
                if user_name:
                    headers += 'Auth User: {}\n'.format(user_name)
            else:
                headers += '{}: {}\n'.format(k, v)

    except Exception as e:
        headers = user_request.headers
    return headers


def _create_log_record(env, user_id=None, user_request=None, user_response=None, user_name=None):
    """create log for request

    :param int namespace_id: Requested namespace id.
    :param string namespace_log_request: Request save option.
    :param string namespace_log_response: Response save option.
    :param int user_id: User id which requests.
    :param user_request: a wrapped werkzeug Request object from user.
    :type user_request: :class:`werkzeug.wrappers.BaseRequest`
    :param user_response: a wrapped werkzeug Response object to user.
    :type user_response: :class:`werkzeug.wrappers.Response`

    :returns: New 'openapi.log' record.
    :rtype: ..models.openapi_log.Log
    """

    try:
        request_resource = user_request.path.split('/')[4]
    except Exception:
        request_resource = 'fastrak'

    log_data = {
        "request": "{} {}".format(user_request.url, user_request.method),
        "request_data": None,
        "response_data": None,
    }

    if user_request:
        headers = _sanitize_headers(user_request, user_name)

        log_data["request_data"] = user_request.__dict__
        log_data["request_resource"] = request_resource
        log_data["request_remote_address"] = user_request.remote_addr
        log_data["request_scheme"] = user_request.scheme
        log_data["request_path"] = user_request.path
        log_data["request_method"] = user_request.method
        log_data["request_headers"] = headers
        log_data["request_parameters"] = user_request.data

    if user_response:
        log_data["response_data"] = user_response
        log_data["response_code"] = user_response.get('code')
        log_data["response_msg"] = user_response.get('message')

    try:
        print("Writing to log")
        env["api.log"].create(log_data)
    except Exception as e:
        _logger.error("******** API LOG ERROR ******** \n{}\n******** END API LOG ERROR ********".format(e))
        print(e)

    return True


# User token auth (db-scoped)
def authenticate_token_for_user(token):
    """Authenticate against the database and setup user session corresponding to the token.

    :param str token: The raw access token.

    :returns: User if token is authorized for the requested user.
    :rtype odoo.models.Model

    :raise: HTTPException if user not found.
    """

    user = request.env["res.users"].sudo().search([("auth_token", "=", token)])

    if user.exists():
        # copy-pasted from odoo.http.py:OpenERPSession.authenticate()
        request.session.uid = user.id
        request.session.login = user.login

        request.session.session_token = user.id and security.compute_session_token(request.session, request.env)

        request.uid = user.id
        request.disable_db = False
        request.session.get_context()

        return user

    raise HTTPException(
        response=error_response(*CODE__no_user_auth), description=error_response(*CODE__no_user_auth)
    )


def get_auth_header(headers, raise_exception=False):
    """check and get Token authentication header from headers

    :param werkzeug.datastructures.Headers headers: All headers in request.
    :param bool raise_exception: raise exception.

    :returns: Found raw authentication header.
    :rtype: str or None

    :raise: HTTPException if raise_exception is **True**
                                              and auth header is not in headers
                                              or it is not Token type.
    """
    auth_header = headers.get("Authorization") or headers.get("authorization")
    if not auth_header or not auth_header.startswith("Token "):
        if raise_exception:
            print("EXCEPTION 1 MISS-CONFIGURED Token or bad authorization header")
            raise HTTPException(
                response=error_response(*CODE__invalid_auth_header),
                description=error_response(*CODE__invalid_auth_header)
            )
    return auth_header


def get_data_from_auth_header(header):
    """decode Token auth header and get data

    :param str header: The raw auth header.

    :returns: a tuple of database name and user token
    :rtype: tuple
    :raise: HTTPException if Token header is invalid base64
                                              string or if the Token header is
                                              in the wrong format
    """

    normalized_token = header.replace("Token ", "").replace("\\n", "").encode("utf-8")
    try:
        decoded_token_parts = (
            base64.b64decode(normalized_token).decode("utf-8").split(":")
        )

    except Exception as e:
        raise HTTPException(
            response=error_response(*CODE__invalid_auth_header), description=error_response(*CODE__invalid_auth_header)
        )

    if len(decoded_token_parts) == 1:
        db_name, user_token = DATABASE_NAME, decoded_token_parts[0]
    elif len(decoded_token_parts) == 2:
        db_name, user_token = decoded_token_parts
    else:
        err_descrip = (
            'Token auth header payload must be of the form "<%s>" (encoded to base64)'
            % "user_token"
            if odoo.tools.config["dbfilter"]
            else "db_name:user_token"
        )
        raise HTTPException(
            response=error_response(500, "Invalid header", err_descrip)
        )

    print("DB: {}  User Token: {}".format(db_name, user_token))

    return db_name, user_token


def setup_db(httprequest, db_name):
    """check and setup db in session by db name

    :param httprequest: a wrapped werkzeug Request object
    :type httprequest: :class:`werkzeug.wrappers.BaseRequest`
    :param str db_name: Database name.

    :raise: HTTPException if the database not found.
    """
    if httprequest.session.db:
        return
    if db_name not in odoo.service.db.list_dbs(force=True):
        raise HTTPException(
            response=error_response(*CODE__db_not_found)
        )

    httprequest.session.db = db_name


# def route(*args, **kwargs):
#     """Set up the environment for route handlers.
#
#     Patches the framework and additionally authenticates
#     the API token and infers database through a different mechanism.
#
#     :param list args: Positional arguments. Transparent pass through to the patched method.
#     :param dict kwargs: Keyword arguments. Transparent pass through to the patched method.
#
#     :returns: wrapped method
#     """
#
#     def decorator(controller_method):
#         @functools.wraps(controller_method)
#         def controller_method_wrapper(*iargs, **ikwargs):
#
#             auth_header = get_auth_header(request.httprequest.headers, raise_exception=True)
#             db_name, user_token = get_data_from_auth_header(auth_header)
#             setup_db(request.httprequest, DATABASE_NAME)
#             authenticated_user = authenticate_token_for_user(user_token)
#             # namespace = get_namespace_by_name_from_users_namespaces(
#             #     authenticated_user, ikwargs["namespace"], raise_exception=True
#             # )
#             data_for_log = {
#                 "user_id": authenticated_user.id,
#                 "user_request": None,
#                 "user_response": None,
#             }
#
#             try:
#                 response = controller_method(*iargs, **ikwargs)
#             except HTTPException as e:
#                 response = e.response
#             except Exception as e:
#                 traceback.print_exc()
#                 if hasattr(e, "error") and isinstance(e.error, Exception):
#                     e = e.error
#                 response = error_response(
#                     status=500,
#                     error=type(e).__name__,
#                     error_descrip=e.name if hasattr(e, "name") else str(e),
#                 )
#
#             data_for_log.update(
#                 {"user_request": request.httprequest, "user_response": response}
#             )
#             print("DATAAAS: ", data_for_log)
#             create_log_record(**data_for_log)
#
#             return response
#
#         return controller_method_wrapper
#
#     return decorator


def check_auth_decorator(controller_method):
    @functools.wraps(controller_method)
    def controller_method_wrapper(*args, **kwargs):

        auth_header = get_auth_header(request.httprequest.headers, raise_exception=True)
        db_name, user_token = get_data_from_auth_header(auth_header)
        setup_db(request.httprequest, DATABASE_NAME)
        authenticated_user = authenticate_token_for_user(user_token)
        print("Authenticated User -> :", authenticated_user.name)
        data_for_log = {
            "user_id": authenticated_user.id,
            'user_name': authenticated_user.name,
            "user_request": None,
            "user_response": None,
        }
        try:
            response = controller_method(*args, **kwargs)
        except HTTPException as e:
            response = e.response
        except Exception as e:
            traceback.print_exc()
            if hasattr(e, "error") and isinstance(e.error, Exception):
                e = e.error
            response = error_response(
                status=500,
                error=type(e).__name__,
                error_descrip=e.name if hasattr(e, "name") else str(e),
            )

        data_for_log.update(
            {"user_request": request.httprequest, "user_response": response}
        )

        data_for_log.update({'env': request.env})

        create_log_record(**data_for_log)

        return response

    return controller_method_wrapper
