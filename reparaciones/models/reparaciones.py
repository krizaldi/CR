# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from datetime import datetime, timedelta
import pytz
import logging, ast
from odoo.exceptions import AccessError, UserError, ValidationError
_logger = logging.getLogger(__name__)


class Reparaciones(models.Model):
    _inherit = 'sale.order'

    flota = fields.Many2one(comodel_name='fleet.vehicle',string='Vehículo')
    responsable = fields.Many2one(comodel_name='res.users',string='Responsable')
    servicios = fields.One2many(comodel_name='sale.order.line',inverse_name='order_id',string='Servicios',)
    check=fields.Boolean(default=False)
    operations = fields.One2many('repair.product', 'order_id', 'Parts', states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True, auto_join=True)
    fees_lines = fields.One2many('repair.service', 'order_id', 'Operations', states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True, auto_join=True)
    tipo_reparacion=fields.Selection([('pintura','Taller Pintura'),('industrial','Taller Industrial'),('servicio','Taller Servicio'),('web','WEB')])

    # @api.depends('state')
    def conf(self):
        self.action_confirm()
        _logger.info("conf()****************")
        if self.state == 'sale':
            for pi in self.picking_ids.filtered(lambda x:x.state not in ['done','cancel']):
                pi.do_unreserve()
            for linea in self.order_line.filtered(lambda x:x.type=='remove'):
                p=self.env['stock.move'].search([['sale_line_id','=',linea.id],['state','not in',['done','cancel','assigned']]])
                p._action_cancel()
                p.unlink()
            for pi in self.picking_ids.filtered(lambda x:x.state not in ['done','cancel']):
                pi.action_assign()
                #if linea.tipo == 'remove':
                    #for picking in self.picking_ids:
                    #    if picking.move_line_ids_without_package:
                    #       for linea_orden in picking.move_line_ids_without_package:
                    #            if linea_orden.product_id.id == linea.product_id.id:
                    #                picking.move_line_ids_without_package = (3, linea_orden.id, 0)

    def validate_picking(self):
        if self.state == 'sale':
            P=self.picking_ids.filtered(lambda x:x.state not in ['done','cancel'])
            for pi in P:
                if pi.state == 'assigned':
                    pi.action_confirm()
                    pi.move_lines._action_assign()
                    pi.action_assign()
                    return pi.button_validate()

    # @api.onchange('operations','fees_lines')
    # def addLine(self):
    #     for record in self:
    #         record.order_line=[(5,0,0)]
    #         data=record.operations.filtered(lambda x:x.type=='add')
    #         for da in data:
    #             pro=dict()
    #             pro['product_id']=da.product_id.id
    #             pro['price_unit']=da.price_unit
    #             pro['tax_id']=da.tax_id.ids
    #             pro['product_uom_qty']=da.product_uom_qty
    #             record.order_line=[(0, 0,pro)]
    #         for da2 in record.fees_lines:
    #             pro=dict()
    #             pro['product_id']=da2.product_id.id
    #             pro['price_unit']=da2.price_unit
    #             pro['tax_id']=da2.tax_id.ids
    #             pro['product_uom_qty']=da2.product_uom_qty
    #             record.order_line=[(0, 0,pro)]
    #         for o in record.order_line:
    #             o.product_id_change()
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'sale.order', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('sale.order', sequence_date=seq_date) or _('New')

        # Makes sure partner_invoice_id', 'partner_shipping_id' and 'pricelist_id' are defined
        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id', 'pricelist_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            addr = partner.address_get(['delivery', 'invoice'])
            vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
            vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
            vals['pricelist_id'] = vals.setdefault('pricelist_id', partner.property_product_pricelist and partner.property_product_pricelist.id)
        result = super(Reparaciones, self).create(vals)
        op=result.operations
        _logger.info(op)
        if('operations' in vals):
            i=0
            for r in vals['operations']:
                r[2]['order_id']=result.id
                if('sale_line_id' in r[2]):
                    del r[2]['sale_line_id']
                sl=self.env['sale.order.line'].create(r[2])
                result.operations[0].write({'sale_line_id':sl.id})
                i=i+1
        if('fees_lines' in vals):
            i=0
            for r in vals['fees_lines']:
                r[2]['order_id']=result.id
                if('tecnico' in r[2]):
                    del r[2]['tecnico']
                if('sale_line_id' in r[2]):
                    del r[2]['sale_line_id']
                sl=self.env['sale.order.line'].create(r[2])
                result.fees_lines[0].write({'sale_line_id':sl.id})
                i=i+1
        return result