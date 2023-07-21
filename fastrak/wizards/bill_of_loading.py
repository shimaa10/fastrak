from odoo import models, fields
from odoo.tools.misc import get_lang
from ..models.bill_of_loading.bill_of_loading import FastrakBillOfLoading


class FastrakReportBillofLoading(models.TransientModel):
    _name = "fastrak.report.bill.of.loading"
    _description = "Bill of Loading Report"

    date_from = fields.Date()
    date_to = fields.Date()

    target_partner = fields.Many2one('res.partner', string='Partner')

    order_status = fields.Selection(FastrakBillOfLoading.STATUS_LIST)

    def print_report(self):
        data = {
            'model': self.env.context.get('active_model', 'fastrak.report.bill.of.loading'),
            'ids': self.ids,
            'form': self.read()[0]
        }

        return self.env.ref('fastrak.action_report_bill_of_loading').with_context(
            discard_logo_check=True).report_action(self, data=data)
