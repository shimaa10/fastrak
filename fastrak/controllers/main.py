# -*- coding: utf-8 -*-
from odoo.http import request, Controller, route

from .utils import API_ROOT, DB_NAME, check_required_fields
import passlib

MAIN_API_ROOT = f'{API_ROOT}'

DEFAULT_CRYPT_CONTEXT = passlib.context.CryptContext(
    # kdf which can be verified by the context. The default encryption kdf is
    # the first of the list
    ['pbkdf2_sha512', 'plaintext'],
    # deprecated algorithms are still verified as usual, but ``needs_update``
    # will indicate that the stored hash should be replaced by a more recent
    # algorithm. Passlib 1.6 supports an `auto` value which deprecates any
    # algorithm but the default, but Ubuntu LTS only provides 1.5 so far.
    deprecated=['plaintext'],
)


class MainController(Controller):

    @route(f'{MAIN_API_ROOT}/check-connection', auth='none', methods=['GET'], type='json')
    def action_connection_check(self, **kwargs):
        try:
            response = {'message': 'Success', 'status': 200}
        except Exception as e:
            print(e)
            response = {'message': 'Error- {}'.format(e), 'status': 500}
        return response

    @route(f'{MAIN_API_ROOT}/auth-token', auth="none", methods=['POST'], type='json')
    def authenticate_token(self, *args, **kwargs):
        response = {'code': None, 'message': None, 'data': None, 'status': 200}
        try:
            required_fields = ['username', 'password']
            if not check_required_fields(kwargs, required_fields):
                response['code'] = 400
                response['message'] = 'incorrect fields the correct fields are ({})'.format(','.join(required_fields))
                return response

            user_name = kwargs.get('username')
            user_password = kwargs.get('password')
            target_user = request.env['res.users'].search([('login', '=', user_name)])

            if not target_user:
                response['code'] = 401
                response['message'] = 'Invalid Credentials'
                return response

            request.env.cr.execute("SELECT COALESCE(password, '') FROM res_users WHERE id=%s", [target_user.id])
            [hashed] = request.env.cr.fetchone()
            valid, replacement = DEFAULT_CRYPT_CONTEXT.verify_and_update(user_password, hashed)

            if not valid:
                response['code'] = 401
                response['message'] = 'Invalid Credentials'
                return response

            # Success
            if not target_user.api_token or not target_user.api_token:
                target_user.sudo().reset_api_token()

            token = target_user.api_token

            response['code'] = 200
            response['message'] = 'Success'
            response['data'] = {'token': token}

        except Exception as e:
            print("Exception : ", e)
            response['code'] = 401
            response['message'] = 'Invalid Credentials'

        return response
