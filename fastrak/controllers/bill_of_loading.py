# -*- coding: utf-8 -*-
from odoo.http import route, request, Controller
from odoo.exceptions import ValidationError

from .custom_auth import check_auth_decorator
from .utils import check_required_fields, API_ROOT
from datetime import datetime

BOL_API_ROOT = f'{API_ROOT}/bill-of-loading'


class BillOfLoading(Controller):
    # Get All BOL
    @check_auth_decorator
    @route(f'{BOL_API_ROOT}/all', auth='none', methods=['GET'], type='json')
    def get_all_bill_of_loading(self, **kwargs):
        response = {'code': None, 'message': None, 'data': None, 'status': 200}
        try:
            required_fields = ['date_from', 'date_to']
            if not check_required_fields(kwargs, required_fields):
                response['code'] = 400
                response['message'] = 'incorrect fields the correct fields are ({})'.format(','.join(required_fields))
                return response
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')

            if not date_from and not date_to:
                today = datetime.today()
                month_day_one = today.replace(day=1).date()
                month_today = today.date()
                filters = [('create_date', '>=', month_day_one.strftime('%Y-%m-%d')),
                           ('create_date', '<=', month_today.strftime('%Y-%m-%d'))]
            else:
                filters = [('create_date', '>=', date_from), ('create_date', '<=', date_to)]

            orders_objects = request.env['fastrak.bill.of.loading'].search(filters)
            response['message'] = 'Success'
            response['code'] = 200

            if orders_objects.exists():
                orders_list = [{'id': order.id, 'order_id': order.order_id, 'customer': order.customer.display_name} for
                               order in orders_objects]
                response['data'] = orders_list
            else:
                response['data'] = 'No Data'

        except Exception as e:
            response['message'] = '{}'.format(e)
            response['code'] = 500

        return response

    # Get BOL
    @check_auth_decorator
    @route(f'{BOL_API_ROOT}', auth='none', methods=['GET'], type='json')
    def get_bill_of_loading(self, **kwargs):
        response = {'code': None, 'message': None, 'data': None, 'status': 200}
        try:
            required_fields = ['order_id']
            if not check_required_fields(kwargs, required_fields):
                response['code'] = 400
                response['message'] = 'incorrect fields the correct fields are ({})'.format(','.join(required_fields))
                return response

            target_id = kwargs.get('order_id')
            if target_id:
                bol_object = request.env['fastrak.bill.of.loading'].search([('order_id', '=', target_id)])

                response['message'] = 'Success'
                response['code'] = 200

                if bol_object.exists():
                    data = {
                        'id': bol_object.id,
                        'order_id': bol_object.order_id,
                        'customer': bol_object.customer.display_name,
                        'weight': bol_object.weight,
                        'delivery_type': bol_object.delivery_type,
                        'delivery_time': bol_object.delivery_time,
                        'has_fragile': bol_object.has_fragile,
                        'number_of_pieces': bol_object.number_of_pieces,
                        'payment_method': bol_object.payment_method,
                        'is_pos_payment': bol_object.is_pos_payment,

                        'order_status': bol_object.order_status,
                        'order_delivery_status': bol_object.order_delivery_status,
                        'order_payment_status': bol_object.order_payment_status
                    }
                    response['data'] = data
                else:
                    response['data'] = 'No Data'

            else:
                response['message'] = 'Success'
                response['data'] = 'No Id Provided'

        except Exception as e:
            response['message'] = '{}'.format(e)
            response['code'] = 500

        return response

    @staticmethod
    def _sanitize_address(address):
        try:
            return str(address).replace('\x00', ' ')
        except Exception as e:
            return address

    # Create BOL
    @check_auth_decorator
    @route(f'{BOL_API_ROOT}', auth='none', methods=['POST'], type='json')
    def action_create_bill_of_loading(self, **kwargs):
        """
        customer,order_id,weight,no of pieces,src,dst,payment_method,type(in,out city),delivery_time
        :param kwargs:
        :return:
        """

        response = {'code': None, 'message': None, 'data': None, 'status': 200}
        required_fields = ['user_id', 'order_id', 'weight', 'number_of_pieces', 'has_fragile', 'delivery_type',
                           'delivery_time', 'is_pos_payment', 'payment_method',
                           'insurance_fees', 'shipping_fees', 'vat', 'discount_amount', 'money_collected',
                           'pickup_address', 'delivery_address', 'description']
        try:
            # Check if not required fields then return
            if not check_required_fields(kwargs, required_fields):
                response['code'] = 400
                response['message'] = 'incorrect fields the correct fields are ({})'.format(','.join(required_fields))
                return response

            bill_of_loading_dict = {'customer': kwargs.get('user_id'),
                                    'order_id': kwargs.get('order_id'),
                                    'delivery_type': kwargs.get('delivery_type'),
                                    'delivery_time': kwargs.get('delivery_time'),
                                    'weight': kwargs.get('weight'),
                                    'number_of_pieces': kwargs.get('number_of_pieces'),
                                    'has_fragile': kwargs.get('has_fragile'),
                                    'is_pos_payment': kwargs.get('is_pos_payment'),
                                    'payment_method': kwargs.get('payment_method'),
                                    'insurance_fees': kwargs.get('insurance_fees'),
                                    'shipping_fees': kwargs.get('shipping_fees'),
                                    'vat': kwargs.get('vat'),
                                    'discount_amount': kwargs.get('discount_amount'),
                                    'money_collected': kwargs.get('money_collected'),
                                    'pickup_address': self._sanitize_address(kwargs.get('pickup_address')),
                                    'delivery_address': self._sanitize_address(kwargs.get('delivery_address')),
                                    'description': kwargs.get('description'),
                                    'src_city': kwargs.get('src_city'),
                                    'dst_city': kwargs.get('dst_city'),
                                    'money_collection_payment_method': kwargs.get('money_collection_payment_method',
                                                                                  'cash')
                                    }

            # Create Lines
            bol_lines = []
            service_product = request.env['product.product'].search([('is_main_service_product', '=', True)])
            vat_product = request.env['product.product'].search([('is_main_vat_service', '=', True)])
            if not service_product:
                raise ValidationError("Service Product Not Found")
            bol_shipping_fees = bill_of_loading_dict.get('shipping_fees')
            bol_discount_amount = bill_of_loading_dict.get('discount_amount')
            bol_insurance_fees = bill_of_loading_dict.get('insurance_fees')
            bol_vat_fees = bill_of_loading_dict.get('vat')

            if bol_shipping_fees:
                bol_lines.append(
                    (0, 0, {'product_id': service_product.id, 'amount': bol_shipping_fees + bol_discount_amount,
                            'service_type': 'shipping',
                            'description': 'Shipping Fees'}
                     )
                )

            if bol_insurance_fees:
                bol_lines.append(
                    (0, 0, {'product_id': service_product.id, 'amount': bol_insurance_fees, 'service_type': 'insurance',
                            'description': 'Insurance Fees'}
                     )
                )

            # Update BOL DICT WITH THE CREATED LINES
            if bol_lines:
                bill_of_loading_dict.update({'service_line_ids': bol_lines})

            bol_created_obj = request.env['fastrak.bill.of.loading'].create(bill_of_loading_dict)
            if bol_created_obj:
                response['code'] = 201
                response['message'] = 'Success'
                response['data'] = {
                    'id': bol_created_obj.id,
                    'order_id': bol_created_obj.order_id,
                }

        except Exception as e:
            response['code'] = 500
            response['message'] = 'Error: {}'.format(e)

        return response

    # Update BOL (if available)
    @check_auth_decorator
    @route(f'{BOL_API_ROOT}', auth='none', methods=['PATCH', 'PUT'], type='json')
    def update_bill_of_loading(self, **kwargs):
        response = {'code': None, 'message': None, 'data': None, 'status': 200}
        success_update_msg = []
        try:
            required_fields = ['order_id']
            if not check_required_fields(kwargs, required_fields):
                response['code'] = 400
                response['message'] = 'incorrect fields the correct fields are ({})'.format(','.join(required_fields))
                return response

            order_id = kwargs.get('order_id', None)
            pickup_address = kwargs.get('pickup_address', None)
            delivery_address = kwargs.get('delivery_address', None)

            payment_method = kwargs.get('payment_method', None)
            is_pos_payment = kwargs.get('is_pos_payment', None)

            weight = kwargs.get('weight', None)
            shipping_fees = kwargs.get('shipping_fees', None)

            discount = kwargs.get('discount_amount', None)

            money_collected = kwargs.get('money_collected', None)
            money_collection_payment_method = kwargs.get('money_collection_payment_method', None)

            if order_id:
                update_dict = {}

                bol_obj = request.env['fastrak.bill.of.loading'].search([('order_id', '=', order_id)])

                if not bol_obj:
                    raise ValidationError("Object Doesn't Exists (BOL) ")

                # Address Update Section
                if pickup_address:
                    update_dict['pickup_address'] = pickup_address
                    success_update_msg.append('Pickup Address')

                if delivery_address:
                    update_dict['delivery_address'] = delivery_address
                    success_update_msg.append('Delivery Address')

                # Payment method Section
                if payment_method:
                    if bol_obj.order_status == 'done':
                        raise ValidationError(
                            "Order has been already confirmed can't perform update action for PAYMENT METHOD")
                    update_dict['payment_method'] = payment_method
                    success_update_msg.append('Payment Method')

                # POS/CASH Section
                if is_pos_payment is not None:
                    print("Updating pos payment :", is_pos_payment)
                    print("Order payment method -> ", bol_obj.payment_method, ' -  - ', payment_method)

                    # Order Has been confirmed Case (3 cases A- pickup order , B- delivery order , C- Invoice order)
                    if bol_obj.order_status == 'done':

                        # Case A- Order is on pickup
                        if bol_obj.payment_method == 'on_pickup' or payment_method == 'on_pickup':

                            if bol_obj.order_delivery_status in ['picked', 'delivered']:
                                raise ValidationError(
                                    "Order has been already confirmed and {} can't update POS PAYMENT METHOD".format(
                                        bol_obj.order_delivery_status))

                            print("Order 'ON PICKUP' is done and payment method is {} requested method is {}".format(
                                bol_obj.payment_method, payment_method))

                        # Case B- Order is on delivery
                        elif bol_obj.payment_method == 'on_delivery' or payment_method == 'on_delivery':

                            if bol_obj.order_delivery_status == 'delivered':
                                raise ValidationError(
                                    "Order has been already delivered can't update POS PAYMENT METHOD")

                            print("Order 'ON DELIVERY' is done and payment method is {} requested method is {}".format(
                                bol_obj.payment_method, payment_method))
                        # Case C- Order is on Credit "Do nothing it won't pass payment validation no worries here"

                    update_dict['is_pos_payment'] = is_pos_payment
                    success_update_msg.append('Is Pos')

                # Weight Section
                if weight:
                    print("Updating Weight - Old {} - New {}".format(bol_obj.weight, weight))

                    # Confirmed (Picked-up) Order
                    if bol_obj.order_status == 'done':
                        # Case Pickup can't edit shipping fees anymore
                        if bol_obj.payment_method == 'on_pickup' or payment_method == 'on_pickup':
                            raise ValidationError(
                                "Order has been already confirmed and picked-up can't update Weight")
                        elif bol_obj.payment_method == 'on_delivery' or payment_method == 'on_delivery':
                            if bol_obj.order_delivery_status == 'delivered':
                                raise ValidationError(
                                    "Order has been already confirmed and  delivered can't update Weight")
                        elif bol_obj.payment_method == 'on_credit' or payment_method == 'on_credit':
                            print("weight on credit")
                            if bol_obj.order_delivery_status == 'delivered':
                                raise ValidationError(
                                    "Order has been already confirmed and delivered can't update Weight")

                            if bol_obj.invoice_id.invoice_payment_state == 'paid':
                                raise ValidationError("Order credit invoice bas been already paid can't update Weight")

                    # Will work in all other order status cases & confirmed order if passed checks
                    update_dict['weight'] = weight
                    success_update_msg.append('Weight')

                # Money Collected Section
                if money_collected is not None:
                    if bol_obj.money_collection_entry:
                        raise ValidationError("Money Collection entry has been created can't update money collected")
                    update_dict['money_collected'] = money_collected
                    success_update_msg.append('Money Collected')

                if money_collection_payment_method:
                    if bol_obj.money_collection_entry:
                        raise ValidationError(
                            "Money Collection entry has been created can't update money collection method")
                    update_dict['money_collection_payment_method'] = money_collection_payment_method
                    success_update_msg.append('Money Collection Payment Method')

                # Shipping Fees Section (3 Cases: A- On Pickup,B- On Delivery C- On Invoice)
                if shipping_fees is not None:
                    target_service_line = bol_obj.service_line_ids.filtered(
                        lambda
                            x: x.service_type == 'shipping' and x.product_id.is_main_service_product == True
                    )
                    # Special case for orders that got full discount then got a price change
                    if not target_service_line:
                        # Special case where original order was with 0 shipping fees then got a shipping fees
                        service_product = request.env['product.product'].search(
                            [('is_main_service_product', '=', True)])
                        bol_obj.service_line_ids = [
                            (0, 0, {'product_id': service_product.id, 'amount': shipping_fees,
                                    'service_type': 'shipping', 'description': 'Shipping Fees'}
                             )
                        ]
                        target_service_line = bol_obj.service_line_ids.filtered(
                            lambda
                                x: x.service_type == 'shipping' and x.product_id.is_main_service_product == True
                        )
                    # Confirmed (Picked-up) Order
                    if bol_obj.order_status == 'done':

                        # Case Pickup can't edit shipping fees anymore
                        if bol_obj.payment_method == 'on_pickup' or payment_method == 'on_pickup':
                            raise ValidationError(
                                "Order has been already confirmed and picked-up can't update Shipping Fees")

                        # Case (Delivery & On Credit) depends on order delivery status and invoice payment status
                        else:
                            print("Case on delivery")
                            if bol_obj.order_delivery_status == 'delivered':
                                raise ValidationError(
                                    "Order has been already confirmed delivered can't update Shipping Fees")

                            if not bol_obj.invoice_id.invoice_payment_state == 'paid':

                                # Update Shipping Service Line
                                target_service_line.amount = shipping_fees

                                # Update Order Shipping Fees
                                bol_obj.write({'shipping_fees': shipping_fees})

                                # Reset invoice to draft edits lines and confirm
                                bol_obj.invoice_id.button_draft()
                                print('A ->', bol_obj.invoice_id.invoice_line_ids)
                                bol_obj.invoice_id.invoice_line_ids = [(5,)]
                                print('B RESET ->', bol_obj.invoice_id.invoice_line_ids)
                                # Add Shipping-Fees Line
                                invoice_service_lines = bol_obj._get_bol_service_lines()
                                # Add VAT Lines
                                invoice_service_lines.append(bol_obj._get_bol_vat_line(invoice_service_lines))
                                print("NEW LINES -> ", invoice_service_lines)
                                bol_obj.invoice_id.invoice_line_ids = invoice_service_lines
                                print('C Assign ->', bol_obj.invoice_id.invoice_line_ids)
                                bol_obj.invoice_id.post()
                                success_update_msg.append('Shipping Fees')

                            else:
                                raise ValidationError("Invoice already has been paid")

                    # Will work in all other order status cases & confirmed order if passed checks
                    update_dict['shipping_fees'] = shipping_fees
                    # Update Shipping Service Line
                    target_service_line.amount = shipping_fees
                    success_update_msg.append('Shipping Fees')

                # Discount Section
                if discount is not None:
                    print("IAM HERE -> ", discount)
                    target_service_line = bol_obj.service_line_ids.filtered(
                        lambda
                            x: x.service_type == 'shipping' and x.product_id.is_main_service_product == True
                    )

                    # Confirmed (Picked-up) Order
                    if bol_obj.order_status == 'done':
                        # Will change order service line & and will change invoice that has been created
                        # but should check first delivery status

                        if bol_obj.payment_method == 'on_pickup' or payment_method == 'on_pickup':
                            raise ValidationError("Order already confirmed & picked can't update discount")

                        # Case On-Delivery or On-Credit
                        else:
                            if bol_obj.order_delivery_status == 'delivered':
                                raise ValidationError("Order already confirmed & delivered can't update discount")

                            # Change (service line amount & invoice line amount)
                            if not bol_obj.invoice_id.invoice_payment_state == 'paid':

                                # Update Shipping Service Line with old net shipping + new discount
                                target_service_line.amount = shipping_fees + discount

                                # Update Order Discount Fees
                                bol_obj.write({'discount_amount': discount})

                                # Reset invoice to draft edits lines and confirm
                                bol_obj.invoice_id.button_draft()
                                print('A ->', bol_obj.invoice_id.invoice_line_ids)
                                bol_obj.invoice_id.invoice_line_ids = [(5,)]
                                print('B RESET ->', bol_obj.invoice_id.invoice_line_ids)

                                invoice_service_lines = bol_obj._get_bol_service_lines()

                                # Append discount to the service lines
                                invoice_service_lines.append(bol_obj._get_discount_service_line(discount))
                                invoice_service_lines.append(bol_obj._get_bol_vat_line(invoice_service_lines))

                                bol_obj.invoice_id.invoice_line_ids = invoice_service_lines
                                print('C Assigned Lines ->', bol_obj.invoice_id.invoice_line_ids)

                                bol_obj.invoice_id.post()
                                success_update_msg.append('Discount')

                            else:
                                raise ValidationError("Invoice already has been paid")

                    update_dict['discount_amount'] = discount
                    target_service_line.amount = shipping_fees + discount

                    success_update_msg.append('Discount')

                print("UPDATE DICT: ", update_dict)

                save_result = bol_obj.with_delay(
                    channel='root.order_detail_update_channel',
                    description=f'Order {bol_obj.order_id} Update ', priority=5,
                    max_retries=5).write(update_dict)

                if save_result:
                    response['code'] = 200
                    response['message'] = 'Order Details ({}) Updated Successfully'.format(','.join(success_update_msg))
                    response['data'] = {'order_id': bol_obj.order_id}

        except Exception as e:
            print(e)
            response['code'] = 500
            response['message'] = 'Error: {}'.format(e)

        return response

    # Confirm Order, Assign Pickup Driver (Order Picked up)
    @check_auth_decorator
    @route(f'{BOL_API_ROOT}/confirm-order-pickup', auth='none', methods=['POST'], type='json')
    def confirm_order_pickup(self, **kwargs):
        response = {'code': None, 'message': None, 'data': None, 'status': 200}

        try:
            required_fields = ['order_id', 'driver_id']
            if not check_required_fields(kwargs, required_fields):
                response['code'] = 400
                response['message'] = 'incorrect fields the correct fields are ({})'.format(','.join(required_fields))
                return response

            order_id = kwargs.get('order_id', None)
            driver_id = kwargs.get('driver_id', None)
            if order_id and driver_id:

                bol_obj = request.env['fastrak.bill.of.loading'].search([('order_id', '=', order_id)])
                driver = request.env['hr.employee'].search([('id', '=', driver_id)])

                if not driver:
                    raise ValidationError("Object Doesn't Exists (Driver)")
                if not bol_obj:
                    raise ValidationError("Object Doesn't Exists (BOL) ")
                if bol_obj.trips_ids.filtered(lambda r: r.trip_status == 'picked'):
                    raise ValidationError("Pick-Up Driver Already Assigned")

                # Check if there is a missing cost center then stop all operation
                # TODO:Maybe considered to be removed in next updates
                bol_obj._check_cost_center()

                save_result = bol_obj.write(
                    {
                        # 'order_delivery_status': 'picked',
                        'order_status': 'done',
                        'trips_ids': [
                            (0, 0, {
                                'driver_id': driver_id,
                                'trip_status': 'picked'
                            })
                        ]
                    }
                )

                if save_result:
                    # Function :confirm_bill_loading , Internal function for GUI should have same logic here
                    if bol_obj.payment_method == 'on_pickup':
                        bol_obj.with_delay(
                            channel='root.order_pickup_channel',
                            description=f'Order {bol_obj.order_id} Pickup ', priority=5,
                            max_retries=5).confirm_bill_loading()

                    # bol_obj.confirm_bill_loading()

                    # if not bol_obj.invoice_id:
                    #     # Create new invoice & validate it if there is no invoice assigned
                    #     invoice_result = bol_obj._create_invoice()
                    #     if invoice_result:
                    #         bol_obj.write({'invoice_id': invoice_result.id})
                    #         bol_obj.invoice_id.action_post()
                    # else:
                    #     # Validate assigned invoice
                    #     current_invoice = bol_obj.invoice_id
                    #     if not current_invoice.state == 'posted':
                    #         bol_obj.invoice_id.action_post()

                response['code'] = 200
                response['message'] = 'Order Pickup Confirmed'
                response['data'] = {'order_id': bol_obj.order_id}

            else:
                response['code'] = 500
                response['message'] = 'Missing Data'

        except Exception as e:
            print(e)
            response['code'] = 500
            response['message'] = 'Error: {}'.format(e)

        return response

    # Used to confirm that order has been delivered and assign the driver
    @check_auth_decorator
    @route(f'{BOL_API_ROOT}/confirm-order-delivery', auth='none', methods=['POST'], type='json')
    def confirm_order_delivery(self, **kwargs):
        response = {'code': None, 'message': None, 'data': None, 'status': 200}
        try:
            required_fields = ['order_id', 'driver_id']
            if not check_required_fields(kwargs, required_fields):
                response['code'] = 400
                response['message'] = 'incorrect fields the correct fields are ({})'.format(','.join(required_fields))
                return response

            order_id = kwargs.get('order_id', None)
            driver_id = kwargs.get('driver_id', None)

            bol_obj = request.env['fastrak.bill.of.loading'].search([('order_id', '=', order_id)])
            driver = request.env['hr.employee'].search([('id', '=', driver_id)])

            if not driver:
                raise ValidationError("Object Doesn't Exists (Driver)")

            if not bol_obj:
                raise ValidationError("Object Doesn't Exists (BOL) ")

            # if bol_obj.order_delivery_status == 'delivered':
            #     raise ValidationError("Delivery Driver Already Assigned")
            #
            # if not bol_obj.order_delivery_status == 'picked':
            #     raise ValidationError("Order Not Picked up yet to be delivered")

            if bol_obj.payment_method in ['on_delivery', 'on_credit']:
                # TODO: Change channel to root.order_delivery_channel
                print(50 * '*')
                bol_obj.with_delay(
                    channel='root.order_pickup_channel',
                    description=f'Confirm Order {bol_obj.order_id} Delivery ', priority=5,
                    max_retries=5).confirm_bill_loading()

            save_result = bol_obj.with_delay(
                channel='root.order_delivery_channel',
                description=f'Order {bol_obj.order_id} Delivery ', priority=5,
                max_retries=5).write(
                {
                    # 'order_delivery_status': 'delivered',
                    'trips_ids': [
                        (0, 0, {
                            'driver_id': driver_id,
                            'trip_status': 'delivered'}
                         )
                    ]
                }
            )

            if save_result:
                response['code'] = 200
                response['message'] = 'Order Delivery Confirmed'
                response['data'] = {'order_id': bol_obj.order_id}

        except Exception as e:
            print(e)
            response['code'] = 500
            response['message'] = 'Error: {}'.format(e)

        return response

    @check_auth_decorator
    @route(f'{BOL_API_ROOT}/confirm-order-money-collection', auth='none', methods=['POST'], type='json')
    def confirm_order_money_collection(self, **kwargs):
        """
        Confirm order money collection entry has been collected by the driver
        :param kwargs:
        :return:
        """
        response = {'code': None, 'message': None, 'data': None, 'status': 200}
        try:

            required_fields = ['order_id', 'collection_type']
            if not check_required_fields(kwargs, required_fields):
                response['code'] = 400
                response['message'] = 'incorrect fields the correct fields are ({})'.format(','.join(required_fields))
                return response
            res = ''
            order_id = kwargs.get('order_id')
            # Collection type 'shipping_fees' to register invoice payment
            # Collection type 'money_collection' to register money collection entry payment
            collection_type = kwargs.get('collection_type')

            bol_obj = request.env['fastrak.bill.of.loading'].search([('order_id', '=', order_id)])
            if not bol_obj:
                raise ValidationError("Object Doesn't Exists")

            if bol_obj.order_status in ('refund', 'canceled'):
                raise ValidationError("Order Status is either Canceled Or Refunded")

            if not bol_obj.order_status == 'done':
                raise ValidationError("Order Not Confirmed Yet")

            # TODO: CHECK MAYBE USELESS
            if bol_obj.payment_is_registered:
                raise ValidationError("Money Already Collected")

            print("Collection Type -> ", collection_type)
            if not collection_type:
                raise ValidationError("Collection type is either 'shipping_fees' or 'money_collection' ")
            if collection_type == 'shipping_fees':
                res = bol_obj.with_delay(
                    channel='root.shipping_fees_channel',
                    description=f'Shipping Fees {bol_obj.order_id}', priority=5,
                    max_retries=5).register_payment(api_action=True)

            elif collection_type == 'money_collection':
                res = bol_obj.with_delay(
                    channel='root.money_collection_channel',
                    description=f'Money Collection {bol_obj.order_id}', priority=5,
                    max_retries=5).create_money_collection_entry(raise_exception=False)

            response['code'] = 200
            response['message'] = 'Confirmed Order Money Collection ({})'.format(res)
            response['data'] = {'order_id': bol_obj.order_id}

        except Exception as e:
            print(e)
            response['code'] = 500
            response['message'] = 'Error: {}'.format(e)

        return response
