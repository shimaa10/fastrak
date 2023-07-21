# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CostCenters(models.Model):
    """docstring for CostCenters"""
    _name = 'cost.centers'
    _description = 'Costcenter Code'
    _rec_name = 'code'

    code = fields.Char(string='Code', required=True)
    title = fields.Char(string='Title', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    def name_get(self):
        res = []
        for order in self:
            name = str(order.code) + " " + str(order.title)
            res.append((order.id, name))
        return res

# class SaleOrder(models.Model):
#     """docstring for SaleOrder"""
#     _inherit = 'sale.order'
#
#     cost_centers_id = fields.Many2one('cost.centers', string='Cost Center')
#
#     def _prepare_invoice(self):
#         res = super(SaleOrder, self)._prepare_invoice()
#         if res:
#             res.update({'cost_centers_id': self.cost_centers_id and self.cost_centers_id.id})
#         return res
#
#     @api.onchange('cost_centers_id')
#     def onchange_cost_centers_id(self):
#         for order in self:
#             if order.order_line:
#                 order.order_line.update({'cost_centers_id': order.cost_centers_id and order.cost_centers_id.id})
#
#
# class SaleOrderLine(models.Model):
#     """docstring for SaleOrderLine"""
#     _inherit = 'sale.order.line'
#
#     cost_centers_id = fields.Many2one('cost.centers', string='Cost Center')
#
#     def _prepare_invoice_line(self):
#         res = super(SaleOrderLine, self)._prepare_invoice_line()
#         if res:
#             res.update({'cost_centers_id': self.cost_centers_id.id})
#         return res
#
#
# class PurchaseOrder(models.Model):
#     """docstring for PurchaseOrder"""
#     _inherit = 'purchase.order'
#
#     cost_centers_id = fields.Many2one('cost.centers', string='Cost Center')
#
#     def action_view_invoice(self):
#         res = super(PurchaseOrder, self).action_view_invoice()
#         if res:
#             res['context'].update({'default_cost_centers_id': self.cost_centers_id and self.cost_centers_id.id})
#         return res
#
#     @api.onchange('cost_centers_id')
#     def onchange_cost_centers_id(self):
#         for order in self:
#             if order.order_line:
#                 order.order_line.update({'cost_centers_id': order.cost_centers_id and order.cost_centers_id.id})
#
#
# class PurchaseOrderLine(models.Model):
#     """docstring for PurchaseOrderLine"""
#     _inherit = 'purchase.order.line'
#
#     cost_centers_id = fields.Many2one('cost.centers', string='Cost Center')
#
#     def _prepare_account_move_line(self, line):
#         move_line_vals = super(PurchaseOrderLine, self)._prepare_account_move_line(line)
#         if 'purchase_line_id' in move_line_vals:
#             po_line = move_line_vals.get('purchase_line_id')
#             po_line_id = self.env['purchase.order.line'].browse(po_line)
#             move_line_vals.update({'cost_centers_id': po_line_id.cost_centers_id.id})
#         return move_line_vals
#
#
# class StockRule(models.Model):
#     _inherit = 'stock.rule'
#
#     def _prepare_purchase_order(self, product_id, product_qty, product_uom, origin, values, partner):
#         res = super(StockRule, self)._prepare_purchase_order(product_id, product_qty, product_uom, origin, values,
#                                                              partner)
#         if res:
#             order_id = self.env['sale.order'].search([('name', 'like', res['origin'])], limit=1)
#             if order_id:
#                 res.update({'cost_centers_id': order_id.cost_centers_id and order_id.cost_centers_id.id})
#         return res
#
#     def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, values, po, partner):
#         res = super(StockRule, self)._prepare_purchase_order_line(product_id, product_qty, product_uom, values, po,
#                                                                   partner)
#         if res:
#             order_id = self.env['purchase.order'].browse(res['order_id'])
#             if order_id:
#                 res.update({'cost_centers_id': order_id.cost_centers_id and order_id.cost_centers_id.id})
#         return res


class AccountMove(models.Model):
    """docstring for AccountInvoice"""
    _inherit = 'account.move'

    cost_centers_id = fields.Many2one('cost.centers', string='Cost Center')

    @api.onchange('cost_centers_id')
    def onchange_cost_centers_id(self):
        for order in self:
            if order.cost_centers_id:
                if order.invoice_line_ids:
                    order.invoice_line_ids.update(
                        {'cost_centers_id': order.cost_centers_id and order.cost_centers_id.id})

                if order.line_ids:
                    order.line_ids.update({'cost_centers_id': order.cost_centers_id and order.cost_centers_id.id})
            else:
                print("Delegating to upcoming functions")

    @api.onchange('line_ids')
    def _check_entry_cost_center(self):
        # Condition applied on entry only
        for rec in self.filtered(lambda l: l.move_type == 'entry'):
            for line in rec.line_ids:
                if line:
                    if line.account_id.required_cost_center:
                        if not rec.cost_centers_id:
                            raise ValidationError(_("Missing Cost Center"))


    @api.onchange('invoice_line_ids')
    def _check_invoice_cost_center_lines(self):
        # Condition applied on Invoice
        for rec in self.filtered(lambda l: l.move_type == 'out_invoice'):
            print("YES INVOICE")
            if not rec.cost_centers_id:
                for line in rec.invoice_line_ids:
                    if line:
                        cost_center = line.product_id.product_tmpl_id.categ_id.cost_centers_id
                        if not cost_center:
                            raise ValidationError(
                                "Missing Cost center in product ({}) Category ({})".format(line.product_id.name,
                                                                                           line.product_id.product_tmpl_id.categ_id.name))
                        print("Target Cost Center: ", cost_center.title, cost_center.id)
                        line.update({'cost_centers_id': cost_center.id})


class AccountMoveLine(models.Model):
    """docstring for AccountInvoiceLine"""
    _inherit = 'account.move.line'

    cost_centers_id = fields.Many2one('cost.centers', string='Cost Center')


class HREmployee(models.Model):
    """docstring for HREmployee"""
    _inherit = 'hr.employee'

    cost_centers_id = fields.Many2one('cost.centers', string='Cost Center')

#
# class HRExpense(models.Model):
#     """docstring for HRExpense"""
#     _inherit = 'hr.expense'
#
#     cost_centers_id = fields.Many2one('cost.centers', string='Cost Center')
#
#     @api.onchange('employee_id')
#     def _onchange_cost_centers_id(self):
#         if self.employee_id:
#             self.cost_centers_id = self.employee_id.cost_centers_id and self.employee_id.cost_centers_id.id
#
#     def action_submit_expenses(self):
#         if any(expense.state != 'draft' or expense.sheet_id for expense in self):
#             raise UserError(_("You cannot report twice the same line!"))
#         if len(self.mapped('employee_id')) != 1:
#             raise UserError(_("You cannot report expenses for different employees in the same report."))
#
#         todo = self.filtered(lambda x: x.payment_mode == 'own_account') or self.filtered(
#             lambda x: x.payment_mode == 'company_account')
#         cost_centers_id = False
#         if self.cost_centers_id:
#             cost_centers_id = self.cost_centers_id and self.cost_centers_id.id
#         return {
#             'name': _('New Expense Report'),
#             'type': 'ir.actions.act_window',
#             'view_mode': 'form',
#             'res_model': 'hr.expense.sheet',
#             'target': 'current',
#             'context': {
#                 'default_expense_line_ids': todo.ids,
#                 'default_employee_id': self[0].employee_id.id,
#                 'default_name': todo[0].name if len(todo) == 1 else '',
#                 'default_cost_centers_id': cost_centers_id,
#             }
#         }
#
#
# class HRExpenseSheet(models.Model):
#     """docstring for HRExpenseSheet"""
#     _inherit = 'hr.expense.sheet'
#
#     cost_centers_id = fields.Many2one('cost.centers', string='Cost Center')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
