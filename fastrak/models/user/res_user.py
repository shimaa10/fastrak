import uuid
import base64

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    # namespace_ids = fields.Many2many("openapi.namespace", string="Allowed Integrations")
    api_token = fields.Char(
        "API Token",
        default=lambda self: self._get_unique_api_token(),
        required=True,
        copy=False,
        help="Authentication token for access to API (/api).",
        readonly=True
    )
    auth_token = fields.Char(readonly=True)

    token_value = fields.Char(compute='_get_token_value')

    def _get_token_value(self):
        self.ensure_one()
        if self.api_token and self.auth_token:
            self.token_value = self.api_token[:5] + 'x' * len(self.api_token[5:])
        else:
            self.token_value = 'Not Assigned Yet'

    def reset_api_token(self):
        for record in self:
            record.write({"api_token": self._get_unique_api_token()})

    def _get_unique_api_token(self):
        auth_token = str(uuid.uuid4())
        api_token = base64.b64encode(auth_token.encode('UTF-8'))
        self.auth_token = auth_token

        while self.search_count([("api_token", "=", api_token), ("auth_token", "=", auth_token)]):
            auth_token = str(uuid.uuid4())
            api_token = base64.b64encode(auth_token.encode('UTF-8'))
            self.auth_token = auth_token
        return api_token

    @api.model
    def reset_all_api_tokens(self):
        self.search([]).reset_api_token()

    def _get_db_name(self):
        dbName = self._cr.dbname
        return dbName
