from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError

from odoo.tools.date_utils import date
from odoo.tools.float_utils import float_round


class GroupInvoice(models.Model):
    _name = 'fastrak.group.invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Fastrak Group Invoice Model'
    _rec_name = 'customer'

    STATE_SELECTION = [
        ('unpaid', 'Un Paid'),
        ('delayed', 'Delayed'),
        ('paid', 'Paid')
    ]

    customer = fields.Many2one(
        'res.partner',
        domain=[('customer_rank', '>', 0)],
        track_visibility='onchange',
        required=True
    )

    from_date = fields.Date(required=True)
    to_date = fields.Date(required=True)

    invoice_ids = fields.One2many(
        'fastrak.group.invoice.line', 'group_invoice_id', track_visibility='onchange', string='Customer Invoices'
    )

    penalty_invoice = fields.Many2one(
        'account.move',
        track_visibility='onchange',
        domain=[('type', '=', 'out_invoice'), ('partner_id', '=', 'customer')]
    )

    print_date = fields.Date(track_visibility='onchange', string='Print Date', required=True,
                             help='The Group invoice issuance date', default=lambda self: date.today())

    due_at = fields.Date(track_visibility='onchange', string='Due At', required=True,
                         help='Max Number of days to pay the group invoice')

    penalty_amount = fields.Float(track_visibility='onchange')
    penalty_rate = fields.Float(track_visibility='onchange', default=1, required=True, string='Penalty Rate (%)', )
    total_amount = fields.Float(track_visibility='onchange', compute="_compute_total_amount")
    total_discount = fields.Float(track_visibility='onchange', readonly=True)
    total_to_collect = fields.Float(track_visibility='onchange', compute="_compute_total_to_collect")

    state = fields.Selection(STATE_SELECTION, default='unpaid', track_visibility='onchange', readonly=True)
    note = fields.Html(default='')
    penalty_terms_and_condition = fields.Html(compute='_compute_payment_terms', inverse='_inverse_payment_terms')

    def _get_report_filename(self):
        for rec in self:
            return '{} Group Invoice'.format(rec.customer.display_name)

    def _get_footer_totals(self):
        """
        Get Footer Amount totals for group credit invoice report
        :return:
        """

        for rec in self:
            # each records represents a group invoice
            total_discount = rec.total_discount
            total_vat = 0
            current_currency = rec.env.user.company_id.currency_id

            # for invoice_line in rec.invoice_ids:
            #     for line in invoice_line.invoice.invoice_line_ids:
            #         total_discount += (line.price_unit * line.quantity) - line.price_subtotal

            gross_total_amount = rec.total_amount + total_discount
            net_total_amount = rec.total_amount

            result = {

                'gross_total_amount': gross_total_amount,
                'gross_total_amount_in_words': current_currency.amount_to_text(gross_total_amount),

                'total_discount': total_discount,
                'total_discount_in_words': current_currency.amount_to_text(total_discount),

                'total_vat': total_vat,

                'net_total_amount': net_total_amount,
                'net_total_amount_in_words': current_currency.amount_to_text(net_total_amount),

            }
            return result

    def print_invoices(self):
        """
        Print all available invoices by calling their report action
        :return:
        """
        for rec in self:
            target_invoices_ids = [inv_line.invoice.id for inv_line in rec.invoice_ids]
            if target_invoices_ids:
                return self.env.ref('fastrak.action_custom_account_invoice_report').with_context(
                    discard_logo_check=True).report_action(target_invoices_ids)

    def _compute_payment_terms(self):
        for rec in self:
            rec.penalty_terms_and_condition = rec.env.user.company_id.penalty_terms

    def _inverse_payment_terms(self):
        pass

    @api.constrains('from_date', 'to_date')
    def _check_from_and_to_date(self):
        """
        Check Dates
        :return:
        """
        for rec in self:
            if rec.to_date < rec.from_date:
                raise ValidationError(_("To Date can't be before From date"))

    @api.constrains('print_date', 'due_at')
    def _check_due_and_print_date(self):
        """
        Check Due At & Print date
        :return:
        """
        for rec in self:
            if rec.due_at < rec.print_date:
                raise UserError(_("Due At can't be less than print date"))

    @api.constrains('penalty_rate')
    def _check_penalty_rate(self):
        """
        Check For Penalty Rate
        :return:
        """
        for rec in self:
            if 0 > rec.penalty_rate or rec.penalty_rate > 100:
                raise ValidationError(_("Penalty rate can only range from  0 till 100"))

    @api.constrains('penalty_amount')
    def _check_penalty_amount(self):
        for rec in self:
            if rec.penalty_amount < 0:
                raise UserError(_("Penalty Amount can't be less than 0"))

    @api.depends('invoice_ids.amount')
    def _compute_total_amount(self):
        """
        Compute the group invoice total amount based on the sum for all invoice_ids found
        :return:
        """
        for rec in self:
            rec_inv_total = 0
            for inv in rec.invoice_ids:
                rec_inv_total += inv.amount

            rec.total_amount = rec_inv_total

    @api.depends('invoice_ids.amount', 'total_amount', 'penalty_amount')
    def _compute_total_to_collect(self):
        for rec in self:
            rec.total_to_collect = rec.total_amount + rec.penalty_amount

    def _check_not_in_old_group_invoice(self, inv):
        """
        Check that invoice is not included in any other group invoice record made for that customer
        :param inv:
        :return:
        """
        old_group_invoice_records = self.search([('customer', '=', self.customer.id), ('id', '!=', self.id)])

        for grp in old_group_invoice_records:
            for line in grp.invoice_ids:
                if line.invoice.id == inv.id:
                    return False
        return True

    def _get_customer_credit_invoices(self):
        """
        Retrieve Current Customer Credit Invoices
        based on customer,on_credit_invoice,state,date range
        :return:
        """

        for rec in self:

            customer_invoices = rec.env['account.move'].search(
                [
                    ('partner_id', '=', rec.customer.id),
                    ('create_date', '>=', rec.from_date),
                    ('create_date', '<=', rec.to_date),
                    ('on_credit_invoice', '=', True),
                    ('state', '=', 'posted'),
                    ('invoice_payment_state', '=', 'not_paid')
                ]
            )

            # Step 1 Reset all old customer invoices
            rec.write({'invoice_ids': [(5,)]})

            # Step 2 Assign the new invoices
            customer_invoice_lines = []
            total_amount = 0
            for inv in customer_invoices:
                if rec._check_not_in_old_group_invoice(inv):
                    # Using Amount Residual here and at the group invoice line to ensure that,
                    # the amount taken is the final left amount for each invoice as client
                    # may have paid a part of that invoice and kept the left amount open as on credit invoice
                    customer_invoice_lines.append((0, 0, {'invoice': inv.id, 'amount': inv.amount_total}))
                    total_amount += inv.amount_total

            print("*" * 160)
            print("Invoices Found -> ", customer_invoices)
            print("Lines ids ->", customer_invoice_lines)
            print("Total Amount ->", total_amount)
            print("*" * 160)

            rec.write({'invoice_ids': customer_invoice_lines, 'total_amount': total_amount})

    def _calculate_penalty_amount(self, penalty_days):
        """
        Calculate penalty amount
        :return:
        """
        print("Called internal calculate_penalty_amount function")
        for rec in self:
            rec.penalty_amount = float_round(penalty_days * (rec.total_amount * (rec.penalty_rate / 100)),
                                             precision_digits=0)

    def _toggle_state_delayed(self):
        """
        Change state to delayed
        :return:
        """
        self.ensure_one()
        self.state = 'delayed'

    def calculate_penalty(self):
        """
        Calculate delay penalty interface
        :return:
        """
        today = date.today()
        for rec in self:
            target_penalty_days = today - rec.due_at
            rec._calculate_penalty_amount(target_penalty_days.days)

    def scheduled_penalty_calculator(self):
        """
        Cron job function to calculate penalty for delayed and unpaid group invoice
        :return:
        """

        today = date.today()
        target_records = self.search([('state', 'in', ('unpaid', 'delayed'))]).filtered(
            lambda record: (today - record.due_at).days > 0)

        for rec in target_records:
            # Call internal calculate penalty function
            rec._toggle_state_delayed()
            rec.calculate_penalty()

    def _get_penalty_service_lines(self):
        """
        Prepare penalty invoice lines to be created
        :return:
        """
        service_line_ids = []
        # Get and check penalty product
        penalty_charge_product = self.env['product.product'].search([('is_main_penalty_charge', '=', True)])
        if not penalty_charge_product:
            raise ValidationError(_("Missing Penalty Charge Service"))

        # Get and check cost center for penalty product
        line_category = penalty_charge_product.product_tmpl_id.categ_id
        if line_category.cost_centers_id:
            cost_center = line_category.cost_centers_id
        else:
            cost_center = None

        line_data = (0, 0, {
            'product_id': penalty_charge_product.id,
            'name': "Invoice Payment Delay Penalty",
            'quantity': 1,
            'price_unit': self.penalty_amount,
            # Add Cost Center To Line
            'cost_centers_id': cost_center.id
        })

        service_line_ids.append(line_data)
        return service_line_ids

    def _prepare_penalty_invoice_lines(self):
        """
            Prepare the dict of values to create the new invoice for a sales order. This method may be
            overridden to implement custom invoice generation (making sure to call super() to establish
            a clean extension chain).
            """
        self.ensure_one()
        # ensure a correct context for the _get_default_journal method and company-dependent fields
        self = self.with_context(default_company_id=self.env.user.company_id.id,
                                 force_company=self.env.user.company_id.id)
        journal = self.env['account.move'].with_context(default_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (
                self.env.user.company_id.name, self.env.user.company_id.id))

        invoice_service_lines = self._get_penalty_service_lines()

        invoice_values = {
            'ref': 'Penalty Invoice {}'.format(self.customer.display_name),
            'type': 'out_invoice',
            'narration': self.note,
            'invoice_user_id': self.create_uid.id,
            'partner_id': self.customer.id,
            'invoice_partner_bank_id': self.env.user.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': 'Penalty Invoice {}'.format(self.customer.display_name),
            'invoice_payment_ref': 'Penalty Invoice {}'.format(self.customer.display_name),
            'invoice_line_ids': invoice_service_lines,
            'company_id': self.env.user.company_id.id,
        }
        return invoice_values

    def create_penalty_invoice(self):

        invoice_model = self.env['account.move']
        for rec in self:
            if rec.penalty_amount:
                # first check if there is a penalty
                if not rec.penalty_invoice:
                    # second check if there is no penalty invoice then create it

                    penalty_invoice = invoice_model.create(rec._prepare_penalty_invoice_lines())
                    penalty_invoice.post()
                    rec.write({'penalty_invoice': penalty_invoice.id})
                else:
                    # second check if there is invoice then update the penalty if invoice not yet paid
                    if rec.penalty_invoice.invoice_payment_state == 'not_paid':
                        # reset to draft & clear invoice lines
                        rec.penalty_invoice.button_draft()
                        rec.penalty_invoice.invoice_line_ids = [(5,)]

                        # add new invoice lines & post invoice again
                        rec.penalty_invoice.invoice_line_ids = rec._get_penalty_service_lines()
                        rec.penalty_invoice.post()

                    else:
                        raise UserError(_("Invoice already has been paid"))

            else:
                raise UserError(_("No Penalty Found"))

    ###################################################################################################################
    # Button Actions
    def generate_group_invoice(self):
        print("Generating Group Invoices")
        self._get_customer_credit_invoices()

    def confirm_group_invoice_payment(self):
        """
        Confirm group invoice payment to ignore penalty amount to be recomputed from the cron job
        :return:
        """
        for rec in self:
            rec.write({'state': 'paid'})

    # End Button Actions
    ###################################################################################################################


class GroupInvoiceLine(models.Model):
    _name = 'fastrak.group.invoice.line'

    invoice = fields.Many2one('account.move', domain=[('type', '=', 'out_invoice')])
    amount = fields.Float(compute='_compute_amount', string="Amount")

    group_invoice_id = fields.Many2one('fastrak.group.invoice')

    def _compute_amount(self):
        for line in self:
            line.amount = line.invoice.amount_total
