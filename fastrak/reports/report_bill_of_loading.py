from odoo import models, fields, api


class SampleReportPrint(models.AbstractModel):
    _name = 'report.fastrak.report_bill_of_loading'

    def get_report_lines_data(self, data):
        start_date = data['form'].get('date_from')
        end_date = data['form'].get('date_to')
        target_partner = data['form'].get('target_partner')
        order_state = data['form'].get('order_status')
        domain = []

        if order_state:
            domain.append(('order_status', '=', order_state))

        if start_date:
            domain.append(('create_date', '>=', start_date))

        if end_date:
            domain.append(('create_date', '<=', end_date))

        if target_partner:
            domain.append(('customer', '=', target_partner[0]))

        bol_objects = self.env['fastrak.bill.of.loading'].search(domain)
        bills_list = []
        for bill in bol_objects:
            bills_list.append(
                {
                    'order_name': bill.order_id,
                    'customer_name': bill.customer.display_name,
                    'create_date': bill.create_date.strftime('%Y-%m-%d  %H:%M:%S'),
                    'total_amount': bill.invoice_id.amount_total,
                    'money_collected': bill.money_collected,
                    'order_status': bill.order_status,
                    'order_delivery_status': bill.order_delivery_status
                }
            )

        return bills_list

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
