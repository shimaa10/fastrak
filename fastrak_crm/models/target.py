from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CrmTargetLine(models.Model):
    _name = 'crm.target.line'

    def _get_sales_teams(self):
        print("oky")
        print("Teams: ", self.crm_target_id.sales_team.member_ids)
        return self.crm_target_id.sales_team.member_ids

    crm_target_id = fields.Many2one('crm.target')
    sales_person = fields.Many2one('res.users')
    target = fields.Integer()


class CrmTarget(models.Model):
    _name = 'crm.target'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Fastrak Crm Target Model"

    name = fields.Char(string=_("Name"))
    start_date = fields.Date(string=_("Start Date"))
    end_date = fields.Date(string=_("End Date"))

    target_type = fields.Selection(selection=[
        # ('amount', 'Amount'),
        ('orders_count', 'Orders'),
        # ('both', 'Both'),
    ], default='orders_count')

    target_amount = fields.Float(string=_("Target Amount"))
    target_orders = fields.Integer(string=_("Target Orders"))
    sales_team = fields.Many2one('crm.team', string=_("Sales Team"))
    target_line_ids = fields.One2many(
        comodel_name='crm.target.line', inverse_name='crm_target_id', string=_("Sales Persons")
    )

    @api.constrains('target_orders')
    def check_target_orders_count(self):
        """
        Check that target lines->target orders count is matched with the defined target orders count
        :return:
        """
        if self.target_orders != sum([line.target for line in self.target_line_ids]):
            raise ValidationError("Target Orders Count doesn't match sales persons target lines count")

    @api.constrains('target_line_ids')
    def check_target_line_ids(self):
        """

        :return:
        """
        for line in self.target_line_ids:
            if line.sales_person not in self.sales_team.member_ids and line.sales_person != self.sales_team.user_id:
                raise ValidationError(
                    f"Sales person {line.sales_person.display_name} is not part of {self.sales_team.display_name} Team")
