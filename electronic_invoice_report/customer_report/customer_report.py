# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
import xlwt
import io
import base64
from xlwt import easyxf
import datetime

columns_list = ["State", "Name", "InternalCode", "BusinessType", "RegistrationNumber", "BranchId", "CountryName",
                "GovernateName", "RegionCity", "Street", "BuildingNumber", "Notes"
                ]


class PrintInvoiceSummary(models.TransientModel):
    _name = "electronic.customer.report"

    @api.model
    def _get_from_date(self):
        current_date = datetime.date.today()
        return datetime.date(current_date.year, current_date.month, 1)

    from_date = fields.Date(string=_('From Date'), default=_get_from_date)
    to_date = fields.Date(string=_('To Date'), default=datetime.date.today())

    electronic_customer_file = fields.Binary(_('Invoice Summary Report'))
    file_name = fields.Char(_('File Name'))
    electronic_customer_report_printed = fields.Boolean(_('Invoice Report Printed'))

    @staticmethod
    def _draw_report_header(worksheet):
        column_heading_style = easyxf('font:height 200;font:bold True;align: horiz center;')
        for key, column_name in enumerate(columns_list):
            worksheet.write(0, key, _(column_name), column_heading_style)
            worksheet.col(key).width = 6000

    def action_print_electronic_customer(self):
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet(_('Electronic Customer Report'))
        self._draw_report_header(worksheet)
        row = 1
        row_style = easyxf('align: horiz center;')
        selection_criteria = [
            ('create_date', '>=', self.from_date), ('create_date', '<=', self.to_date), ('name', '!=', 'Administrator')
        ]

        partner_objs = self.env['res.partner'].search(selection_criteria)

        for partner in partner_objs:
            worksheet.write(row, 0, '', row_style)
            worksheet.write(row, 1, partner.display_name, row_style)
            worksheet.write(row, 2, partner.id, row_style)
            worksheet.write(row, 3, 'Business' if partner.company_type == 'company' else 'Person', row_style)
            worksheet.write(row, 4, partner.vat or '', row_style)
            worksheet.write(row, 5, '', row_style)
            worksheet.write(row, 6, partner.country_id.name or '', row_style)
            worksheet.write(row, 7, partner.state_id.name or '', row_style)
            worksheet.write(row, 8, partner.city or '', row_style)
            worksheet.write(row, 9, partner.street or '', row_style)
            worksheet.write(row, 10, '', row_style)
            worksheet.write(row, 11, partner.comment or '', row_style)
            row += 1

        fp = io.BytesIO()
        workbook.save(fp)
        excel_file = base64.encodebytes(fp.getvalue())
        self.electronic_customer_file = excel_file
        self.file_name = 'E-Customer Report.xls'
        self.electronic_customer_report_printed = True
        fp.close()

        return {
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'electronic.customer.report',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
        }
