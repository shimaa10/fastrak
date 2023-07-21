from odoo import models, fields


class ProductCategory(models.Model):
    """docstring for ProductCategory"""
    _inherit = 'product.category'

    cost_centers_id = fields.Many2one('cost.centers', string='Cost Center')
