from odoo import models, fields, api

from odoo.tools.misc import get_lang
import datetime
import calendar


class FastrakCrmTargetReport(models.TransientModel):
    _name = "fastrak_crm.report.crm.target"
    _description = "CRM Target Report"

    @api.model
    def _get_default_start_date(self):
        current_date = datetime.date.today()
        return datetime.date(current_date.year, current_date.month, 1)

    @api.model
    def _get_default_end_date(self):
        current_date = datetime.date.today()
        month_last_day = calendar.monthrange(current_date.year, current_date.month)[1]

        return datetime.date(current_date.year, current_date.month, month_last_day)

    date_from = fields.Date(string='From', default=_get_default_start_date)
    date_to = fields.Date(string='To', default=_get_default_end_date)

    sales_person = fields.Many2one('res.users', string='Sales Person')
    sales_team = fields.Many2one('crm.team')

    def print_report(self):
        data = {
            'model': self.env.context.get('active_model', 'fastrak_crm.report.crm.target'),
            'ids': self.ids,
            'form': self.read()[0]
        }

        return self.env.ref('fastrak_crm.action_report_crm_target_report').with_context(
            discard_logo_check=True).report_action(self, data=data)
