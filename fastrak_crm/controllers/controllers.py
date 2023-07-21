# -*- coding: utf-8 -*-
# from odoo import http


# class FastrakCrm(http.Controller):
#     @http.route('/fastrak_crm/fastrak_crm/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/fastrak_crm/fastrak_crm/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('fastrak_crm.listing', {
#             'root': '/fastrak_crm/fastrak_crm',
#             'objects': http.request.env['fastrak_crm.fastrak_crm'].search([]),
#         })

#     @http.route('/fastrak_crm/fastrak_crm/objects/<model("fastrak_crm.fastrak_crm"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('fastrak_crm.object', {
#             'object': obj
#         })
