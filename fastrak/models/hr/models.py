from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CustomHrDepartment(models.Model):
    _inherit = 'hr.department'

    is_operation_department = fields.Boolean()

    @api.constrains('is_operation_department')
    def _constraint_operation_department(self):
        self.ensure_one()
        if self.is_operation_department:
            result = self.search([('is_operation_department', '=', True), ('id', '!=', self.id)])
            if result.exists():
                raise ValidationError("Can't have more than one operation department")


class CustomEmployee(models.Model):
    _inherit = 'hr.employee'

    _sql_constraints = [
        ('hr_mobile_unique', 'UNIQUE(mobile_phone)', 'Mobile Number Already Exists'),
        ('hr_email_unique', 'UNIQUE(work_email)', 'Email address Already Exists')
    ]

    last_name = fields.Char(string='Last Name')
    custody_account = fields.Many2one('account.account', domain=[('is_custody_account', '=', True)])
    is_driver = fields.Boolean()

    @api.onchange('name', 'last_name')
    def change_private_address_name(self):
        """
        Change The related contact of the employee with the updated name and last name
        :return:
        """

        self.address_home_id.name = self.name
        self.address_home_id.last_name = self.last_name

    @api.onchange('mobile_phone', 'work_email')
    def change_private_address_mobile_email(self):
        """
        Change The related contact of the employee with the updated mobile and email
        :return:
        """
        self.address_home_id.mobile = self.mobile_phone
        self.address_home_id.email = self.work_email

    # @api.depends('name', 'last_name')
    # def _compute_display_name(self):
    #     diff = dict(show_address=None, show_address_only=None, show_email=None, html_format=None, show_vat=None)
    #     names = dict(self.with_context(**diff).name_get())
    #     for partner in self:
    #         print('CMPT: ', partner, partner.name, partner.last_name)
    #         partner.display_name = names.get(partner.id)

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, "{} {}".format(record.name, record.last_name)))
        return result
