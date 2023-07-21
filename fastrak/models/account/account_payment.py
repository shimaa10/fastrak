from odoo import models


class CustomPayment(models.Model):
    _inherit = 'account.payment'

    def _check_bol_invoice_payment(self):
        """
        Check invoice payment and toggle BOL order payment status after posting payment
        :return:
        """
        invoice_ids = self.invoice_ids
        if invoice_ids:
            bol_obj = self.env['fastrak.bill.of.loading'].search([('invoice_id', '=', invoice_ids[0].id)])
            if bol_obj:
                bol_obj.toggle_order_payment_status()

    def post(self):
        res = super(CustomPayment, self).post()
        self._check_bol_invoice_payment()
        return res
