import re
from odoo import models, fields, api
from odoo.osv.expression import get_unaccent_wrapper


class CustomPartner(models.Model):
    _inherit = 'res.partner'

    _sql_constraints = [
        ('mobile_unique', 'UNIQUE(mobile)', 'Mobile Number Already Exists'),
        ('email_unique', 'UNIQUE(email)', 'Email address Already Exists')
    ]

    last_name = fields.Char(string='Last Name')
    customer_company_name = fields.Char(string='Company Name')
    is_premium_user = fields.Boolean(string='Premium User')
    cr = fields.Char(string='CR')

    @api.depends('is_company', 'name', 'last_name', 'parent_id.display_name', 'type', 'company_name')
    def _compute_display_name(self):
        diff = dict(show_address=None, show_address_only=None, show_email=None, html_format=None, show_vat=None)
        names = dict(self.with_context(**diff).name_get())
        for partner in self:
            partner.display_name = names.get(partner.id)

    def name_get(self):
        result = []
        for record in self:
            if self._context.get('display_with_id', False):
                if record.last_name:
                    result.append((record.id, "{} {} {}".format(record.id, record.name, record.last_name)))
                else:
                    result.append((record.id, "{} {}".format(record.id, record.name)))

            else:
                if record.last_name:
                    result.append((record.id, "{} {}".format(record.name, record.last_name)))
                else:
                    result.append((record.id, "{}".format(record.name)))
        return result

    def _get_name(self):
        """ Utility method to allow name_get to be overrided without re-browse the partner """
        partner = self
        name = partner.name or ''

        if partner.company_name or partner.parent_id:
            if not name and partner.type in ['invoice', 'delivery', 'other']:
                name = dict(self.fields_get(['type'])['type']['selection'])[partner.type]
            if not partner.is_company:
                name = self._get_contact_name(partner, name)
        if self._context.get('show_address_only'):
            name = partner._display_address(without_company=True)
        if self._context.get('show_address'):
            name = name + "\n" + partner._display_address(without_company=True)
        name = name.replace('\n\n', '\n')
        name = name.replace('\n\n', '\n')
        if self._context.get('address_inline'):
            name = name.replace('\n', ', ')
        if self._context.get('show_email') and partner.email:
            name = "%s <%s>" % (name, partner.email)
        if self._context.get('html_format'):
            name = name.replace('\n', '<br/>')
        if self._context.get('show_vat') and partner.vat:
            name = "%s ‒ %s" % (name, partner.vat)
        return name

    # # Original name_get
    # def name_get(self):
    #     res = []
    #     for partner in self:
    #         name = partner._get_name()
    #         res.append((partner.id, name))
    #     return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()

        if not recs:
            # domain = ['|', ('id', operator, name), ('last_name', operator, name)]
            # old_domain = ['|', ('name', operator, name), ('id', operator, name)]
            # extended_domain = ['|', '|', ('name', operator, name), ('id', operator, name), ('name', operator, name),
            #                    ('last_name', operator, name)
            #                    ]
            # TODO: Might check on isdigit to checks if digits only match using = operator

            print('DIGIT: ', name.isdigit())
            print('Numeric : ', name.isnumeric())
            print('Alpha: ', name.isalpha())
            print('AlNum: ', name.isalnum())

            if name.isnumeric():
                extended_domain_two = ['|', '|', ('id', '=', name or 0), ('name', operator, name),
                                       ('display_name', operator, name)]
            else:

                extended_domain_two = ['|', '|', ('id', operator, name), ('name', operator, name),
                                       ('display_name', operator, name)]

            recs = self.search(extended_domain_two + args, limit=limit)
        return recs.name_get()
