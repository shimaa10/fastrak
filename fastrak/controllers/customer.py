import json
import logging

from odoo.http import request, Controller, route

from .custom_auth import check_auth_decorator
from .utils import check_required_fields, DB_NAME, API_ROOT

logging.basicConfig(level=logging.DEBUG)

_logger = logging.getLogger(__name__)

CUSTOMER_API_ROOT = f'{API_ROOT}/customer'


class FastrakCustomer(Controller):

    # List Customers
    @check_auth_decorator
    @route(f'{CUSTOMER_API_ROOT}/all', auth='none', methods=['GET'], type='json')
    def get_all_customers(self, **kwargs):
        result = {'code': None, 'message': None, 'data': None, 'status': 200}
        try:
            customers_objs = request.env['res.partner'].search([('customer_rank', '>', 0)])
            result['message'] = 'Success'
            result['code'] = 200
            if customers_objs.exists():
                customers_list = [
                    {'name': customer.name, 'id': customer.id, 'mobile': customer.mobile, 'email': customer.email,
                     'company_name': customer.customer_company_name} for customer in customers_objs]

                result['data'] = customers_list

        except Exception as e:
            result['message'] = 'error:{}'.format(e)
            result['code'] = 500
        return result

    # Retrieve Customer
    @check_auth_decorator
    @route(f'{CUSTOMER_API_ROOT}', auth='none', methods=['GET'], type='json')
    def get_customer(self, **kwargs):
        """
        Get customer details
        :param kwargs: id
        :return: json response result :{'message': , 'status': , 'data': }
        """
        result = {'code': None, 'message': None, 'status': 200, 'data': None}

        try:
            customer_obj = request.env['res.partner'].search(
                [
                    ('customer_rank', '>', 0),
                    ('id', '=', kwargs.get('id'))
                ]
            )

            result['message'] = 'Success'
            result['code'] = 200

            if customer_obj.exists():
                customer_dict = {
                    'first_name': customer_obj.name,
                    'last_name': customer_obj.last_name,
                    'company_name': customer_obj.company_name,
                    'is_business_account': customer_obj.is_premium_user,
                    'email': customer_obj.email,
                    'mobile': customer_obj.mobile,
                    'cr': customer_obj.cr,
                    'vat': customer_obj.vat
                }

                result['data'] = customer_dict

            else:
                result['message'] = 'No Data Found'
                result['code'] = 404
        except Exception as e:
            result['message'] = 'error:{}'.format(e)
            result['code'] = 500

        return result

    # Create Customer
    @check_auth_decorator
    @route(f'{CUSTOMER_API_ROOT}', auth='none', methods=['POST'], type='json')
    def create_customer(self, **kwargs):
        """
        Create Customer Api EndPoint
        Available fields :
        1- first_name 'required'
        2- last_name 'required'
        3- company_name 'not required'
        4- is_business_user 'not required'
        5- email 'required'
        6- mobile 'required'
        7- vat_id 'if business account'
        8- cr_id 'if business account'
        9- profile_image
        :param kwargs:
        :return:
        """

        response = {'code': None, 'message': None, 'data': None, 'status': 200}

        try:
            # Check Required Fields
            required_fields = ['first_name', 'last_name', 'email', 'mobile']
            if not check_required_fields(kwargs, required_fields):
                response['code'] = 400
                response['message'] = 'incorrect fields Error the correct fields are ({})'.format(
                    ','.join(required_fields))
                return response

            customer_dict = {
                'customer_rank': 1
            }

            if kwargs.get('first_name'):
                customer_dict.update({'name': kwargs.get('first_name')})

            if kwargs.get('last_name'):
                customer_dict.update({'last_name': kwargs.get('last_name')})

            if kwargs.get('company_name'):
                customer_dict.update({'customer_company_name': kwargs.get('company_name')})

            if kwargs.get('is_business_user'):
                customer_dict.update({'is_premium_user': kwargs.get('is_business_user')})

            if kwargs.get('email'):
                customer_dict.update({'email': kwargs.get('email')})

            if kwargs.get('mobile'):
                customer_dict.update({'mobile': kwargs.get('mobile')})

            if kwargs.get('vat'):
                customer_dict.update({'vat': kwargs.get('vat')})

            if kwargs.get('cr'):
                customer_dict.update({'cr': kwargs.get('cr')})

            if kwargs.get('profile_image'):
                customer_dict.update({'image_1920': kwargs.get('profile_image')})

            print("Customer Final Dict: ", customer_dict)

            res = request.env['res.partner'].create(customer_dict)
            # Compute Commercial Partner
            res._compute_commercial_partner()

            # Recompute Display Name
            request.env.add_to_compute(res._fields['display_name'], res.search([('id', '=', res.id)]))

            response['message'] = 'Success'
            response['code'] = 201
            response['data'] = {'id': res.id}
        except Exception as e:
            print(e)

            response['message'] = 'Error: {}'.format(e)
            response['code'] = 500

        return response

    # Update Customer
    @check_auth_decorator
    @route(f'{CUSTOMER_API_ROOT}', auth='none', methods=['PATCH', 'PUT'], type='json')
    def update_customer(self, **kwargs):
        """
                Update Customer Api EndPoint
                Available fields :
                1- first_name
                2- last_name
                3- company_name
                4- is_business_user
                5- email
                6- mobile
                7- vat_id 'if business account'
                8- cr_id 'if business account'
                9- profile_image
                :param kwargs:
                :return:
                """

        response = {'code': None, 'message': None, 'data': None, 'status': 200}

        id = kwargs.get('id')
        try:
            required_fields = ['id']
            if not check_required_fields(kwargs, required_fields):
                response['code'] = 400
                response['message'] = 'incorrect fields Error the correct fields are ({})'.format(
                    ','.join(required_fields))
                return response

            if id:
                customer_object = request.env['res.partner'].search([('id', '=', int(id))])
                if customer_object.exists():
                    customer_dict = {}
                    if kwargs.get('first_name'):
                        customer_dict.update({'name': kwargs.get('first_name')})

                    if kwargs.get('last_name'):
                        customer_dict.update({'last_name': kwargs.get('last_name')})

                    if kwargs.get('company_name'):
                        customer_dict.update({'customer_company_name': kwargs.get('company_name')})

                    if kwargs.get('is_business_user') is not None:
                        if kwargs.get('is_business_user'):
                            customer_dict.update({'is_premium_user': True})
                        else:
                            customer_dict.update({'is_premium_user': False})

                    if kwargs.get('email'):
                        customer_dict.update({'email': kwargs.get('email')})

                    if kwargs.get('mobile'):
                        customer_dict.update({'mobile': kwargs.get('mobile')})

                    if kwargs.get('vat'):
                        customer_dict.update({'vat': kwargs.get('vat')})

                    if kwargs.get('cr'):
                        customer_dict.update({'cr': kwargs.get('cr')})

                    if kwargs.get('profile_image'):
                        customer_dict.update({'image_1920': kwargs.get('profile_image')})

                    print("Final update dict: ", customer_dict)

                    update_result = customer_object.write(customer_dict)

                    if update_result:
                        response['message'] = 'Success'
                        response['code'] = 200

                else:
                    response['message'] = "Error Customer Doesn't Exists"
                    response['code'] = 404
            else:
                response['message'] = 'Error No ID Provided'
                response['code'] = 400

        except Exception as e:
            response['error'] = '{}'.format(e)
            response['code'] = 500
            # TODO: Add logger
            print(e)
        print("UPDATE RESULT: ", response)
        return response


