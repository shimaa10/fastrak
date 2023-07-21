from odoo import fields, models


class FastrakCrm(models.Model):
    _inherit = 'crm.lead'

    expected_orders_count = fields.Integer()
    expected_amount = fields.Monetary(currency_field='company_currency')

    lead_start_date = fields.Date(string="Start Date")
    lead_end_date = fields.Date(string="End Date")

    def convert_opportunity(self, partner_id, user_ids=False, team_id=False):
        customer = False
        if partner_id:
            customer = self.env['res.partner'].browse(partner_id)
        for lead in self:
            if not lead.active or lead.probability == 100:
                continue
            vals = lead._convert_opportunity_data(customer, team_id)

            # Updating Lead Values
            vals.update({
                'lead_start_date': lead.lead_start_date,
                'lead_end_date': lead.lead_end_date,
                'expected_orders_count': lead.expected_orders_count,
                'expected_amount': lead.expected_amount,
            })

            lead.write(vals)

        if user_ids or team_id:
            self.allocate_salesman(user_ids, team_id)

        return True
