import json
from odoo.http import route, request, Controller
from .custom_auth import check_auth_decorator
from .utils import check_required_fields, API_ROOT

"""
on driver creation should create an employee 
then create private address(contact for the employee) 'link between contact and employee'

"""

EMPLOYEE_API_ROOT = f'{API_ROOT}/driver'


class DriverController(Controller):
    # List All Drivers
    @check_auth_decorator
    @route(f'{EMPLOYEE_API_ROOT}/all', auth='none', type='json', methods=['GET'])
    def list_drivers(self, *args, **kwargs):
        """
        return list of all drivers
        :param args:
        :param kwargs:
        :return:
        """
        result = {'code': None, 'message': None, 'data': None, 'status': 200}
        try:
            print("iiiinnnnn")
            all_employees = request.env['hr.employee'].search([('active', '=', True), ('is_driver', '=', True)])
            print("innnnnnnnnnn22222")
            if all_employees.exists():
                result['message'] = 'Success'
                result['code'] = 200

                drivers_list = [{'first_name': emp.name, 'last_name': emp.last_name, 'email': emp.work_email,
                                 'mobile': emp.mobile_phone, 'id': emp.id} for emp in
                                all_employees]

                result['data'] = drivers_list
            else:
                result['message'] = 'Success'
                result['code'] = 200

        except Exception as e:
            result['message'] = 'Error:{}'.format(e)
            result['code'] = 500

        return result

    # Get Driver Info
    @check_auth_decorator
    @route(f'{EMPLOYEE_API_ROOT}', auth='none', type='json', methods=['GET'])
    def get_driver(self, *args, **kwargs):
        """
        Return Driver Details
        :param args:
        :param kwargs:
        :return:
        """
        result = {'code': None, 'message': None, 'data': None, 'status': 200}
        try:
            id = kwargs.get('id')
            if id:
                driver = request.env['hr.employee'].search([('id', '=', int(id)), ('active', '=', True)])
                if driver.exists():
                    res = {'first_name': driver.name,
                           'last_name': driver.last_name,
                           'job_title': driver.job_title,
                           'email': driver.work_email,
                           'mobile': driver.mobile_phone
                           }

                    result['message'] = 'Success'
                    result['code'] = 200
                    result['data'] = res

                else:
                    result['message'] = 'Success'
                    result['code'] = 200
                    result['data'] = 'No Data'
            else:
                result['message'] = 'Success'
                result['code'] = 200
                result['data'] = 'No ID Provided'

        except Exception as e:
            result['message'] = 'Error:{}'.format(e)
            result['code'] = 500

        return result

    # Create Driver
    @check_auth_decorator
    @route(f'{EMPLOYEE_API_ROOT}', auth='none', type='json', methods=['POST'])
    def create_driver(self, *args, **kwargs):

        response = {'code': None, 'message': None, 'data': None, 'status': 200}

        try:
            required_fields = ['first_name', 'last_name', 'email', 'mobile']
            if not check_required_fields(kwargs, required_fields):
                response['code'] = 500
                response['message'] = 'incorrect fields Error the correct fields are ({})'.format(
                    ','.join(required_fields))
                return response

            department = request.env['hr.department'].search([('is_operation_department', '=', True)])
            custody_account = request.env['account.account'].search([('is_custody_account', '=', True)])

            employee_dict = {'department_id': department.id or None,
                             'job_title': 'Driver',
                             'is_driver': True,
                             'custody_account': custody_account.id or None}

            contact_dict = {'type': 'private'}

            if kwargs.get('first_name'):
                employee_dict.update({'name': kwargs.get('first_name')})
                contact_dict.update({'name': kwargs.get('first_name')})
            if kwargs.get('last_name'):
                employee_dict.update({'last_name': kwargs.get('last_name')})
                contact_dict.update({'last_name': kwargs.get('last_name')})
            if kwargs.get('email'):
                employee_dict.update({'work_email': kwargs.get('email')})
                contact_dict.update({'email': kwargs.get('email')})
            if kwargs.get('mobile'):
                employee_dict.update({'mobile_phone': kwargs.get('mobile')})
                contact_dict.update({'mobile': kwargs.get('mobile')})

            create_contact_result = request.env['res.partner'].create(contact_dict)
            if create_contact_result:
                request.env.add_to_compute(create_contact_result._fields['display_name'],
                                           create_contact_result.search([('id', '=', create_contact_result.id)]))

                employee_dict.update({'address_home_id': create_contact_result.id})

                create_result = request.env['hr.employee'].create(employee_dict)
                if create_result:
                    response['message'] = 'Success'
                    response['code'] = 200
                    response['data'] = {'first_name': create_result.name, 'last_name': create_result.last_name,
                                        'id': create_result.id}
                else:
                    # TODO:CHECK THIS
                    response['message'] = 'Success'
                    response['code'] = 200
                    response['data'] = 'No Data'
            else:
                # TODO:CHECK THIS
                response['message'] = 'Success'
                response['code'] = 200
                response['data'] = 'No Data'

        except Exception as e:
            response['message'] = 'Error:{}'.format(e)
            response['code'] = 500

        return response

    # Update Driver
    @check_auth_decorator
    @route(f'{EMPLOYEE_API_ROOT}', auth='none', type='json', methods=['PATCH', 'PUT'])
    def update_driver(self, *args, **kwargs):
        result = {'code': None, 'message': None, 'data': None, 'status': 200}
        try:
            id = kwargs.get('id')
            if id:
                target_employee = request.env['hr.employee'].search([('id', '=', int(id))])
                if target_employee.exists():

                    employee_update_dict = {}
                    employee_private_address_dict = {}

                    if kwargs.get('first_name'):
                        employee_update_dict.update({'name': kwargs.get('first_name')})
                        employee_private_address_dict.update({'name': kwargs.get('first_name')})

                    if kwargs.get('last_name'):
                        employee_update_dict.update({'last_name': kwargs.get('last_name')})

                        employee_private_address_dict.update({'last_name': kwargs.get('last_name')})

                    if kwargs.get('email'):
                        employee_update_dict.update({'work_email': kwargs.get('email')})
                        employee_private_address_dict.update({'email': kwargs.get('email')})

                    if kwargs.get('mobile'):
                        employee_update_dict.update({'mobile_phone': kwargs.get('mobile')})
                        employee_private_address_dict.update({'mobile': kwargs.get('mobile')})

                    target_result = target_employee.write(employee_update_dict)

                    if target_employee.address_home_id:
                        target_employee.address_home_id.write(employee_private_address_dict)

                    if target_result:
                        result['message'] = 'Success'
                        result['code'] = 201

                else:
                    result['message'] = "Error Driver Doesn't exist"
                    result['code'] = 500

            else:
                result['message'] = 'Error : No ID Provided'
                result['code'] = 404

        except Exception as e:
            result['message'] = 'Error:{}'.format(e)
            result['code'] = 500
            print(e)
        return result