# Bank Api's
# add bank and attach it to customer

class FastrakBankController(Controller):

    @check_auth_decorator
    @route(f'{API_ROOT}/bank/all', auth='none', type='json', methods=['GET'])
    def get_bank_list(self):
        """
        Return All Available bank list
        :return:
        """
        response = {'code': None, 'message': None, 'data': None, 'status': 200}
        try:
            result = [{'name': bank.name, 'swift_code': bank.bic, 'id': bank.id} for bank in
                      request.env['res.bank'].sudo().search([])]

            response['message'] = 'Success'
            response['code'] = 200
            response['data'] = result

        except Exception as e:
            print(e)
            response['message'] = '{}'.format(e)
            response['code'] = 500

        return response

    @check_auth_decorator
    @route(f'{CUSTOMER_API_ROOT}/bank/all', auth='none', type='json', methods=['GET'])
    def get_customer_bank_list(self, **kwargs):
        """
        Return All Available bank list for specific customer
        :param kwargs:
        :return:
        """
        response = {'code': None, 'message': None, 'data': None, 'status': 200}
        try:
            customer_id = kwargs.get('id')
            if not check_required_fields(kwargs, ['id']):
                response['code'] = 500
                response['message'] = 'incorrect fields Error the correct fields are ({})'.format(','.join(['id']))
                return response

            if customer_id:
                response['message'] = 'Success'
                response['code'] = 200

                customer_bank_list = [{'id': bank.id, 'name': bank.bank_id.name, 'swift_code': bank.bank_id.bic,
                                       'account_number': bank.acc_number, 'iban_number': bank.iban_number} for bank in
                                      request.env['res.partner.bank'].search([('partner_id', '=', int(customer_id))])]

                response['data'] = customer_bank_list

        except Exception as e:
            print(e)
            response['message'] = '{}'.format(e)
            response['code'] = 500

        return response

    @check_auth_decorator
    @route(f'{CUSTOMER_API_ROOT}/bank', auth='none', type='json', methods=['POST'])
    def create_customer_bank(self, **kwargs):
        """
        Create and link bank to specific customer
        :param kwargs:
        :return:
        """

        response = {'code': None, 'message': None, 'data': None, 'status': 200}
        try:

            # Check on required Fields
            required_fields = ['user_id', 'account_number', 'iban_number', 'swift_code']

            if not check_required_fields(kwargs, required_fields):
                response['code'] = 500
                response['message'] = 'incorrect fields Error the correct fields are ({})'.format(
                    ','.join(required_fields))
                return response

            customer_id = kwargs.get('user_id')
            customer_obj = request.env['res.partner'].search([('id', '=', int(customer_id))])
            if customer_id and customer_obj.exists():

                customer_bank_details = {'partner_id': customer_id}

                if kwargs.get('account_number'):
                    customer_bank_details.update({'acc_number': kwargs.get('account_number')})

                if kwargs.get('iban_number'):
                    customer_bank_details.update({'iban_number': kwargs.get('iban_number')})

                if kwargs.get('swift_code'):
                    bank_id = get_bank_or_create(kwargs.get('swift_code'))
                    customer_bank_details.update({'bank_id': bank_id.id})

                print("BANK TO CREATE DETAILS: ", customer_bank_details)

                create_result = request.env['res.partner.bank'].create(customer_bank_details)

                if create_result:
                    response['message'] = 'Success'
                    response['code'] = 201
                    response['data'] = {
                        'id': create_result.id,
                        'name': create_result.bank_id.name,
                        'account_number': create_result.acc_number,
                    }
            else:
                # No Customer Found
                response['message'] = 'No Customer Found'
                response['code'] = 500

        except Exception as e:
            response['message'] = 'Error: {}'.format(e)
            response['code'] = 500

        return response


def get_bank_or_create(swift):
    """
    Get bank or create new one with the name and swift

    :param swift: bank swift code
    :param name: bank name 'should always be upper case'
    :return: bank instance
    """

    bank = request.env['res.bank'].search([('bic', '=', swift)])
    if not bank:
        bank = request.env['res.bank'].create({'bic': swift, 'name': swift})

    return bank
