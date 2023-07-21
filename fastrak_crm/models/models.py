# -*- coding: utf-8 -*-

from odoo import models, fields, api


# class PartnerBindingInherit(models.TransientModel):
#     _inherit = 'crm.partner.binding'
#
#     action = fields.Selection(selection=[
#         # ('create', 'Create a new customer'),
#         ('exist', 'Link to an existing customer'),
#         ('nothing', 'Do not link to a customer')
#     ], string='Related Customer', required=True)


class Lead2OpportunityPartnerInherit(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'

    # name = fields.Selection(
    #     selection=[('convert', 'Convert to opportunity')], string='Conversion Action', required=True
    # )
    #
    # action = fields.Selection(
    #     string='Related Customer', required=True,
    #     selection=[
    #         ('exist', 'Link to an existing Customer :D'),
    #         ('nothing', 'Do not link to a customer :(')
    #     ],
    # )

    def _check_partner_sales_person(self):
        """
        Check if there is no salesperson assigned for that customer assign the current user to it
        :return:
        """
        if not self.partner_id.user_id:
            self.partner_id.user_id = self.user_id

    def action_apply(self):
        self._check_partner_sales_person()
        return super().action_apply()
