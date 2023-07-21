from odoo import models, fields
from odoo.tools.date_utils import date
from datetime import timedelta


class ApiLog(models.Model):
    _name = "api.log"
    _order = "id desc"
    _description = "API logs"
    _rec_name = 'request_path'

    request_resource = fields.Char()

    request = fields.Char("Request")
    request_data = fields.Text("Request Data")

    request_scheme = fields.Char(string="Scheme")
    request_path = fields.Char(string="Path")
    request_method = fields.Char(string="Method")
    request_remote_address = fields.Char(string="Remote Address")
    request_headers = fields.Text(string="Headers")
    request_parameters = fields.Text(string="Parameters")

    response_data = fields.Text(string="Response Data")

    response_code = fields.Char(string="Code")
    response_msg = fields.Text(string="Message")

    def remove_old_log(self):
        """
        Delete logs older than 2 weeks
        :return:
        """
        today = date.today()
        one_week_ago = today - timedelta(days=14)

        self.search([('create_date', '<=', one_week_ago), ('response_code', '!=', '500')]).unlink()
