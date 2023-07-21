from odoo import models, fields
from odoo.tools.misc import get_lang


class FastrakReportBillofLoading(models.TransientModel):
    _name = "fastrak.report.group.invoice"
    _description = "Group Invoice Report"

    date_from = fields.Date()
    date_to = fields.Date()

    target_partner = fields.Many2one('res.partner', string='Partner')
    STATE_SELECTION = [('draft', 'Draft'), ('posted', 'posted'), ('cancel', 'Cancel')]
    state = fields.Selection(selection=STATE_SELECTION, default='draft')

    def print_report(self):
        data = {
            'model': self.env.context.get('active_model', 'fastrak.report.group.invoice'),
            'ids': self.ids,
            'form': self.read()[0]
        }

        return self.env.ref('fastrak.action_report_group_invoice').with_context(
            discard_logo_check=True).report_action(self, data=data)
