from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GroupInvoiceDiscountWizard(models.TransientModel):
    _name = "group.invoice.discount.wizard"
    _description = "Group Invoice Discount Wizard"

    discount_type = fields.Selection(selection=[('amount', 'Amount'), ('percent', 'Percentage')], default='percent')
    discount_amount = fields.Float()
    discount_percentage = fields.Float()
    invoice_selection_type = fields.Selection(selection=[('all', 'All Invoices'), ('specific', 'Specific Invoice')],
                                              default='all')

    @api.constrains('discount_percentage')
    def check_discount_constraints(self):
        for rec in self:
            if 0 >= rec.discount_percentage > 100:
                raise ValidationError(_("Discount is not set correctly"))

    def _get_group_invoice_record(self):
        """
        Return the current active group invoice record
        :return:
        """
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        grp_inv_rec = self.env[str(active_model)].search([('id', '=', active_id)])
        return grp_inv_rec

    def _get_initial_invoices_ids(self):
        """
        Return current group invoice associated invoices
        :return:
        """
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        if active_id and active_model:
            grp_inv_rec = self.env[str(active_model)].search([('id', '=', active_id)])

            invoice_list = [(group_invoice_line.invoice.id, group_invoice_line.invoice.name) for group_invoice_line in
                            grp_inv_rec.invoice_ids]
            return invoice_list
        return []

    target_invoice = fields.Selection(selection=_get_initial_invoices_ids)

    def _get_discount_service_line(self, discount_amount):
        """
        Prepare discount line to be created
        :return:
        """

        service_line_ids = []
        # Get and check discount product
        discount_service_product = self.env['product.product'].search([('is_main_discount_service', '=', True)])
        if not discount_service_product:
            raise ValidationError(_("Missing Discount Service"))

        # Get and check cost center for discount product
        line_category = discount_service_product.product_tmpl_id.categ_id
        if line_category.cost_centers_id:
            cost_center = line_category.cost_centers_id
        else:
            cost_center = None

        line_data = (0, 0, {
            'product_id': discount_service_product.id,
            'name': "Invoice Discount",
            'quantity': 1,
            'price_unit': -discount_amount,
            # Add Cost Center To Line
            'cost_centers_id': cost_center.id
        })

        service_line_ids.append(line_data)
        return service_line_ids

    def _update_invoice_lines(self, inv, discount):
        """
        Update invoice lines actual update wrapper
        :param inv:
        :param discount:
        :return:
        """
        discount_lines = self._get_discount_service_line(discount)
        inv.invoice_line_ids = discount_lines

    def _get_target_invoice_objects(self, all_invoices=False, target_invoice_id=None):
        """
        Return the target invoices to work on them based on the user selection [ALL,Specific]
        :param all_invoices:
        :param target_invoice_id:
        :return:
        """

        if all_invoices:
            grp_inv_rec = self._get_group_invoice_record()
            invoices = [group_invoice_line.invoice for group_invoice_line in grp_inv_rec.invoice_ids]

        else:
            invoices = self.env['account.move'].search([('id', '=', target_invoice_id)])

        return invoices

    def update_group_invoice(self):
        wizard_form = self.read()[0]
        invoice_selection = wizard_form.get('invoice_selection_type')
        discount_selection = wizard_form.get('discount_type')

        # Check invoice selection
        if invoice_selection == 'all':
            invoices = self._get_target_invoice_objects(all_invoices=True)

        else:
            target_invoices = wizard_form.get('target_invoice')
            invoices = self._get_target_invoice_objects(target_invoice_id=target_invoices)

        # Check Discount selection
        if discount_selection == 'amount':
            target_discount_amount = wizard_form.get('discount_amount')

            for invoice in invoices:
                self._update_invoice_lines(invoice, discount=target_discount_amount)
                self._get_group_invoice_record().total_discount += target_discount_amount

        else:
            target_discount_percentage = wizard_form.get('discount_percentage')

            for invoice in invoices:
                target_discount_amount = round(invoice.amount_residual * (target_discount_percentage / 100))

                self._update_invoice_lines(invoice, discount=target_discount_amount)
                self._get_group_invoice_record().total_discount += target_discount_amount

        return True
