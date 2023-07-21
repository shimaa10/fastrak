# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CustomCompany(models.Model):
    _inherit = 'res.company'
    company_report_header = fields.Binary()
    company_report_footer = fields.Binary()
    bank_details = fields.Html()
    penalty_terms = fields.Html()
    activate_vat_calculation = fields.Boolean()
