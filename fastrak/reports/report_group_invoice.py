from odoo import models, fields, api


class SampleReportPrint(models.AbstractModel):
    _name = 'report.fastrak.report_group_invoice'

    def _get_bol_number(self, invoice):
        result = ' '
        try:
            bol_obj = self.env['fastrak.bill.of.loading'].search([('invoice_id', '=', invoice.id)])
            result = bol_obj.order_id
        except Exception as e:
            print(e)
            pass
        return result

    def get_report_lines_data(self, data):
        start_date = data['form'].get('date_from')
        end_date = data['form'].get('date_to')
        target_partner = data['form'].get('target_partner')
        invoice_state = data['form'].get('state')
        domain = [('move_type', '=', 'out_invoice')]

        net_total_amount = 0
        total_discount = 0
        total_tax = 0
        total_amount_words = ''
        net_amount_word = ''

        if start_date:
            domain.append(('create_date', '>=', start_date))

        if end_date:
            domain.append(('create_date', '<=', end_date))

        if target_partner:
            domain.append(('partner_id', '=', target_partner[0]))

        if invoice_state:
            domain.append(('state', '=', invoice_state))

        invoices_objects = self.env['account.move'].search(domain)
        invoices_list = []

        for invoice in invoices_objects:
            net_total_amount += invoice.amount_total
            total_tax = 0.0

            for line in invoice.invoice_line_ids:
                total_discount += (line.price_unit * line.quantity) - line.price_subtotal

            invoices_list.append(
                {
                    'invoice_name': invoice.name,
                    'customer_name': invoice.partner_id.display_name,
                    'create_date': invoice.create_date.strftime('%Y-%m-%d'),
                    'total_amount': invoice.amount_total,
                    'bol_number': self._get_bol_number(invoice),
                    'weight': invoice.get_bol_info().get('weight'),
                    'number_of_pieces': invoice.get_bol_info().get('number_of_pieces'),
                    'delivery_type': invoice.get_bol_info().get('delivery_type'),
                    'src_city': invoice.get_bol_info().get('src_city'),
                    'dst_city': invoice.get_bol_info().get('dst_city'),
                    'delivery_time': invoice.get_bol_info().get('delivery_time'),
                    'currency_name': invoice.currency_id.symbol,

                }
            )
        if net_total_amount:
            net_amount_word = self.env.company.currency_id.amount_to_text(net_total_amount)
            total_amount_words = self.env.company.currency_id.amount_to_text(
                net_total_amount - total_discount + total_tax)

        return invoices_list, net_total_amount, net_amount_word, total_amount_words, total_discount, total_tax

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
        invoices, net_total_amount, net_amount_word, total_amount_words, total_discount, total_tax = self.get_report_lines_data(
            data)

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'headers': headers,
            'data': data['form'],
            'invoices': invoices,
            'total_amount': net_total_amount - total_discount + total_tax,
            'total_amount_words': total_amount_words,
            'net_total_amount': net_total_amount,
            'net_total_words': net_amount_word,
            'total_discount': total_discount,
            'total_tax': total_tax,
            'date_today': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),

        }
