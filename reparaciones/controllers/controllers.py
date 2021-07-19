# -*- coding: utf-8 -*-
# from odoo import http


# class Reparaciones(http.Controller):
#     @http.route('/reparaciones/reparaciones/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/reparaciones/reparaciones/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('reparaciones.listing', {
#             'root': '/reparaciones/reparaciones',
#             'objects': http.request.env['reparaciones.reparaciones'].search([]),
#         })

#     @http.route('/reparaciones/reparaciones/objects/<model("reparaciones.reparaciones"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('reparaciones.object', {
#             'object': obj
#         })
