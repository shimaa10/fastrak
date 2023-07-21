from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WithdrawRequestCommission(models.Model):
    _name = 'withdraw.request.commission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'fastrak customer withdraw request commission'
    _rec_name = 'commission_type'

    _sql_constraints = [("unique_commission_range", "unique(range_from,range_to)", "Can't have same range duplicated")]

    active = fields.Boolean(default=True)

    COMMISSION_TYPES = [('amount', 'Amount'), ('percent', 'Percentage')]

    commission_type = fields.Selection(selection=COMMISSION_TYPES, required=True, track_visibility='onchange')

    commission_amount = fields.Float(track_visibility='onchange')

    commission_percentage = fields.Float(track_visibility='onchange')

    range_from = fields.Float(required=True, track_visibility='onchange')

    range_to = fields.Float(required=True, track_visibility='onchange')

    @api.constrains('commission_percentage')
    def _check_commission_percentage(self):
        for rec in self:
            if rec.commission_type == 'percent' and rec.commission_percentage:
                if 0 > rec.commission_percentage or rec.commission_percentage > 100:
                    raise UserError(_("Commission Rate can't be less than 0 or higher than 100"))

    @api.constrains('commission_amount')
    def _check_commission_amount(self):
        for rec in self:
            if rec.commission_type == 'amount' and rec.commission_amount:
                if 0 > rec.commission_amount or rec.commission_amount > rec.range_to:
                    raise UserError(_("Commission amount can't be less than 0 or higher than Range To"))

    @api.constrains('range_from', 'range_to')
    def _check_range_duplication(self):
        for rec in self:
            if rec.range_from > rec.range_to:
                raise UserError(_("(Range To) Can't be less than (Range From) "))
