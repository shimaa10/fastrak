from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CustomProduct(models.Model):
    _inherit = 'product.template'

    is_main_service_product = fields.Boolean(
        track_visibility='onchange',
        help="Used to define the main shipping service product")
    is_main_penalty_charge = fields.Boolean(
        track_visibility='onchange',
        help="Used to define the main penalty charge product that will be used in penalty invoice")

    is_main_withdraw_charge = fields.Boolean(
        track_visibility='onchange',
        help="Used to define the customer withdraw charge product that will be used in withdraw request invoice")

    is_main_discount_service = fields.Boolean(
        track_visibility='onchange',
        help="Used to define the main discount  product that will be used in making discount on invoice")

    is_main_vat_service = fields.Boolean(
        track_visibility='onchange',
        help="Used to define the main Vat  product that will be used in making vat on invoice")

    @api.constrains('is_main_service_product')
    def check_main_service_product(self):
        result = self.search(
            [
                ('is_main_service_product', '=', True), ('id', '!=', self.id)
            ]
        )
        if result.exists() and self.is_main_service_product:
            raise ValidationError("Can't Have More Than One Main Service Product")

    @api.constrains('is_main_penalty_charge')
    def check_main_penalty_charge_service(self):
        result = self.search(
            [
                ('is_main_penalty_charge', '=', True), ('id', '!=', self.id)
            ]
        )
        if result.exists() and self.is_main_penalty_charge:
            raise ValidationError("Can't Have More Than One Penalty Charge Product")

    @api.constrains('is_main_withdraw_charge')
    def check_main_withdraw_charge_service(self):
        result = self.search(
            [
                ('is_main_withdraw_charge', '=', True), ('id', '!=', self.id)
            ]
        )
        if result.exists() and self.is_main_withdraw_charge:
            raise ValidationError("Can't Have More Than One Withdraw Charge Product")

    @api.constrains('is_main_discount_service')
    def check_main_discount_service(self):
        result = self.search(
            [
                ('is_main_discount_service', '=', True), ('id', '!=', self.id)
            ]
        )
        if result.exists() and self.is_main_discount_service:
            raise ValidationError("Can't Have More Than One Main Discount Product")

    @api.constrains('is_main_vat_service')
    def check_main_vat_service(self):
        result = self.search(
            [
                ('is_main_vat_service', '=', True), ('id', '!=', self.id)
            ]
        )
        if result.exists() and self.is_main_vat_service:
            raise ValidationError("Can't Have More Than One Main Vat Product")
