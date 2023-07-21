import json
import logging
from odoo.http import route, request, Controller
from odoo.exceptions import ValidationError
from .custom_auth import check_auth_decorator
from .utils import check_required_fields, API_ROOT
from odoo.tools.float_utils import float_round

logging.basicConfig(level=logging.DEBUG)

_logger = logging.getLogger(__name__)

WITHDRAW_REQUEST_API_ROOT = f'{API_ROOT}/withdraw-request'


class WithDrawRequest(Controller):
    """
    Handle all operations related to the customer withdraw request
    """

    @check_auth_decorator
    @route(f'{WITHDRAW_REQUEST_API_ROOT}/all', auth='none', type='json', methods=['GET'])
    def list_withdraw_request(self, *args, **kwargs):
        response = {'status': 200, 'code': None, 'message': None, 'data': 'Empty'}

        try:
            all_withdraw_request = request.env['withdraw.request'].sudo().search([('active', '=', True)])

            withdraw_requests_list = [
                {
                    'id': cust_req.id, 'request_timestamp': cust_req.request_timestamp,
                    'customer': cust_req.customer.display_name,
                    'amount': cust_req.amount,
                    'status': cust_req.status
                } for cust_req in all_withdraw_request
            ]

            response['data'] = withdraw_requests_list

            response['message'] = 'Success'
            response['code'] = 200
        except Exception as e:
            response['message'] = 'Error:{}'.format(e)
            response['code'] = 500

        return response

    @check_auth_decorator
    @route(f'{WITHDRAW_REQUEST_API_ROOT}', auth='none', type='json', methods=['GET'])
    def view_with_draw_request(self, *args, **kwargs):
        response = {'status': 200, 'code': None, 'message': None, 'data': 'Empty'}

        try:
            required_fields = ['request_id']
            if not check_required_fields(kwargs, required_fields):
                response['code'] = 400
                response['message'] = 'incorrect fields the correct fields are ({})'.format(','.join(required_fields))
                return response

            request_id = kwargs.get('request_id')
            if request_id:
                withdraw_request_object = request.env['withdraw.request'].search([('id', '=', request_id)])
                if withdraw_request_object.exists():
                    response['data'] = {
                        'request_timestamp': withdraw_request_object.request_timestamp,
                        'customer': withdraw_request_object.customer.display_name,
                        'amount': withdraw_request_object.amount,
                        'status': withdraw_request_object.status
                    }
                    response['message'] = 'Success'
                    response['code'] = 200

        except Exception as e:
            response['message'] = 'Error:{}'.format(e)
            response['code'] = 500

        return response

    @staticmethod
    def _get_tax_percentage_amount():

        return (request.env['account.tax'].search(
            [('active', '=', True), ('type_tax_use', '=', 'sale'), ('amount_type', '=', 'percent')]
        ).amount) / 100

    @check_auth_decorator
    @route(f'{WITHDRAW_REQUEST_API_ROOT}', auth='none', type='json', methods=['POST'])
    def create_with_draw_request(self, *args, **kwargs):
        response = {'status': 200, 'code': None, 'message': None, 'data': 'Empty'}

        try:
            required_fields = ['customer_id', 'amount', 'order_ids']
            if not check_required_fields(kwargs, required_fields):
                response['code'] = 400
                response['message'] = 'incorrect fields the correct fields are ({})'.format(','.join(required_fields))
                return response

            commission = request.env['withdraw.request.commission'].search(
                [
                    ('range_from', '<=', kwargs.get('amount')), ('range_to', '>=', kwargs.get('amount'))
                ], limit=1
            )
            if not commission:
                raise ValidationError("No commission range found")

            orders_string = '\n'.join(kwargs.get('order_ids').split(',')) if ',' in kwargs.get(
                'order_ids') else "No Orders Sent"

            withdraw_obj_dict = {
                'customer': kwargs.get('customer_id'),
                'amount': kwargs.get('amount'),
                'customer_collection_type': kwargs.get('customer_collection_type'),
                'order_ids': orders_string,
                'revenue_type': commission.commission_type,
                'revenue_amount': commission.commission_amount,
                'revenue_percentage': commission.commission_percentage,
            }

            if commission.commission_type == 'percent':
                withdraw_obj_dict['revenue_amount'] = float_round(
                    (commission.commission_percentage / 100) * kwargs.get('amount'), precision_digits=0)

            # Calculate Vat Revenue Amount
            withdraw_obj_dict['revenue_vat_amount'] = withdraw_obj_dict.get(
                'revenue_amount') * self._get_tax_percentage_amount()

            res = request.env['withdraw.request'].create(withdraw_obj_dict)

            response['message'] = 'Success'
            response['code'] = 201
            response['data'] = {'id': res.id}
        except Exception as e:
            response['message'] = 'Error:{}'.format(e)
            response['code'] = 500

        return response

    @check_auth_decorator
    @route(f'{WITHDRAW_REQUEST_API_ROOT}/confirm-completed', auth='none', type='json', methods=['PUT', 'PATCH'])
    def confirm_with_draw_request_payment(self, *args, **kwargs):
        response = {'status': 200, 'code': None, 'message': None, 'data': 'Empty'}

        try:
            required_fields = ['request_id']
            if not check_required_fields(kwargs, required_fields):
                response['code'] = 400
                response['message'] = 'incorrect fields the correct fields are ({})'.format(','.join(required_fields))
                return response

            request_id = kwargs.get('request_id')
            if request_id:
                withdraw_request_object = request.env['withdraw.request'].search([('id', '=', request_id)])
                if withdraw_request_object.exists():
                    res = withdraw_request_object.operation_confirm_payment(api_request=True)
                    if res:
                        response['message'] = 'Success (Payment Confirmed)'
                        response['code'] = 200
                else:
                    raise ValidationError(
                        "Object Doesn't Exists (Withdraw Request with id -> {}) ".format(kwargs.get('request_id')))

        except Exception as e:
            response['message'] = 'Error:{}'.format(e)
            response['code'] = 500

        return response
