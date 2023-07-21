# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import ValidationError


class AccountBalanceReport(models.TransientModel):
    _inherit = "account.common.account.report"
    _name = 'account.trial.balance.report'
    _description = 'Trial Balance Report'

    journal_ids = fields.Many2many('account.journal', 'account_balance_report_journal_rel', 'account_id', 'journal_id',
                                   string='Journals', required=True, default=[])

    def _print_report(self, data):
        # Check that date must be filled
        if not data.get('form').get('date_from') or not data.get('form').get('date_to'):
            raise ValidationError("You must select date From & To")

        data = self.pre_print_report(data)
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref('trial_balance_report.action_trial_balance_report').report_action(records, data=data)
