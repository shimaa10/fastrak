# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
import xlwt
import io
import base64
from xlwt import easyxf
import datetime
from odoo.tools.float_utils import float_repr

columns_list = ["State", "DocumentType", "CustomerCode", "CustomerName", "DateTimeIssued", "TaxpayerActivityCode",
                "DocumentCode",
                "ExtraDiscountAmount", "ReferenceDocumentCodes", "PosDeviceSerialNo", "ReferenceSalesReceiptCode",
                "Notes", "PurchaseOrderReference", "PurchaseOrderDescription", "SalesOrderReference",
                "SalesOrderDescription", "ProformaInvoiceNumber", "BankName", "BankAddress", "BankAccountNo",
                "BankAccountIBAN", "SwiftCode", "PaymentTerms", "Approach", "Packaging", "DateValidity", "ExportPort",
                "CountryOfOrigin", "GrossWeight", "NetWeight", "DeliveryTerms", "ItemCode", "Description",
                "UnitTypeCode", "Quantity", "CurrencyCode", "AmountSold", "CurrencyExchangeRate",
                "TaxableDiscountValueType", "TaxableDiscountValue", "ValueDifference", "NonTaxableDiscountAmount",
                "TotalTaxableFees", "TaxTypeCode", "TaxSubTypeCode", "ValueType", "Value"]


