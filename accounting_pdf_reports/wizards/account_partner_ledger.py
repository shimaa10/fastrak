# -*- coding: utf-8 -*-

from odoo import fields, models, _


class AccountPartnerLedger(models.TransientModel):
    _inherit = "account.common.partner.report"
    _name = "account.report.partner.ledger"
    _description = "Account Partner Ledger"

    amount_currency = fields.Boolean("With Currency",
                                     help="It adds the currency column on report if the "
                                          "currency differs from the company currency.")
    reconciled = fields.Boolean('Reconciled Entries')
    specified_partner = fields.Many2one('res.partner', string='Partner Name')

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'reconciled': self.reconciled, 'amount_currency': self.amount_currency})
        if self.specified_partner:
            data['form'].update({'specified_partner': self.specified_partner.id})
        return self.env.ref('accounting_pdf_reports.action_report_partnerledger').report_action(self, data=data)