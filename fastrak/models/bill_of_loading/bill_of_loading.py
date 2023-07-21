# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.date_utils import datetime
import logging
from odoo.tools.float_utils import float_round

logging.basicConfig(level=logging.DEBUG)

_logger = logging.getLogger()


class FastrakBillOfLoading(models.Model):
    _name = 'fastrak.bill.of.loading'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'fastrak bill of loading model'
    _rec_name = 'order_id'

    _sql_constraints = [
        ('bol_unique_order_id', 'UNIQUE(order_id)', 'Order Id Should Be Unique')
    ]

    STATUS_LIST = [('draft', 'Draft'), ('done', 'Done'), ('refund', 'Refund'),
                   ('canceled', 'Canceled'), ('audited', 'Audited')]

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env['res.company'].browse(
        self.env['res.company']._company_default_get('fastrak.bill.of.loading').id))

    order_id = fields.Char(track_visibility='onchange', string='Order ID', required=True)  # order_id
    delivery_type = fields.Selection([('in', 'Inside City'), ('out', 'Outside City')], track_visibility='onchange',
                                     required=True)
    customer = fields.Many2one('res.partner', track_visibility='onchange', required=True,
                               domain=[('customer_rank', '>', 0)])
    # Shipment info
    pickup_address = fields.Text(track_visibility='onchange')
    delivery_address = fields.Text(track_visibility='onchange')
    src_city = fields.Char(track_visibility='onchange')
    dst_city = fields.Char(track_visibility='onchange')

    weight = fields.Float(string='Weight', track_visibility='onchange', required=True)
    delivery_time = fields.Selection([('rushed', 'Rushed'), ('same', 'Same Day'), ('next', 'Next Day')],
                                     string='Delivery Time', track_visibility='onchange', required=True)
    has_fragile = fields.Boolean(track_visibility='onchange')  # has_fragile
    number_of_pieces = fields.Integer(track_visibility='onchange', required=True, default=1)  # number_of_pieces

    payment_method = fields.Selection([
        ('on_pickup', 'On Pickup'), ('on_delivery', 'On Delivery'), ('on_credit', 'On Credit')
    ], track_visibility='onchange', default='on_pickup', required=True)

    money_collection_payment_method = fields.Selection(
        [
            ('cash', 'Cash'), ('pos', 'POS Machine (Visa)')
        ],
        track_visibility='onchange', default='cash'
    )

    description = fields.Text(track_visibility='onchange')
    money_collected = fields.Float(track_visibility='onchange')
    insurance_fees = fields.Float(track_visibility='onchange')
    shipping_fees = fields.Float(track_visibility='onchange', required=True)
    bank_commission_fees = fields.Float(track_visibility='onchange', default=2)
    money_collection_bank_commission_fees = fields.Float(track_visibility='onchange', default=2)
    vat = fields.Float(track_visibility='onchange')
    discount_amount = fields.Float(track_visibility='onchange')

    is_pos_payment = fields.Boolean(track_visibility='onchange')

    # Order State's
    order_status = fields.Selection(STATUS_LIST, track_visibility='onchange', default='draft')

    order_delivery_status = fields.Selection([('picked', 'Picked'), ('delivered', 'Delivered')],
                                             track_visibility='onchange')

    order_payment_status = fields.Selection([('open', 'Not Paid'), ('paid', 'Paid')], track_visibility='onchange')

    # Service Line Charges Shipping,Insurance,etc..
    service_line_ids = fields.One2many('bill.of.loading.line', 'bol_id', track_visibility='onchange')

    # Assigned Drivers
    trips_ids = fields.One2many('bill.of.loading.trips', 'bol_id', track_visibility='onchange')

    # BOL Invoice
    invoice_id = fields.Many2one('account.move', track_visibility='onchange', domain=[('type', 'in', ('out_invoice',))])

    # For Invoice Payment POS
    invoice_payment_collection = fields.Many2one(
        'account.payment', track_visibility='onchange', string='Invoice Payment',
        domain=[('payment_type', '=', 'inbound')]
    )

    # For Invoice Payment Cash
    payment_collection_entry = fields.Many2one(
        'account.move', track_visibility='onchange', string='Payment Entry',
        domain=[('type', '=', ('entry',))]
    )

    # For External Money Collected for customer
    money_collection_entry = fields.Many2one('account.move', track_visibility='onchange',
                                             domain=[('type', '=', ('entry',))])

    payment_is_registered = fields.Boolean(string='Register Payment')

    bank_commission_entry = fields.Many2one('account.move', track_visibility='onchange',
                                            domain=[('type', '=', 'entry')])

    # Refund & Cancellation Section
    refund_reason_comment = fields.Text(track_visibility='onchange', string='Refund Reason')

    refund_invoice_id = fields.Many2one('account.move', track_visibility='onchange',
                                        domain=[('type', 'in', ('out_refund',))])

    cancellation_reason = fields.Many2one('cancellation.reason', track_visibility='onchange')

    extra_notes = fields.Text()

    def _check_cost_center(self):
        """
        Check the existence of the cost center in each line else stop the whole operation
        :return:
        """
        self.ensure_one()
        for line in self.service_line_ids:
            line_category = line.product_id.product_tmpl_id.categ_id
            if not line_category.cost_centers_id:
                raise ValidationError("Missing Cost Center in Product Category : ({})".format(line_category.name))

    @api.constrains('bank_commission_fees')
    def check_bank_commission_fees(self):
        if self.is_pos_payment:
            if self.bank_commission_fees <= 0:
                raise ValidationError("Error bank commission fees is more or less than range")

    @api.constrains('money_collection_bank_commission_fees')
    def check_money_collection_bank_commission_fees(self):
        if self.money_collection_payment_method == 'pos':
            if self.money_collection_bank_commission_fees <= 0:
                raise ValidationError("Money Collection Bank Commission Fees Can't be equal or less than 0%")

    @api.depends('invoice_id.invoice_payment_state')
    def toggle_order_payment_status(self):
        self.ensure_one()
        if self.invoice_id.invoice_payment_state == 'paid':
            self.write({'order_payment_status': 'paid'})

    def write(self, vals):
        """
        Override Write Method to add log on one2many field for Drivers
        :param vals:
        :return:
        """
        res = super(FastrakBillOfLoading, self).write(vals)

        trips = vals.get('trips_ids')
        content = "<li> Driver: {} has been assigned for {} </li>".format(str(trips), 'Trip')

        if trips:

            try:
                print("Trips ->", trips)

                # Getting last trip as it will be always the current one
                trip = trips[-1]
                print("Main Trip -> ", trip)
                # Trip Details
                trip_data = trips[-1][2]
                print("Trip details -> ", trip_data)

                if trip[0] == 0:
                    print(
                        "Driver : {} - Direction : {} - Description : {}".format(
                            trip_data.get('driver_id'),
                            trip_data.get('trip_status'),
                            trip_data.get('trip_description')
                        )
                    )
                    content = "<li> Driver: {} has been assigned for {} </li>".format(
                        trip_data.get('driver_id'), trip_data.get('trip_status')
                    )

                elif trip[0] == 2:
                    # removal
                    print(
                        "Driver : {} - Direction : {} - Description : {}".format(
                            trip_data.get('driver_id'),
                            trip_data.get('trip_status'),
                            trip_data.get('trip_description')
                        )
                    )

                    content = "<li> Driver: {} has been removed </li>".format(trip_data.get('driver_id'))

            except Exception as e:
                _logger.exception("Error In Trips Log {}".format(e))

            self.message_post(body=content)

        return res

    def unlink(self):
        """
        Override delete no one can delete any order
        :return:
        """
        if not self.env.user.name == 'Administrator':
            raise ValidationError("Order Can't Be Deleted")
        else:
            return super().unlink()

    def _get_report_filename(self):
        """
        Return Report Name
        :return:
        """
        return '{}-{}'.format(self.order_id, self.customer.display_name)

    def confirm_bill_loading(self):
        """
        Confirm BOL will toggle state and create invoice
        manual case: user can still edit the bol before confirm as much as he want once confirmed it will create an invoice
        and link it to the BOL
        automated case 'API': once order received it will create bol,validate it & create invoice and post it
        :return:
        """
        print("Called Confirm Bill of loading")
        self.ensure_one()
        self.write({'order_status': 'done', 'order_payment_status': 'open', 'cancellation_reason': [(5, 0, 0)]})

        if not self.invoice_id:
            # Create new invoice & validate it if there is no invoice assigned
            if self.shipping_fees:
                invoice_result = self._create_invoice()
                if invoice_result:
                    invoice_result.action_post()
                    self.write({'invoice_id': invoice_result.id})
        else:
            # Validate assigned invoice
            current_invoice = self.invoice_id
            if not current_invoice.state == 'posted':
                self.invoice_id.action_post()

    def refund_bill_loading(self):
        """
        TODO: NOT YET COMPLETED
        - switch BOL status to refund
        - Create Credit note for invoice (Reverse Entry)
        - Create reverse entry for money collected

        :return:
        """
        # Reverse Move Call Internal reverse_moves method
        # Cancel = True to reconcile the reversed move with the invoice
        self.ensure_one()
        if not self.refund_reason_comment:
            raise ValidationError("Refund Reason Should be Added First")
        if self.invoice_id:
            print("Refunding  Invoice")
            print("Refund reason:", self.refund_reason_comment)
            self.invoice_id.write({'refund_reason_comment': self.refund_reason_comment})
            self.invoice_id._reverse_moves([{'ref': _('Reversal of %s') % self.invoice_id.name}], cancel=True)

            # if self.invoice_id.invoice_payment_state == 'paid':
            #     # Case Invoice Already Paid
            #     print("Refunding Paid Invoice")
            #     self.invoice_id._reverse_moves([{'ref': _('Reversal of %s') % self.invoice_id.name}], cancel=True)
            # else:
            #     # Case Invoice Not Yet Paid
            #     print("Canceling Posted Only Invoice")
            #     self.invoice_id.write({'cancellation_reason': self.cancellation_reason.id})
            #     self.invoice_id.button_cancel()

        self.update({'order_status': 'refund'})

    def cancel_bill_loading(self):
        """
        TODO: NOT YET COMPLETED: should check first if possible to cancel or not (if invoiced and done can't cancelled)
        # only possible to cancel if there is no invoice or no any operation happened to it
        Cases:
        1- order not yet confirmed pickup
        2- order is pickedup
        :return:
        """
        self.ensure_one()
        if not self.cancellation_reason:
            raise ValidationError("Cancellation Reason is Required")

        self.update({'order_status': 'canceled'})

    def reset_to_draft(self):
        # TODO: should check first if possible to reset or not (if invoiced and done can't reset)
        # only possible to reset if there is no invoice or no any operation happened to it
        self.ensure_one()
        self.update({'order_status': 'draft'})

    def audited_bill_of_loading(self):
        self.ensure_one()
        self._check_both_driver_exists()
        self.update({'order_status': 'audited'})

    def _check_both_driver_exists(self):
        """
        Ensure that there is pickup & delivery driver in eace order
        :return:
        """
        self.ensure_one()
        current_trips = self.trips_ids
        pickup_trip = current_trips.filtered(lambda r: r.trip_status == 'picked')
        delivery_trip = current_trips.filtered(lambda r: r.trip_status == 'delivered')

        if not pickup_trip or not delivery_trip:
            raise ValidationError(_("Something Wrong with the Drivers Assigned Kindly Check it"))
        return True

    # ---------------------------------------------************************---------------------------------------------
    # Invoice Section
    def _get_tax_lines(self) -> object:
        """
        Return tax object id to be used as vat for the invoice line
        :return:
        """
        return self.env['account.tax'].search(
            [('active', '=', True), ('type_tax_use', '=', 'sale'), ('amount_type', '=', 'code')]
        ).id

    def _get_tax_line_object(self):
        """
        Return tax object to be used as vat for calculation
        :return:
        """
        return self.env['account.tax'].search(
            [('active', '=', True), ('type_tax_use', '=', 'sale'), ('amount_type', '=', 'percent')])

    def _get_amount_after_tax(self, amount):
        """
        Return the net amount after deducting the tax included in the price
        :param amount:
        :return:
        """
        tax_percentage = (self._get_tax_line_object().amount / 100) + 1
        # print("tax amount:", self._get_tax_line_object().amount)
        # print(f"Amount Before Tax: {amount}")
        # r0 = float_round(amount / tax_percentage, precision_rounding=0.01, rounding_method='UP')
        # r1 = float_round(round(amount / tax_percentage, 2), precision_rounding=0.01, rounding_method='UP')
        # r2 = round(float_round(amount / tax_percentage, precision_rounding=0.000000000000001, rounding_method='UP'), 2)
        # r3 = float_round(round(amount / tax_percentage, 2), precision_rounding=0.000000000000001, rounding_method='UP')
        # print(f"FloatRounded UP-A: {r0}")
        # print(f"FloatRounded UP-A: {r1}")
        # print(f"FloatRounded UP-B: {r2}")
        # print(f"FloatRounded UP-C: {r3}")

        return round(float_round(amount / tax_percentage, precision_rounding=0.000000000000001, rounding_method='UP'),
                     2)

    def _get_bol_service_lines(self) -> list:
        """
        Prepare invoice lines to be created
        :return:
        """
        # print(50 * '*', "Service Line", 50 * '*')
        service_line_ids = []
        for line in self.service_line_ids:
            if self.company_id.activate_vat_calculation:
                line_data = (0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.description,
                    'quantity': 1,
                    'price_unit': self._get_amount_after_tax(line.amount),
                    # 'tax_ids': [self._get_tax_lines()]
                })
            else:
                line_data = (0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.description,
                    'quantity': 1,
                    'price_unit': line.amount
                })

            # Add Cost Center To Line
            line_category = line.product_id.product_tmpl_id.categ_id
            if line_category.cost_centers_id:
                cost_center = line_category.cost_centers_id
                line_data[2].update({'cost_centers_id': cost_center.id})
            else:
                raise ValidationError("Missing Cost Center in Product Category : ({})".format(line_category.name))

            service_line_ids.append(line_data)
        # print(f"Service Line: {line_data}")
        # print(50 * '*', "End Service Line", 50 * '*')

        return service_line_ids

    def _get_discount_service_line(self, discount_amount) -> tuple:
        """
        Prepare discount line to be created
        :return:
        """
        # print(50 * '*', "Discount Line", 50 * '*')

        # Get and check discount product
        discount_service_product = self.env['product.product'].search([('is_main_discount_service', '=', True)])
        if not discount_service_product:
            raise ValidationError(_("Missing Discount Service"))

        # Get and check cost center for discount product
        line_category = discount_service_product.product_tmpl_id.categ_id
        if line_category.cost_centers_id:
            cost_center = line_category.cost_centers_id
        else:
            cost_center = None
        # TODO: New Vat calculation stopped
        # Added tax to discount to be reversed amount
        if self.company_id.activate_vat_calculation:
            line_data = (0, 0, {
                'product_id': discount_service_product.id,
                'name': "Invoice Discount",
                'quantity': 1,
                'price_unit': -self._get_amount_after_tax(discount_amount),
                # Add Cost Center To Line
                'cost_centers_id': cost_center.id,
                # 'tax_ids': [self._get_tax_lines()]

            })
        else:
            line_data = (0, 0, {
                'product_id': discount_service_product.id,
                'name': "Invoice Discount",
                'quantity': 1,
                'price_unit': -discount_amount,
                # Add Cost Center To Line
                'cost_centers_id': cost_center.id,
            })
        # print(f"Discount Line: {line_data}")
        # print(50 * '*', "End Discount Line", 50 * '*')

        return line_data

    def _get_vat_recalculated_price(self, original_vat_price, invoice_service_lines=None):
        """
        Compares actual vat amount with the residual mount of the order after deducting the discount
        and return the complementary amount if the actual amount is not the right one
        :param original_vat_price:
        :param invoice_service_lines:
        :return:
        """
        shipping_amt = 0
        discount_amt = 0
        price_unit = original_vat_price

        srv_line = list(filter(lambda line: line[2].get('name') == 'Shipping Fees', invoice_service_lines))
        disc_line = list(filter(lambda line: line[2].get('name') == 'Invoice Discount', invoice_service_lines))

        if srv_line:
            srv_line = (srv_line[0])[2]
            shipping_amt = srv_line.get('price_unit')

        if disc_line:
            disc_line = (disc_line[0])[2]
            discount_amt = disc_line.get('price_unit')

        base_amt = round(shipping_amt + discount_amt, 2)

        final_amount = round(self.shipping_fees - base_amt, 2)

        if base_amt + final_amount == self.shipping_fees:
            price_unit = final_amount

        return price_unit

    def _get_bol_vat_line(self, invoice_service_lines=None) -> list:
        """
        Prepare invoice lines to be created (Vat Lines)
        :return:
        """
        vat_service_product = self.env['product.product'].search([('is_main_vat_service', '=', True)])
        tax_percentage = self._get_tax_line_object().amount / 100
        price_unit = self._get_amount_after_tax(self.shipping_fees) * tax_percentage

        shipping_line = self.service_line_ids.filtered(lambda line: line.service_type == 'shipping')

        if not shipping_line.amount == self.discount_amount:
            price_unit = self._get_vat_recalculated_price(price_unit, invoice_service_lines)
            line_data = (0, 0, {
                'product_id': vat_service_product.id,
                'name': vat_service_product.name,
                'quantity': 0,
                'price_unit': price_unit,
                'tax_ids': [self._get_tax_lines()]
            })
        else:
            line_data = (0, 0, {
                'product_id': vat_service_product.id,
                'name': vat_service_product.name,
                'quantity': 0,
                'price_unit': 0,
                'tax_ids': [self._get_tax_lines()]
            })

        return line_data

    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        # ensure a correct context for the _get_default_journal method and company-dependent fields
        self = self.with_context(default_company_id=self.company_id.id, force_company=self.company_id.id)
        journal = self.env['account.move'].with_context(default_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (
                self.company_id.name, self.company_id.id))

        invoice_service_lines = self._get_bol_service_lines()
        # TODO: iam here not yet completed

        if self.discount_amount and self.shipping_fees:
            # Add discount line to invoice if there is both discount & shipping
            invoice_discount_line = self._get_discount_service_line(self.discount_amount)
            invoice_service_lines.append(invoice_discount_line)

        invoice_service_lines.append(self._get_bol_vat_line(invoice_service_lines))

        print("Invoice Lines:", invoice_service_lines)

        invoice_vals = {
            'ref': '{}'.format(self.order_id),
            'type': 'out_invoice',
            # 'narration': self.note,
            # 'currency_id': self.pricelist_id.currency_id.id,
            # 'campaign_id': self.campaign_id.id,
            # 'medium_id': self.medium_id.id,
            # 'source_id': self.source_id.id,
            'invoice_user_id': self.create_uid.id,
            # 'team_id': self.team_id.id,
            'partner_id': self.customer.id,
            # 'partner_shipping_id': self.partner_shipping_id.id,
            'invoice_partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            # 'fiscal_position_id': self.fiscal_position_id.id or self.partner_invoice_id.property_account_position_id.id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.order_id,
            'invoice_payment_ref': self.order_id,
            # 'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'invoice_line_ids': invoice_service_lines,
            'company_id': self.env.user.company_id.id,
        }
        if self.payment_method == 'on_credit':
            invoice_vals.update({'on_credit_invoice': True})
            print("Order Inv Values -> ", invoice_vals)
        return invoice_vals

    def _create_invoice(self):
        """
        Create Invoice and return invoice object
        :return:
        """
        invoice_model = self.env['account.move']
        invoice_data = self._prepare_invoice()
        print("BEFORE CREATING INVOICE")
        invoice = invoice_model.create(invoice_data)
        print("after CREATING INVOICE")

        return invoice

    # End of Invoice Section
    # ---------------------------------------------************************---------------------------------------------

    # ---------------------------------------------************************---------------------------------------------
    # Edits Section

    # End of Edits Section
    # ---------------------------------------------************************---------------------------------------------

    # ---------------------------------------------************************---------------------------------------------
    # Register Payment Section
    def _get_register_payment_lines(self):
        """
        Prepare invoice register payment lines to be created
        :return:
        """

        print("Register Payment Custody Entry")
        collector_driver = self._get_invoice_money_collection_driver()
        if not collector_driver:
            raise ValidationError(_("Something Wrong with the Drivers Assigned Kindly Check it"))

        petty_cash_account = self.env['account.account'].search([('is_custody_account', '=', True)])
        line_1 = (0, 0, {
            'account_id': petty_cash_account.id,
            'partner_id': collector_driver.address_home_id.id,
            'debit': self.invoice_id.amount_total,
        })

        line_2 = (0, 0, {
            'account_id': self.customer.property_account_receivable_id.id,
            'partner_id': self.customer.id,
            'credit': self.invoice_id.amount_total,
        })

        print("LINE1: ", line_1, "LINE2: ", line_2)

        return [line_1, line_2]

    def _prepare_register_payment_entry(self):
        """
        Prepare the dict of values to create the new invoice for payment register. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        # ensure a correct context for the _get_default_journal method and company-dependent fields
        self = self.with_context(default_company_id=self.company_id.id, force_company=self.company_id.id)
        journal = self.env['account.move'].with_context(default_type='entry')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (
                self.company_id.name, self.company_id.id))

        move_lines = self._get_register_payment_lines()

        entry_vals = {
            'ref': '{}'.format(self.order_id),
            'type': 'entry',
            'invoice_user_id': self.create_uid.id,
            'invoice_partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'line_ids': move_lines,
            'company_id': self.env.user.company_id.id,
        }
        return entry_vals

    # POS PAYMENT

    def _prepare_pos_payment_vals(self):
        """
        Create the payment values.
        :return: The payment values as a dictionary
        """

        payment_date = datetime.now()
        current_invoice = self.invoice_id
        amount = current_invoice.amount_residual
        journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)

        values = {
            'payment_date': payment_date,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'has_invoices': True,
            'payment_method_id': 1,
            'partner_id': self.customer.id,
            'amount': amount,
            'currency_id': current_invoice.currency_id.id,
            'journal_id': journal.id,
            'communication': '{} ({})'.format(current_invoice.name, self.order_id),
            'invoice_ids': [(6, 0, current_invoice.ids)],
            'partner_bank_account_id': self.invoice_id.invoice_partner_bank_id.id,
            'company_id': self.invoice_id.company_id.id,

        }

        return values

    def _prepare_bank_commission_entry(self):
        """
        Prepare bank charges entry lines
        :return: values as a dict
        """
        amount = self.shipping_fees * (self.bank_commission_fees / 100)

        # Check if commission fees is less than floor 2 then use the floor amount
        print("Commission Amount ", amount)
        if amount < 2.00:
            amount = 2.00

        journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)

        bank_account = self.env['account.account'].search([('is_default_bank_account', '=', True)])

        bank_commission_account = self.env['account.account'].search([('is_bank_commission_account', '=', True)])
        if not journal or not bank_account or not bank_commission_account:
            raise ValidationError("Missing Bank info account for bank commission")

        print("BANK ACCOUNT -> ", bank_account)
        print("BANK COMMISSION ACCOUNT -> ", bank_commission_account)

        line_1 = (0, 0, {
            'account_id': bank_account.id,
            'debit': amount,
        })

        line_2 = (0, 0, {
            'account_id': bank_commission_account.id,
            'credit': amount,
        })

        print("COMMISSION MOVES  LINE 1->", line_1)
        print("COMMISSION MOVES  LINE 2->", line_2)

        move_lines = [line_1, line_2]

        values = {
            'ref': '{}'.format(self.order_id),
            'type': 'entry',
            'invoice_user_id': self.create_uid.id,
            'invoice_partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'line_ids': move_lines,
            'company_id': self.env.user.company_id.id,

        }
        return values

    def register_payment(self, api_action=False):
        """
        Responsible to create journal entry in case of cash payment or
        creating a customer payment in case of pos machine payment
        for closing the invoice
        :param api_action:
        :return:
        """
        print("Register Payment Function called")

        if not self.trips_ids:
            raise ValidationError(_("No Trips Assigned Yet"))

        if self.payment_method in ['on_pickup', 'on_delivery']:
            if self.shipping_fees:

                if self.is_pos_payment:
                    # Case POS payment register money directly on bank account
                    print("POS Payment Section")
                    current_invoice = self.invoice_id
                    if not current_invoice:
                        raise ValidationError("No Invoice Found")

                    if current_invoice.invoice_payment_state == 'paid':
                        raise ValidationError("Invoice already paid")

                    if self.invoice_payment_collection:
                        raise ValidationError("Payment already has been created")

                    payment_model = self.env['account.payment']
                    payment_vals = self._prepare_pos_payment_vals()
                    payment = payment_model.create(payment_vals)

                    self.write({'invoice_payment_collection': payment.id})
                    self.toggle_order_payment_status()

                    # Create Bank Charge Entry
                    # Allowed order to be created and change status without checking the bank commission
                    if self.bank_commission_fees:

                        bank_entry = self.env['account.move'].create(self._prepare_bank_commission_entry())
                        self.write({'bank_commission_entry': bank_entry.id})
                        self.bank_commission_entry.action_post()
                    else:
                        print("no bank commission fees ->", self.bank_commission_fees)

                    if not api_action:
                        # Payment should be manually approved by accountant after being created thought api
                        payment.post()
                        # Assign the payment entry same account move
                        # as it will eventually refer to it in the account.payment

                    # payment_model_cxt = payment_model.with_context(
                    #     active_ids=current_invoice.ids, active_model='account.move', active_id=current_invoice.id)
                    #
                    # invoice_payment = payment_model_cxt.create(
                    #     {
                    #         'payment_date': datetime.now(),
                    #         'payment_type': 'inbound',
                    #         'partner_type': 'customer',
                    #         'has_invoices': True,
                    #         'payment_method_id': 1,
                    #         'partner_id': self.customer.id,
                    #         'amount': current_invoice.amount_total,
                    #         'currency_id': self.invoice_id.currency_id.id,
                    #         'journal_id': journal.id,
                    #         'communication': '{} ({})'.format(current_invoice.name, self.order_id),
                    #         'invoice_ids': [(6, 0, current_invoice.ids)],
                    #
                    #     }
                    # )

                    # self.write({'payment_collection_entry': self.invoice_id.id})

                else:
                    # Case Cash Payment register money on employee custody
                    print("Case Cash Payment")
                    current_invoice = self.invoice_id

                    if current_invoice.invoice_payment_state == 'paid':
                        raise ValidationError("Invoice already paid")

                    if self.payment_collection_entry:
                        raise ValidationError("Payment Entry already has been created")

                    entry_data = self._prepare_register_payment_entry()
                    entry_result = self.env['account.move'].create(entry_data)
                    self.write({'payment_collection_entry': entry_result.id})
                    self.payment_collection_entry.post()
            else:
                print("No shipping fees")
        else:
            # Case order is marked on_credit payment no action should be taken in that case
            # return 'On Credit Payment Order Non eligible to register invoice payment'
            raise ValidationError("On Credit Payment Order Non eligible to register invoice payment")
        return True

    # End of Payment Register Section
    # ---------------------------------------------************************---------------------------------------------

    # ---------------------------------------------************************---------------------------------------------
    # Other's Money Collection Section
    def _get_invoice_money_collection_driver(self):
        """
        Generic Function that return Driver who collected the money based on the order payment method
        Edit: based on the business logic the money collection driver will always be the delivery driver
        :return:
        """
        driver = None
        try:
            current_trips = self.trips_ids
            if self.payment_method == 'on_pickup':
                # Get Pickup Driver
                target_trip = current_trips.filtered(lambda r: r.trip_status == 'picked')
                print("Target Trip: ", target_trip)
                if not target_trip.trip_status == 'picked':
                    raise ValidationError("Trip data are Mis-configured")

                driver = target_trip.driver_id

            elif self.payment_method == 'on_delivery':
                # Get Delivery Driver
                target_trip = current_trips.filtered(lambda r: r.trip_status == 'delivered')
                if not target_trip.trip_status == 'delivered':
                    raise ValidationError("Trip data are Mis-configured")

                driver = target_trip.driver_id

        except IndexError:
            raise ValidationError(_("Something Wrong with the Drivers Assigned Kindly Check it"))
        except Exception as e:
            print('Exception: ', e)
        print("FINAL DRIVER TO RET: ", driver)
        return driver

    def _get_money_collection_entry_driver(self):
        """
        Get & return the driver responsible for the extra money collection
        based on the business logic flow it will always be the delivery driver
        :return: driver object
        """
        driver = None
        try:
            current_trips = self.trips_ids
            # Get Delivery Driver
            target_trip = current_trips.filtered(lambda r: r.trip_status == 'delivered')
            if not target_trip.trip_status == 'delivered':
                raise ValidationError("Trip data are Mis-configured (Missing Delivery Driver)")

            driver = target_trip.driver_id

        except IndexError:
            raise ValidationError(_("Something Wrong with the Drivers Assigned Kindly Check it"))
        except Exception as e:
            print('Exception: ', e)
            raise ValidationError(_("Something Wrong with the Drivers Assigned Kindly Check it\n{}".format(e)))

        print("Money Collection Driver: ", driver)
        return driver

    def _get_money_collection_entry_lines(self):
        """
        Prepare money collection entry lines to be created
        :return:
        """
        lines = []
        print("Preparing Money Collection Lines")
        print("Money collection payment method -> ", self.money_collection_payment_method)

        collector_driver = self._get_money_collection_entry_driver()
        print("Collector Driver -> ", collector_driver)
        if not collector_driver:
            raise ValidationError("Delivery Driver Not Assigned Yet")

        if self.money_collection_payment_method == 'cash':
            # Case Cash payment to driver

            petty_cash_account = self.env['account.account'].search([('is_custody_account', '=', True)])
            line_1 = (0, 0, {
                'account_id': petty_cash_account.id,
                'partner_id': collector_driver.address_home_id.id,
                'debit': self.money_collected,
            })
            lines.append(line_1)

        else:
            # No Need For Driver here entry will be reflected on bank account & customer directly
            # On money collect using pos add additional amount by the bank commission percentage
            #   Dr on bank account as amount will be at bank
            #       Cr additional to the bank commission account

            money_collected_bank_commission_fees = self.money_collected * (
                    self.money_collection_bank_commission_fees / 100)
            bank_account = self.env['account.account'].search([('is_default_bank_account', '=', True)])
            # Check if the commission is lower than 2.00 EGP then use the default value which is 2.00 EGP
            if money_collected_bank_commission_fees < 2.00:
                money_collected_bank_commission_fees = 2.00

            line_1 = (0, 0, {
                'account_id': bank_account.id,
                'debit': self.money_collected + money_collected_bank_commission_fees,
            })

            lines.append(line_1)

            # Entry line  3 bank commission account
            bank_commission_account = self.env['account.account'].search([('is_bank_commission_account', '=', True)])
            line_3 = (0, 0, {
                'account_id': bank_commission_account.id,
                'credit': money_collected_bank_commission_fees
            })

            lines.append(line_3)

        # Customer Data Fixed in both cases (pos_payment or not)
        money_collection_account = self.env['account.account'].search([('is_money_collection_account', '=', True)])
        line_2 = (0, 0, {
            'account_id': money_collection_account.id,
            'partner_id': self.customer.id,
            'credit': self.money_collected,
        })

        lines.insert(1, line_2)

        return lines

    def _prepare_money_collection_entry(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """

        self.ensure_one()
        # ensure a correct context for the _get_default_journal method and company-dependent fields
        self = self.with_context(default_company_id=self.company_id.id, force_company=self.company_id.id)
        if self.money_collection_payment_method == 'cash':
            journal = self.env['account.move'].with_context(default_type='entry')._get_default_journal()
        else:
            journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)

        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (
                self.company_id.name, self.company_id.id))

        move_lines = self._get_money_collection_entry_lines()

        entry_vals = {
            'ref': '{}'.format(self.order_id),
            'type': 'entry',
            'invoice_user_id': self.create_uid.id,
            'invoice_partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'line_ids': move_lines,
            'company_id': self.env.user.company_id.id,
        }
        return entry_vals

    def create_money_collection_entry(self, raise_exception=True):
        """
        Money Collection Action
        did user asked for pos machine yes:no
            if yes then the money should be automatically gone in my bank account
            if no then i should create entry
        IF NON POS ORDER:
            is the order payment method on_delivery -> get driver who delivered the order and assign to entry
            is the order payment method on_pickup -> get driver who picked-up and assign to entry
        :return:
        """
        # First check should be a driver who collected the money and money amount to be collected
        # else Don't Take any action
        print("Money Collection Function Called")

        if not self.money_collected:
            if raise_exception:
                raise ValidationError("No money to collect")
            else:
                return "No Money To Collect"

        if self.trips_ids:
            if not self.money_collection_entry:
                print("PREPARING DATA")
                entry_dict = self._prepare_money_collection_entry()
                account_move_model = self.env['account.move']
                entry_result = account_move_model.create(entry_dict)

                if entry_result:
                    self.write({'money_collection_entry': entry_result.id})
                    self.money_collection_entry.action_post()
            else:
                raise ValidationError(_("Entry Already Exists"))

        else:
            raise ValidationError(_("No Trips Assigned Yet"))

        return True

    # End Other's Money Collection Section
    # ---------------------------------------------************************---------------------------------------------


