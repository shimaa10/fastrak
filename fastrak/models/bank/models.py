from odoo import models, fields, api


class CustomResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'
    _sql_constraints = [('unique_iban_number', 'UNIQUE(iban_number)', 'IBAN Must Be Unique')]
    iban_number = fields.Char(string='IBAN', unique=True)
