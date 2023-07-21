from odoo import models, fields, api


class FastrakCrmSalesReport(models.AbstractModel):
    _name = 'report.fastrak_crm.report_crm_sales'

    def _get_customer_orders(self, customer, start_date, end_date):
        return self.env['fastrak.bill.of.loading'].search_count(
            [
                ('customer', '=', customer),
                ('create_date', '>=', start_date),
                ('create_date', '<=', end_date),
            ]
        )

    def get_report_lines_data(self, data):
        start_date = data['form'].get('date_from')
        end_date = data['form'].get('date_to')
        sales_person = data['form'].get('sales_person')
        sales_team = data['form'].get('sales_team')
        domain = [('create_date', '>=', start_date), ('create_date', '<=', end_date)]

        if sales_team:
            domain.append(('team_id', '=', sales_team[0]))

        if sales_person:
            domain.append(('user_id', '=', sales_person[0]))

        lead_objects = self.env['crm.lead'].search(domain)

        leads_list = [
            {
                'lead_name': lead.name,
                'sales_team': lead.team_id.display_name,
                'sales_person': lead.user_id.display_name,
                'customer_name': lead.partner_id.display_name,
                'create_date': lead.create_date.strftime('%Y-%m-%d  %H:%M:%S'),
                'expected_orders_count': lead.expected_orders_count,
                'customer_orders': self._get_customer_orders(
                    lead.partner_id.id, lead.lead_start_date, lead.lead_end_date
                )
            } for lead in lead_objects
        ]

        print('Leads:', leads_list)

        return leads_list

    @api.model
    def _get_report_values(self, docids, data):
        """in this function can access the data returned from the button
        click function"""
        partner = data['form'].get('target_partner')
        partner = partner[1] if partner else None

        headers = {
            'partner_name': partner,
            'date_from': data['form'].get('date_from'),
            'date_to': data['form'].get('date_to'),
            'order_status': data['form'].get('order_status')

        }

        # value = []
        # query = """SELECT *
        #                 FROM sale_order as so
        #                 JOIN sale_order_line AS sl ON so.id = sl.sale_order_id
        #                 WHERE sl.id = %s"""
        # value.append(model_id)
        # self._cr.execute(query, value)
        # record = self._cr.dictfetchall()

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'headers': headers,
            'data': data['form'],
            'docs': self.get_report_lines_data(data),
            'date_today': fields.Datetime.now(),

        }
