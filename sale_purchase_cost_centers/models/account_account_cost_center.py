from odoo import models, fields


class AccountAccount(models.Model):
    """docstring for AccountAccount"""
    _inherit = 'account.account'

    required_cost_center = fields.Boolean()
