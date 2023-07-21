from odoo import models, fields, api, _
from odoo.tools.date_utils import datetime
from odoo.tools.float_utils import float_round
from odoo.exceptions import ValidationError, UserError


class WithDrawRequest(models.Model):
    _name = 'withdraw.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'fastrak customer withdraw request model'
    _rec_name = 'customer'

    STATUS_LIST = [
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('canceled', 'Canceled')
    ]

    OPERATION_STATUS_LIST = [
        ('draft', 'Draft'),
        ('finished', 'Finished'),
        ('canceled', 'Canceled')
    ]

    CUSTOMER_COLLECTION_TYPE = [
        ('1', 'Collect From Bank'),
        ('2', 'Collect From Hub'),
        ('3', 'Collect From Home'),
        ('4', 'Collect From E-Wallet'),
        ('5', 'Collect From Pickup'),
    ]

    active = fields.Boolean(default=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env['res.company'].browse(
        self.env['res.company']._company_default_get('withdraw.request').id), readonly=True)

    request_timestamp = fields.Datetime(default=lambda self: datetime.now(), readonly=True, string='Request Time')
    status = fields.Selection(STATUS_LIST, track_visibility='onchange', required=True, default='draft', readonly=True)
    operation_status = fields.Selection(OPERATION_STATUS_LIST, track_visibility='onchange', default='draft',
                                        readonly=True)

    customer = fields.Many2one('res.partner', required=True, track_visibility='onchange',
                               domain=[('customer_rank', '>', 0)])
    customer_id = fields.Integer(string='Customer ID', related='customer.id', readonly=True)

    amount = fields.Float(track_visibility='onchange')

    revenue_type = fields.Selection(
        selection=[('amount', 'Amount'), ('percent', 'Percentage')],
        track_visibility='onchange'
    )

    revenue_percentage = fields.Float(track_visibility='onchange')
    revenue_amount = fields.Float(track_visibility='onchange', readonly=True)
    revenue_vat_amount = fields.Float(track_visibility='onchange')

    # Invoice & Payment Section
    payment_journal = fields.Many2one('account.journal', track_visibility='onchange',
                                      domain=[('type', 'in', ('bank', 'cash'))])
    # Revenue Invoice
    invoice = fields.Many2one('account.move', track_visibility='onchange', domain=[('move_type', '=', 'out_invoice')],
                              readonly=True, string='Invoice')

    # Entry for the invoice payment
    # Case of cash payment to customer
    invoice_payment = fields.Many2one('account.payment', track_visibility='onchange', readonly=True,
                                      string='Invoice Payment')

    # Entry for the customer payment to deduct amount from the other's money collection account

    customer_withdraw_entry = fields.Many2one('account.move', track_visibility='onchange', readonly=True,
                                              domain=[('move_type', '=', 'entry')], string='Customer Withdraw Entry')

    note = fields.Text(track_visibility='onchange', string='Notes')
    order_ids = fields.Text(track_visibility='onchange', string='Notes', readonly=True)
    customer_collection_type = fields.Selection(string='Collection Type', track_visibility='onchange',
                                                selection=CUSTOMER_COLLECTION_TYPE)

    def _get_report_filename(self):
        return '{} Withdraw Request'.format(self.customer.display_name)

    @api.constrains('amount')
    def check_amount(self):
        if self.amount <= 0:
            raise ValidationError("Amount Can't be less or equal to 0")

    @api.constrains('revenue_percentage')
    def check_revenue_percentage(self):
        for rec in self:
            if rec.revenue_type == 'percent':
                if 0 > rec.revenue_percentage or rec.revenue_percentage > 100:
                    raise ValidationError("Incorrect Revenue Percentage")

    def _get_amount_rounded(self, amount):
        """
        Round the revenue amount with the internal odoo float_round function
        :return:
        """
        return float_round(amount, precision_digits=0)

    def _get_tax_percentage_amount(self):

        return (self.env['account.tax'].search(
            [('active', '=', True), ('type_tax_use', '=', 'sale'), ('amount_type', '=', 'percent')]
        ).amount) / 100

    @api.onchange('revenue_amount')
    def compute_vat_amount(self):
        self.revenue_vat_amount = self.revenue_amount * self._get_tax_percentage_amount()

    @api.onchange('amount')
    def calculate_service_revenue_amount(self):
        for rec in self:
            commission = self.env['withdraw.request.commission'].search(
                [
                    ('range_from', '<=', rec.amount), ('range_to', '>=', rec.amount)
                ], limit=1
            )

            rec.revenue_type = commission.commission_type
            rec.revenue_amount = commission.commission_amount
            rec.revenue_percentage = commission.commission_percentage

            if rec.revenue_type == 'percent':
                rec.revenue_amount = self._get_amount_rounded((rec.revenue_percentage / 100) * rec.amount)

    # ############################################ Invoice Section #############################################
    def _get_tax_lines(self):

        return self.env['account.tax'].search(
            [('active', '=', True), ('type_tax_use', '=', 'sale'), ('amount_type', '=', 'percent')]
        ).id

    def _get_customer_invoice_lines(self):
        self.ensure_one()
        """
        Prepare invoice lines to be created
        :return:
        """

        money_collection_service_product = self.env['product.product'].search([('is_main_withdraw_charge', '=', True)])
        if not money_collection_service_product:
            raise ValidationError(_("Missing Main Service Charge"))

        service_price = self.revenue_amount

        # Get and check cost center for penalty product
        line_category = money_collection_service_product.product_tmpl_id.categ_id
        if line_category.cost_centers_id:
            cost_center = line_category.cost_centers_id.id
        else:
            cost_center = False

        if self.company_id.activate_vat_calculation:
            line_data = (0, 0, {
                'product_id': money_collection_service_product.id,
                'name': '{} - Withdrawal Fees'.format(self.customer.display_name),
                'quantity': 1,
                'price_unit': service_price,
                # Add Cost Center To Line
                'cost_centers_id': cost_center,
                'tax_ids': [self._get_tax_lines()]

            })
        else:
            line_data = (0, 0, {
                'product_id': money_collection_service_product.id,
                'name': '{} - Withdrawal Fees'.format(self.customer.display_name),
                'quantity': 1,
                'price_unit': service_price,
                # Add Cost Center To Line
                'cost_centers_id': cost_center,
            })

        return [line_data]

    def _prepare_customer_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        # ensure a correct context for the _search_default_journal method and company-dependent fields
        self = self.with_context(default_company_id=self.company_id.id, force_company=self.company_id.id)
        journal = self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.company_id.id)],limit=1)
        if not journal or journal.type != 'sale':
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (
                self.company_id.name, self.company_id.id))

        invoice_service_lines = self._get_customer_invoice_lines()

        invoice_values = {
            'ref': 'Money Collection Invoice {}'.format(self.customer.display_name),
            'move_type': 'out_invoice',
            'invoice_user_id': self.create_uid.id,
            'partner_id': self.customer.id,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': 'Money Collection Invoice {}'.format(self.customer.display_name),
            'payment_reference': 'Money Collection Invoice {}'.format(self.customer.display_name),
            'invoice_line_ids': invoice_service_lines,
            'company_id': self.env.user.company_id.id,
        }
        return invoice_values

    # ############################################ End Invoice Section #############################################

    def _get_customer_withdraw_payment_entry_lines(self):
        lines = []

        # Customer Other's money collection account Fixed in both cases (cash or bank)

        money_collection_account = self.env['account.account'].search([('is_money_collection_account', '=', True)])
        if not money_collection_account:
            raise ValidationError(_("Missing Money Collection Account, Please Add it from Chart of Accounts and check the box 'Is Money Collection Account'"))
        line_1 = (0, 0, {
            'account_id': money_collection_account.id,
            'partner_id': self.customer.id,
            'debit': self.amount,
        })
        lines.append(line_1)

        if self.payment_journal.type == 'cash':
            line_2 = (0, 0, {
                'account_id': self.payment_journal.inbound_payment_method_line_ids[:1].payment_account_id.id,
                'credit': self.amount
            })

        elif self.payment_journal.type == 'bank':
            line_2 = (0, 0, {
                'account_id': self.payment_journal.inbound_payment_method_line_ids[:1].payment_account_id.id,
                'credit': self.amount
            })

        lines.append(line_2)

        return lines

    def _prepare_customer_withdraw_payment_entry(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        # ensure a correct context for the _search_default_journal method and company-dependent fields
        self = self.with_context(default_company_id=self.company_id.id, force_company=self.company_id.id)
        journal = self.env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', self.company_id.id)], limit=1)
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (
                self.company_id.name, self.company_id.id))

        move_lines = self._get_customer_withdraw_payment_entry_lines()
        entry_vals = {
            'ref': '{} Money Withdraw'.format(self.customer.display_name),
            'move_type': 'entry',
            'invoice_user_id': self.create_uid.id,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': self.payment_journal.id,  # company comes from the journal
            'line_ids': move_lines,
            'company_id': self.env.user.company_id.id,
        }
        return entry_vals

    def _prepare_invoice_payment_record_values(self):
        """
        Create the payment values for the invoice.
        :return: The payment values as a dictionary
        """
        self.ensure_one()
        payment_date = datetime.now()

        values = {
            'date': payment_date,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            # 'has_invoices': True,
            'payment_method_id': 1,
            'partner_id': self.customer.id,
            # 'amount': self.revenue_amount + self.revenue_vat_amount,
            'amount': self.invoice.amount_residual,
            'currency_id': self.company_id.currency_id.id,
            'journal_id': self.payment_journal.id,
            'ref': '{} Money Collection Revenue Payment'.format(self.customer.display_name),
            'reconciled_invoice_ids': [(6, 0, [self.invoice.id])],
            # 'partner_bank_account_id': self.invoice_id.partner_bank_id.id,
            'company_id': self.company_id.id,

        }

        return values

    def _send_withdraw_notification(self, message):
        """
        Send Notification Message To withdrawal assistance that
        :param message:
        :return:
        """
        withdrawal_assistance_group = self.env.ref('fastrak.withdrawal_assistant')

        withdrawal_assistance_users = self.env['res.users'].search(
            [('groups_id', '=', withdrawal_assistance_group.id)]
        )

        notification_ids = []
        for user in withdrawal_assistance_users:
            notification_ids.append((0, 0, {
                'res_partner_id': user.partner_id.id,
                'notification_type': 'inbox'}))

        self.message_post(body=message, message_type='comment', subtype_id=self.env.ref('mail.mt_comment').id,
                          notification_ids=notification_ids)

    def operation_confirm_payment(self, api_request=False):
        """
        Toggle operation status based on the received request from the operation panel application throught API
        :return:
        """
        self.operation_status = 'finished'
        self._send_withdraw_notification(
            'Withdraw request {} for customer {} has been Finished by operation side'.format(
                self.id, self.customer.display_name)
        )

        if api_request:
            return True

    def _create_invoice_payment(self):
        """
        Create and attach the invoice payment to the record and post the payment

        :return:
        """
        payment_model = self.env['account.payment']
        payment_vals = self._prepare_invoice_payment_record_values()
        payment = payment_model.create(payment_vals)
        self.invoice_payment = payment.id
        self.invoice_payment.action_post()

    def request_invoice_creation(self):
        """
        :return:
        """

        if not self.invoice:
            account_move = self.env['account.move'].create(self._prepare_customer_invoice())
            self.invoice = account_move.id
            self.invoice.action_post()
        else:
            raise UserError(_("Invoice already has been created"))

    def _create_withdraw_payment_entry(self):
        """
        Create customer withdraw payment entry and attach it to the current record
        :return:
        """
        entry = self.env['account.move'].create(self._prepare_customer_withdraw_payment_entry())
        self.customer_withdraw_entry = entry.id
        self.customer_withdraw_entry.action_post()

    def request_payment_entries_creation(self):
        """
        Create all payment Entries
        :return:
        """

        self.ensure_one()
        if not self.payment_journal:
            raise ValidationError(_("Missing Payment Journal"))
        if not self.invoice:
            raise ValidationError(_("Missing Invoice"))

        if self.payment_journal.type not in ['bank', 'cash']:
            raise ValidationError(_("Wrong Payment Journal"))

        if not self.invoice_payment:
            self._create_invoice_payment()
        else:
            raise ValidationError(_("Payment Invoice ALready Created"))
        if not self.customer_withdraw_entry:
            self._create_withdraw_payment_entry()
        else:
            raise ValidationError(_("Payment Entry Already Created"))

    def confirm_request_payment(self):
        """
        Should be pressed when all payment has been done
        :return:
        """
        self.status = 'done'

    def cancel_request_payment(self):
        self.status = 'canceled'

    def reset_request_payment(self):
        self.status = 'draft'

    @api.model
    def create(self, vals_list):
        res = super().create(vals_list)
        res._send_withdraw_notification(
            'Withdraw request {} for customer {} has been created by operation'.format(
                res.id, res.customer.display_name)
        )
        return res
