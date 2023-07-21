from odoo import models, fields, api
from odoo.exceptions import ValidationError

from translate import Translator

translator = Translator(to_lang="Arabic")


class CustomAccountMove(models.Model):
    _inherit = 'account.move'
    print_discount = fields.Boolean(string='Print Discount', default=False)
    cancellation_reason = fields.Many2one('cancellation.reason', track_visibility='onchange')
    refund_reason_comment = fields.Text(track_visibility='onchange', string='Refund Reason')

    audit_and_lock = fields.Boolean(default=False)
    on_credit_invoice = fields.Boolean(default=False)

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(CustomAccountMove, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
    #                                                          submenu=submenu)
    #     # print("res:", res)
    #     if view_type == 'form':
    #         print(res.keys(), '\n')
    #         print(res['toolbar'])
    #         print(res['arch'])
    #         # res contains the view form, and you can manipulate res string, as you desired.
    #     return res

    def audit_and_lock_move(self):
        self.ensure_one()
        self.write({'audit_and_lock': True})

    def write(self, vals):
        if self.audit_and_lock:
            raise ValidationError("Can't Edit Move After Being Audited")
        return super(CustomAccountMove, self).write(vals)

    def button_cancel(self):
        if not self.cancellation_reason:
            raise ValidationError("Cancellation Reason Should be Added First")
        return super().button_cancel()

    amount_total_words_ar = fields.Char()
    amount_untaxed_words_ar = fields.Char()

    @api.depends('amount_total')
    def _compute_amount_total_words(self):

        for invoice in self:
            invoice.amount_total_words = invoice.currency_id.amount_to_text(invoice.amount_total)
            # invoice.amount_total_words_ar = translator.translate(invoice.amount_total_words)

    @api.depends('amount_untaxed')
    def _compute_amount_untaxed_words(self):
        for invoice in self:
            invoice.amount_untaxed_words = invoice.currency_id.amount_to_text(invoice.amount_untaxed)
            # invoice.amount_untaxed_words_ar = translator.translate(invoice.amount_untaxed_words)

    amount_total_words = fields.Char("Total (In Words)", compute="_compute_amount_total_words")

    amount_untaxed_words = fields.Char("Total (In Words)", compute="_compute_amount_untaxed_words")

    def _get_bol(self, invoice_id):
        """
        Return BOL related that contains the target invoice
        :param invoice_id:
        :return:
        """
        bol_ob = self.env['fastrak.bill.of.loading'].search([('invoice_id', '=', invoice_id)])
        return bol_ob

    def get_bol_info(self):
        """
        Get required info from the BOL
        :return:
        """
        delivery_time_selection_dict = {'rushed': 'Rushed', 'same': 'Same Day', 'next': 'Next Day'}
        delivery_type_selection_dict = {'in': 'Inside City', 'out': 'Outside City'}

        for invoice in self:
            bol = self._get_bol(invoice.id)
            if bol:
                result = {
                    'weight': bol.weight,
                    'delivery_time': delivery_time_selection_dict.get(bol.delivery_time),
                    'delivery_type': delivery_type_selection_dict.get(bol.delivery_type),
                    'src_city': bol.src_city,
                    'dst_city': bol.dst_city,
                    'number_of_pieces': bol.number_of_pieces
                }
                # if bol.delivery_type == 'out':
                #     result['src_city'] = bol.src_city
                #     result['dst_city'] = bol.dst_city
            else:
                result = {'weight': '', 'delivery_time': '', 'delivery_type': '', 'number_of_pieces': '',
                          'src_city': '', 'dst_city': ''}
            return result

    def _get_discounted_amount_lines(self):
        for rec in self:
            # Loop of 1 always as it is being called on single invoice
            discount = 0
            discounted_lines = rec.invoice_line_ids.filtered(
                lambda x: x.product_id.product_tmpl_id.is_main_discount_service)

            for line in discounted_lines:
                discount += -(line.price_subtotal)
        return discount