class BillOfLoadingLine(models.Model):
    _name = 'bill.of.loading.line'

    product_id = fields.Many2one('product.product', string='Product')
    currency_id = fields.Many2one('res.currency', string='Currency')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    description = fields.Text()
    service_type = fields.Selection(
        selection=[
            ('shipping', 'Shipping Service'),
            ('vat', 'Vat Service'),
            ('insurance', 'Insurance Service')
        ],
        string="Service Type", default='shipping'
    )
    bol_id = fields.Many2one('fastrak.bill.of.loading')


class BillOfLoadingTrips(models.Model):
    _name = 'bill.of.loading.trips'

    driver_id = fields.Many2one('hr.employee', domain=[('address_home_id', '!=', False)], track_visibility='onchange',
                                required=True)
    trip_status = fields.Selection(
        [
            ('picked', 'Picked Up'), ('inter_delivery', 'Intermediate delivery'), ('delivered', 'Delivered')
        ]
        , string='Status', default='picked', track_visibility='onchange'
    )
    trip_description = fields.Text()
    bol_id = fields.Many2one('fastrak.bill.of.loading')

    def create(self, vals_list):
        """
        Add Validation on trips
        :param vals_list:
        :return:
        """
        res = super(BillOfLoadingTrips, self).create(vals_list)

        if res:
            state = res.trip_status
            bol = res.bol_id
            if state and bol:
                if state == 'picked':
                    # Check First if there is no delivery state means order still have no delivery pickup action yet
                    if not bol.order_delivery_status:
                        bol.write({'order_delivery_status': 'picked'})
                    else:
                        raise ValidationError("Pick-Up Driver Already Assigned")

                elif state == 'delivered':
                    # Check if the existence of pickup driver first
                    if not bol.order_delivery_status == 'picked':
                        raise ValidationError("Missing Pickup Driver")
                    # Check order delivery state not delivered
                    if not bol.order_delivery_status == 'delivered':
                        bol.write({'order_delivery_status': 'delivered'})
                    else:
                        raise ValidationError("Delivery Driver Already Assigned")

        return res

    def write(self, vals):
        # TODO: CHECK URGENTLY
        res = super().write(vals)
        print("Editing Trip: {}".format(self.bol_id))
        if self.trip_status == 'picked':
            if not self.bol_id.order_delivery_status == 'picked':
                self.bol_id.write({'order_delivery_status': 'picked'})
            else:
                raise ValidationError("Pick-Up Driver Already Assigned")

        if self.trip_status == 'delivered':
            if not self.bol_id.order_delivery_status == 'picked':
                self.bol_id.write({'order_delivery_status': 'picked'})
            else:
                raise ValidationError("Pick-Up Driver Already Assigned")

        return res