class PrintInvoiceSummary(models.TransientModel):
    _name = "electronic.invoice.report"

    @api.model
    def _get_from_date(self):
        current_date = datetime.date.today()
        return datetime.date(current_date.year, current_date.month, 1)

    @api.model
    def _get_to_date(self):
        return datetime.date.today()

    from_date = fields.Date(string=_('From Date'), default=_get_from_date)
    to_date = fields.Date(string=_('To Date'), default=_get_to_date)

    electronic_invoice_file = fields.Binary(_('Invoice Summary Report'))
    file_name = fields.Char(_('File Name'))
    electronic_invoice_report_printed = fields.Boolean(_('Invoice Report Printed'))

    @staticmethod
    def _draw_report_header(worksheet):
        column_heading_style = easyxf('font:height 200;font:bold True;align: horiz center;')
        for key, column_name in enumerate(columns_list):
            worksheet.write(0, key, _(column_name), column_heading_style)
            worksheet.col(key).width = 6000

    @staticmethod
    def _get_invoice_shipping_line(invoice: object):
        return invoice.invoice_line_ids.filtered(lambda
                                                     line: line.product_id.is_main_service_product == True or line.product_id.is_main_withdraw_charge == True)

    @staticmethod
    def _get_invoice_discount_line(invoice: object):
        return invoice.invoice_line_ids.filtered(lambda line: line.product_id.is_main_discount_service == True)

    def _get_order_object(self, invoice: object):
        return self.env['fastrak.bill.of.loading'].search([('invoice_id', '=', invoice.id)])

    def _get_invoice_object(self, inv_name: str):
        return self.env['account.move'].search([('name', '=', inv_name), ('type', '=', 'out_invoice')])

    def _get_invoice_amounts(self, invoice: object):
        order = None
        if invoice.type == 'out_refund':
            original_invoice = ((invoice.ref.split(':')[-1]).strip()).split(',')
            order = self._get_order_object(self._get_invoice_object(original_invoice))
        elif invoice.type == 'out_invoice':
            order = self._get_order_object(invoice)
        if order:
            shp_line = order.service_line_ids.filtered(lambda line: line.product_id.is_main_service_product)

            discount = order.discount_amount
            if discount:
                discount /= 1.14

            line_untaxed = shp_line.amount / 1.14
            line_discount_removed = line_untaxed - discount
            final_vat = line_discount_removed * (14 / 100)

            return float_repr(line_untaxed, 5), float_repr(final_vat, 5), float_repr(abs(discount), 5)

        else:
            # Case Withdraw request Invoice
            return float_repr(invoice.amount_untaxed, 5), float_repr(invoice.amount_tax, 5), 0.00000

    def action_print_electronic_invoice(self):
        workbook = xlwt.Workbook()

        worksheet = workbook.add_sheet(_('Electronic Invoice Report'))
        self._draw_report_header(worksheet)

        row = 1

        # inv_row_style = easyxf(
        #     'font:height 210;'
        #     'align: horiz center;'
        #     'pattern: pattern solid,'
        #     'fore_color gray25;'
        #     'font: color white;'
        #     'font:bold True;'
        #     "borders: top thin,bottom thin")

        row_style = easyxf('align: horiz center;')

        selection_criteria = [
            ('type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.from_date),
            ('invoice_date', '<=', self.to_date),

        ]

        invoice_objs = self.env['account.move'].search(selection_criteria)

        for invoice in invoice_objs:
            invoice_name = invoice.name
            shipping_line = self._get_invoice_shipping_line(invoice)
            line_amount, vat_amount, discount_amount = self._get_invoice_amounts(invoice)

            worksheet.write(row, 0, '', row_style)  # State not handled by us
            worksheet.write(row, 1, 'Invoice' if invoice.type == 'out_invoice' else 'CreditNote', row_style)
            worksheet.write(row, 2, invoice.partner_id.id, row_style)
            worksheet.write(row, 3, invoice.partner_id.display_name, row_style)
            worksheet.write(row, 4, invoice.invoice_date.strftime('%Y-%m-%d'), row_style)
            worksheet.write(row, 5, "5229", row_style)  # Fixed Taxpayer Code
            worksheet.write(row, 6, invoice_name, row_style)
            worksheet.write(row, 7, '', row_style)
            worksheet.write(row, 8, ((invoice.ref.split(':')[-1]).strip()).split(',')[
                0] if invoice.type == 'out_refund' else '', row_style)
            worksheet.write(row, 9, '', row_style)
            worksheet.write(row, 10, '', row_style)
            worksheet.write(row, 11, invoice.narration or '', row_style)
            worksheet.write(row, 12, '', row_style)
            worksheet.write(row, 13, '', row_style)
            worksheet.write(row, 14, '', row_style)
            worksheet.write(row, 15, '', row_style)
            worksheet.write(row, 16, '', row_style)
            worksheet.write(row, 17, '', row_style)
            worksheet.write(row, 18, '', row_style)
            worksheet.write(row, 19, '', row_style)
            worksheet.write(row, 20, '', row_style)
            worksheet.write(row, 21, '', row_style)
            worksheet.write(row, 22, '', row_style)
            worksheet.write(row, 23, '', row_style)
            worksheet.write(row, 24, '', row_style)
            worksheet.write(row, 25, '', row_style)
            worksheet.write(row, 26, '', row_style)
            worksheet.write(row, 27, '', row_style)
            worksheet.write(row, 28, self._get_order_object(invoice).weight or '', row_style)
            worksheet.write(row, 29, '', row_style)
            worksheet.write(row, 30, '', row_style)
            worksheet.write(row, 31, shipping_line.product_id.default_code, row_style)
            worksheet.write(row, 32, str(shipping_line.name).split('-')[-1] or '', row_style)
            worksheet.write(row, 33, 'EA', row_style)

            worksheet.write(row, 34, 1, row_style)
            worksheet.write(row, 35, 'EGP', row_style)  # Currency Code
            # worksheet.write(row, 35, float_repr(shipping_line.price_subtotal, 5), row_style)  # Amount sold
            worksheet.write(row, 36, line_amount, row_style)  # Amount sold
            worksheet.write(row, 37, 1, row_style)  # CurrencyExchangeRate 'Always to be 1 as using egp'
            worksheet.write(row, 38, 'Amount', row_style)
            # worksheet.write(row, 38, float_repr(abs(self._get_invoice_discount_line(invoice).price_subtotal), 5) or '',
            #                 row_style)  # Taxable Discount Amount
            worksheet.write(row, 39, discount_amount or '', row_style)  # Taxable Discount Amount
            worksheet.write(row, 40, '', row_style)
            worksheet.write(row, 41, '', row_style)
            worksheet.write(row, 42, '', row_style)  # TotalTaxableFees
            worksheet.write(row, 43, 'T1', row_style)  # TaxTypeCode
            worksheet.write(row, 44, 'V009', row_style)  # TaxSubTypeCode
            worksheet.write(row, 45, 'Amount', row_style)  # ValueType
            # worksheet.write(row, 45, float_repr(invoice.amount_tax, 5), row_style)  # Value
            worksheet.write(row, 46, vat_amount, row_style)  # Value

            row += 1

        fp = io.BytesIO()
        workbook.save(fp)
        excel_file = base64.encodebytes(fp.getvalue())
        self.electronic_invoice_file = excel_file
        self.file_name = 'E-Invoice Report.xls'
        self.electronic_invoice_report_printed = True
        fp.close()

        return {
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'electronic.invoice.report',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
        }
