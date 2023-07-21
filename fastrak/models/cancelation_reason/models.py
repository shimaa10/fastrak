from odoo import models, fields, api


class CancellationReasons(models.Model):
    _name = 'cancellation.reason'
    _rec_name = 'reason'

    reason = fields.Char(required=True)
    active = fields.Boolean(default=True)
