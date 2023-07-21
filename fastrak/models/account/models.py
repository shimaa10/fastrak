from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CustomAccount(models.Model):
    _inherit = 'account.account'

    is_custody_account = fields.Boolean()
    is_money_collection_account = fields.Boolean()
    is_default_bank_account = fields.Boolean()
    is_bank_commission_account = fields.Boolean()

    @api.constrains('is_custody_account')
    def _check_custody_account(self):
        """
        Prevent having more than 1 custody account
        :return:
        """
        result = self.search(
            [('is_custody_account', '=', True), ('company_id', '=', self.company_id.id), ('id', '!=', self.id)]
        )

        if result and self.is_custody_account:
            raise ValidationError("Can't have more than one custody account")

    @api.constrains('is_money_collection_account')
    def _check_money_collection_account(self):
        """
        Prevent having more than 1 money collection account
        :return:
        """
        result = self.search(
            [('is_money_collection_account', '=', True), ('company_id', '=', self.company_id.id), ('id', '!=', self.id)]
        )

        if result and self.is_money_collection_account:
            raise ValidationError("Can't have more than one money collection account")

    @api.constrains('is_default_bank_account')
    def _check_default_bank_account(self):
        """
        Prevent having more than 1 default bank account
        :return:
        """
        result = self.search(
            [('is_default_bank_account', '=', True), ('company_id', '=', self.company_id.id), ('id', '!=', self.id)]
        )

        if result and self.is_default_bank_account:
            raise ValidationError("Can't have more than one default bank account")

    @api.constrains('is_bank_commission_account')
    def _check_bank_commission_account(self):
        """
        Prevent having more than 1  bank commission account
        :return:
        """
        result = self.search(
            [('is_bank_commission_account', '=', True), ('company_id', '=', self.company_id.id), ('id', '!=', self.id)]
        )

        if result and self.is_bank_commission_account:
            raise ValidationError("Can't have more than one bank commission account")
