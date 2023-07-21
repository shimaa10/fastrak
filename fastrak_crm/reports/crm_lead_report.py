from odoo import models, fields, api


class FastrakCrmLeadReport(models.AbstractModel):
    _name = 'report.fastrak_crm.report_crm_lead'

    def get_report_lines_data(self, data):
        start_date = data['form'].get('date_from')
        end_date = data['form'].get('date_to')
        sales_person = data['form'].get('sales_person')
        sales_team = data['form'].get('sales_team')
        stage_id = data['form'].get('stage_id')
        domain = [('lead_start_date', '>=', start_date), ('lead_end_date', '<=', end_date)]

        if stage_id:
            domain.append(('stage_id', '=', stage_id[0]))

        if sales_team:
            domain.append(('team_id', '=', sales_team[0]))

        if sales_person:
            domain.append(('user_id', '=', sales_person[0]))

        lead_objects = self.env['crm.lead'].search(domain)

        leads_list = [
            {
                'name': lead.name,
                'probability': lead.probability,
                'customer_code': lead.partner_id.id,
                'customer_name': lead.partner_id.display_name,
                'priority': lead.priority,
                'tag_ids': lead.tag_ids,
                'expected_orders_count': lead.expected_orders_count,
                'start_date': lead.lead_start_date.strftime('%Y-%m-%d'),
                'end_date': lead.lead_end_date.strftime('%Y-%m-%d'),
                # 'notes': lead.description,
                'state': lead.stage_id.display_name,

            } for lead in lead_objects
        ]

        return leads_list

    @api.model
    def _get_report_values(self, docids, data):
        """in this function can access the data returned from the button
        click function"""
        sales_team = data['form'].get('sales_team')
        sales_team = sales_team[1] if sales_team else None

        sales_person = data['form'].get('sales_person')
        sales_person = sales_person[1] if sales_person else None

        headers = {
            'sales_team': sales_team,
            'sales_person': sales_person,
            'date_from': data['form'].get('date_from'),
            'date_to': data['form'].get('date_to'),
            'lead_status': data['form'].get('stage_id')

        }

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'headers': headers,
            'data': data['form'],
            'docs': self.get_report_lines_data(data),
            'date_today': fields.Datetime.now(),

        }
