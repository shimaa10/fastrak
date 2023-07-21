from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FastrakCrmTargetReport(models.AbstractModel):
    _name = 'report.fastrak_crm.report_crm_target'

    @staticmethod
    def _get_target_sales_persons(target: object):
        return [line.sales_person for line in target.target_line_ids]

    def _get_sales_person_target_line(self, crm_target_id, sales_person):
        return self.env['crm.target.line'].search(
            [('crm_target_id', '=', crm_target_id), ('sales_person', '=', sales_person)])

    def _get_sales_person_customer(self, sales_person):
        return self.env['res.partner'].search([('user_id', '=', sales_person)])

    def _get_customer_orders(self, customer, start_date, end_date):
        return self.env['fastrak.bill.of.loading'].search_count(
            [
                ('customer', '=', customer),
                ('create_date', '>=', start_date),
                ('create_date', '<=', end_date),
            ]
        )

    def _get_customers_orders(self, start_date, end_date, team_members, sales_person=None):
        customers = []

        if not sales_person:
            for person in team_members:
                customer_object = self._get_sales_person_customer(person.id)
                if customer_object:
                    for customer in customer_object:
                        customers.append(customer)

        else:
            for customer in self._get_sales_person_customer(sales_person[0]):
                customers.append(customer)

        return [
            {
                'customer_code': customer.id,
                'customer_name': customer.display_name,
                'total_orders': self._get_customer_orders(customer.id, start_date, end_date)
            } for customer in customers
        ]

    def _get_team_object(self, team_id):
        return self.env['crm.team'].search([('id', '=', team_id)])

    def get_report_lines_data(self, data):
        start_date = data['form'].get('date_from')
        end_date = data['form'].get('date_to')
        sales_person = data['form'].get('sales_person')
        sales_team = data['form'].get('sales_team')

        domain = [('start_date', '>=', start_date), ('end_date', '<=', end_date), ('sales_team', '=', sales_team[0])]

        if sales_person:
            team_object = self._get_team_object(sales_team[0])
            if sales_person[0] not in team_object.member_ids.ids and int(sales_person[0]) != team_object.user_id.id:
                raise ValidationError(f"{sales_person[1]} is not part of {sales_team[1]}")

        target_objects = self.env['crm.target'].search(domain)

        target_list = [
            {
                'date_from': start_date,
                'date_to': end_date,
                'sales_person': sales_person,

                'target_name': target.name,
                'start_date': target.start_date,
                'end_date': target.end_date,
                'target_orders': target.target_orders,

                'sales_team': target.sales_team.display_name,
                'sales_members': self._get_target_sales_persons(target),
                'customers_orders': self._get_customers_orders(
                    start_date=start_date, end_date=end_date,
                    team_members=self._get_target_sales_persons(target),
                    sales_person=sales_person
                )

            } for target in target_objects
        ]
        print("List:", target_list)

        return target_list

    @api.model
    def _get_report_values(self, docids, data):
        """in this function can access the data returned from the button
        click function"""
        # sales_team = data['form'].get('sales_team')
        # sales_team = sales_team[1] if sales_team else None
        #
        # sales_person = data['form'].get('sales_person')
        # sales_person = sales_person[1] if sales_person else None

        # headers = {
        #     'sales_team': sales_team,
        #     'sales_person': sales_person,
        #     'date_from': data['form'].get('date_from'),
        #     'date_to': data['form'].get('date_to')
        # }

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'data': data['form'],
            'docs': self.get_report_lines_data(data),
            'date_today': fields.Datetime.now()
        }
