from odoo import models, fields


class BolProduct(models.Model):
    _inherit = 'product.product'

    bol_line = fields.Many2one('fastrak.bill.of.loading')
