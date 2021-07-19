# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import AccessError, UserError, ValidationError
from collections import defaultdict
import datetime

class RepairProduct(models.Model):
    _name = 'repair.product'
    _description = 'Repair Product'
    name = fields.Text('Description', required=True)
    order_id = fields.Many2one('sale.order', 'Repair Order Reference',index=True, ondelete='cascade')
    type = fields.Selection([('add', 'Add'),('remove', 'Remove')], 'Type', default='add', required=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price')
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', store=True, digits=0)
    tax_id = fields.Many2many('account.tax', relation = 'tax_repair_rel', column1 = 'id1', column2 = 'id2', string = 'Taxes')
    product_uom_qty = fields.Float('Quantity', default=1.0,digits='Product Unit of Measure', required=True)
    product_uom = fields.Many2one('uom.uom', 'Product Unit of Measure',required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    invoice_line_id = fields.Many2one('account.move.line', 'Invoice Line',copy=False, readonly=True)
    sale_line_id=fields.Many2one('sale.order.line')
    #location_id = fields.Many2one('stock.location', 'Source Location',index=True, required=True)
    #location_dest_id = fields.Many2one('stock.location', 'Dest. Location',index=True, required=True)
    move_id = fields.Many2one('stock.move', 'Inventory Move',copy=False, readonly=True)
    #lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial')
    state = fields.Selection([('draft', 'Draft'),('confirmed', 'Confirmed'),('done', 'Done'),('cancel', 'Cancelled')], 'Status', default='draft',copy=False, readonly=True, required=True,help='The status of a repair line is set automatically to the one of the linked repair order.')
    product_type = fields.Selection(related='product_id.type')
    virtual_available_at_date = fields.Float(compute='_compute_qty_at_date')
    scheduled_date = fields.Datetime(compute='_compute_qty_at_date')
    free_qty_today = fields.Float(compute='_compute_qty_at_date')
    qty_available_today = fields.Float(compute='_compute_qty_at_date')
    warehouse_id = fields.Many2one('stock.warehouse', compute='_compute_qty_at_date')
    qty_to_deliver = fields.Float(compute='_compute_qty_to_deliver')
    is_mto = fields.Boolean(default=False)
    display_qty_widget = fields.Boolean(compute='_compute_qty_to_deliver')
    qty_delivered = fields.Float('Delivered Quantity', copy=False, compute='_compute_qty_delivered', inverse='_inverse_qty_delivered', compute_sudo=True, store=True, digits='Product Unit of Measure', default=0.0)
    customer_lead = fields.Float(
        'Lead Time', required=True, default=0.0,
        help="Number of days between the order confirmation and the shipping of the products to the customer")

    qty_delivered_method=fields.Selection([('manual','manual'),('analytic','analytic')],default='analytic')
    qty_delivered_manual=fields.Float(compute='_compute_qty_delivered')

    @api.depends('qty_delivered_method', 'qty_delivered_manual')
    def _compute_qty_delivered(self):
        """ This method compute the delivered quantity of the SO lines: it covers the case provide by sale module, aka
            expense/vendor bills (sum of unit_amount of AAL), and manual case.
            This method should be overridden to provide other way to automatically compute delivered qty. Overrides should
            take their concerned so lines, compute and set the `qty_delivered` field, and call super with the remaining
            records.
        """
        # compute for analytic lines
        #lines_by_analytic = self.filtered(lambda sol: sol.qty_delivered_method == 'analytic')
        #mapping = lines_by_analytic._get_delivered_quantity_by_analytic([('amount', '<=', 0.0)])
        #for so_line in lines_by_analytic:
        #    so_line.qty_delivered = mapping.get(so_line.id or so_line._origin.id, 0.0)
        # compute for manual lines
        for line in self:
            line.qty_delivered = line.qty_delivered_manual or 0.0



    # def _get_delivered_quantity_by_analytic(self, additional_domain):
    #     """ Compute and write the delivered quantity of current SO lines, based on their related
    #         analytic lines.
    #         :param additional_domain: domain to restrict AAL to include in computation (required since timesheet is an AAL with a project ...)
    #     """
    #     result = {}

    #     # avoid recomputation if no SO lines concerned
    #     if not self:
    #         return result

    #     # group analytic lines by product uom and so line
    #     domain = expression.AND([[('so_line', 'in', self.ids)], additional_domain])
    #     data = self.env['account.analytic.line'].read_group(
    #         domain,
    #         ['so_line', 'unit_amount', 'product_uom_id'], ['product_uom_id', 'so_line'], lazy=False
    #     )

    #     # convert uom and sum all unit_amount of analytic lines to get the delivered qty of SO lines
    #     # browse so lines and product uoms here to make them share the same prefetch
    #     lines = self.browse([item['so_line'][0] for item in data])
    #     lines_map = {line.id: line for line in lines}
    #     product_uom_ids = [item['product_uom_id'][0] for item in data if item['product_uom_id']]
    #     product_uom_map = {uom.id: uom for uom in self.env['uom.uom'].browse(product_uom_ids)}
    #     for item in data:
    #         if not item['product_uom_id']:
    #             continue
    #         so_line_id = item['so_line'][0]
    #         so_line = lines_map[so_line_id]
    #         result.setdefault(so_line_id, 0.0)
    #         uom = product_uom_map.get(item['product_uom_id'][0])
    #         if so_line.product_uom.category_id == uom.category_id:
    #             qty = uom._compute_quantity(item['unit_amount'], so_line.product_uom, rounding_method='HALF-UP')
    #         else:
    #             qty = item['unit_amount']
    #         result[so_line_id] += qty

    #     return result

    @api.onchange('qty_delivered')
    def _inverse_qty_delivered(self):
        """ When writing on qty_delivered, if the value should be modify manually (`qty_delivered_method` = 'manual' only),
            then we put the value in `qty_delivered_manual`. Otherwise, `qty_delivered_manual` should be False since the
            delivered qty is automatically compute by other mecanisms.
        """
        for line in self:
            if line.qty_delivered_method == 'manual':
                line.qty_delivered_manual = line.qty_delivered
            else:
                line.qty_delivered_manual = 0.0

    @api.depends('product_id', 'product_uom_qty', 'qty_delivered', 'state', 'product_uom')
    def _compute_qty_to_deliver(self):
        """Compute the visibility of the inventory widget."""
        for line in self:
            line.qty_to_deliver = line.product_uom_qty - line.qty_delivered
            if line.state == 'draft' and line.product_type == 'product' and line.product_uom and line.qty_to_deliver > 0:
                line.display_qty_widget = True
            else:
                line.display_qty_widget = False

    @api.depends('product_id', 'customer_lead', 'product_uom_qty', 'product_uom', 'order_id.warehouse_id', 'order_id.commitment_date')
    def _compute_qty_at_date(self):
        """ Compute the quantity forecasted of product at delivery date. There are
        two cases:
         1. The quotation has a commitment_date, we take it as delivery date
         2. The quotation hasn't commitment_date, we compute the estimated delivery
            date based on lead time"""
        qty_processed_per_product = defaultdict(lambda: 0)
        grouped_lines = defaultdict(lambda: self.env['repair.product'])
        # We first loop over the SO lines to group them by warehouse and schedule
        # date in order to batch the read of the quantities computed field.
        for line in self:
            if not (line.product_id and line.display_qty_widget):
                continue
            line.warehouse_id = line.order_id.warehouse_id
            if line.order_id.commitment_date:
                date = line.order_id.commitment_date
            else:
                date = datetime.datetime.now()
            grouped_lines[(line.warehouse_id.id, date)] |= line

        treated = self.browse()
        for (warehouse, scheduled_date), lines in grouped_lines.items():
            product_qties = lines.mapped('product_id').with_context(to_date=scheduled_date, warehouse=warehouse).read([
                'qty_available',
                'free_qty',
                'virtual_available',
            ])
            qties_per_product = {
                product['id']: (product['qty_available'], product['free_qty'], product['virtual_available'])
                for product in product_qties
            }
            for line in lines:
                line.scheduled_date = scheduled_date
                qty_available_today, free_qty_today, virtual_available_at_date = qties_per_product[line.product_id.id]
                line.qty_available_today = qty_available_today - qty_processed_per_product[line.product_id.id]
                line.free_qty_today = free_qty_today - qty_processed_per_product[line.product_id.id]
                line.virtual_available_at_date = virtual_available_at_date - qty_processed_per_product[line.product_id.id]
                if line.product_uom and line.product_id.uom_id and line.product_uom != line.product_id.uom_id:
                    line.qty_available_today = line.product_id.uom_id._compute_quantity(line.qty_available_today, line.product_uom)
                    line.free_qty_today = line.product_id.uom_id._compute_quantity(line.free_qty_today, line.product_uom)
                    line.virtual_available_at_date = line.product_id.uom_id._compute_quantity(line.virtual_available_at_date, line.product_uom)
                qty_processed_per_product[line.product_id.id] += line.product_uom_qty
            treated |= lines
        remaining = (self - treated)
        remaining.virtual_available_at_date = False
        remaining.scheduled_date = False
        remaining.free_qty_today = False
        remaining.qty_available_today = False
        remaining.warehouse_id = False

    # @api.depends('product_id', 'repair_id.warehouse_id', 'product_id.route_ids')
    # def _compute_is_mto(self):
    #     """ Verify the route of the product based on the warehouse
    #         set 'is_available' at True if the product availibility in stock does
    #         not need to be verified, which is the case in MTO, Cross-Dock or Drop-Shipping
    #     """
    #     self.is_mto = False
    #     for line in self:
    #         if not line.display_qty_widget:
    #             continue
    #         product = line.product_id
    #         #product_routes = line.route_id or (product.route_ids + product.categ_id.total_route_ids)

    #         # Check MTO
    #         #mto_route = line.repair_id.warehouse_id.mto_pull_id.route_id
    #         #if not mto_route:
    #             #try:
    #             #    mto_route = self.env['stock.warehouse']._find_global_route('stock.route_warehouse0_mto', _('Make To Order'))
    #             #except UserError:
    #                 # if route MTO not found in ir_model_data, we treat the product as in MTS
    #          #       pass

    #         #if mto_route and mto_route in product_routes:
    #         #    line.is_mto = True
    #         #else:
    #         line.is_mto = False
    @api.constrains('lot_id', 'product_id')
    def constrain_lot_id(self):
        for line in self.filtered(lambda x: x.product_id.tracking != 'none' and not x.lot_id):
            raise ValidationError(_("Serial number is required for operation line with product '%s'") % (line.product_id.name))

    #@api.depends('price_unit', 'repair_id', 'product_uom_qty', 'product_id', 'repair_id.invoice_method')
    @api.depends('price_unit', 'order_id', 'product_uom_qty', 'product_id')
    def _compute_price_subtotal(self):
        for line in self:
            taxes = line.tax_id.compute_all(line.price_unit, line.order_id.pricelist_id.currency_id, line.product_uom_qty, line.product_id, line.order_id.partner_id)
            line.price_subtotal = taxes['total_excluded']

    @api.onchange('type', 'order_id')
    def onchange_operation_type(self):
        """ On change of operation type it sets source location, destination location
        and to invoice field.
        @param product: Changed operation type.
        @param guarantee_limit: Guarantee limit of current record.
        @return: Dictionary of values.
        """
        if not self.type:
            self.location_id = False
            self.location_dest_id = False
        elif self.type == 'add':
            self.onchange_product_id()
            args = self.order_id.company_id and [('company_id', '=', self.order_id.company_id.id)] or []
            warehouse = self.env['stock.warehouse'].search(args, limit=1)
            self.location_id = warehouse.lot_stock_id
            self.location_dest_id = self.env['stock.location'].search([('usage', '=', 'production')], limit=1).id
        else:
            self.price_unit = 0.0
            self.tax_id = False
            self.location_id = self.env['stock.location'].search([('usage', '=', 'production')], limit=1).id
            self.location_dest_id = self.env['stock.location'].search([('scrap_location', '=', True)], limit=1).id

    @api.onchange('order_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        """ On change of product it sets product quantity, tax account, name,
        uom of product, unit price and price subtotal. """
        partner = self.order_id.partner_id
        pricelist = self.order_id.pricelist_id
        if not self.product_id or not self.product_uom_qty:
            return
        if self.product_id:
            if partner:
                self.name = self.product_id.with_context(lang=partner.lang).display_name
            else:
                self.name = self.product_id.display_name
            if self.product_id.description_sale:
                if partner:
                    self.name += '\n' + self.product_id.with_context(lang=partner.lang).description_sale
                else:
                    self.name += '\n' + self.product_id.description_sale
            self.product_uom = self.product_id.uom_id.id
        if self.type != 'remove':
            if partner and self.product_id:
                fp = partner.property_account_position_id
                if not fp:
                    # Check automatic detection
                    pass
                    #fp_id = self.env['account.fiscal.position'].get_fiscal_position(partner.id, delivery_id=self.repair_id.address_id.id)
                    #fp = self.env['account.fiscal.position'].browse(fp_id)
                taxes = self.product_id.taxes_id.filtered(lambda x: x.company_id == self.order_id.company_id)
                self.tax_id = fp.map_tax(taxes, self.product_id, partner).ids
            warning = False
            #if not pricelist:
            #    warning = {
            #        'title': _('No pricelist found.'),
            #        'message':
            #           _('You have to select a pricelist in the Repair form !\n Please set one before choosing a product.')}
            #    return {'warning': warning}
            #else:
            self._onchange_product_uom()

    @api.onchange('product_uom')
    def _onchange_product_uom(self):
        partner = self.order_id.partner_id
        pricelist = self.order_id.pricelist_id
        if pricelist and self.product_id and self.type != 'remove':
            price = pricelist.get_product_price(self.product_id, self.product_uom_qty, partner, uom_id=self.product_uom.id)
            #if price is False:
            #    warning = {
            #        'title': _('No valid pricelist line found.'),
            #        'message':
            #            _("Couldn't find a pricelist line matching this product and quantity.\nYou have to change either the product, the quantity or the pricelist.")}
             #   return {'warning': warning}
            #else:
            self.price_unit = price

    def unlink(self):
        if(self.order_id.state in ['sale','done']):
            raise UserError(_('You can not remove an order line once the sales order is confirmed.\nYou should rather set the quantity to 0.'))
        else:
            self.sale_line_id.unlink()
        return super(RepairProduct, self).unlink()

    def write(self,values):
        if(self.sale_line_id):
            v=values
            if('sale_line_id' in v):
                del v['sale_line_id']
            self.sale_line_id.write(v)
        return super(RepairProduct,self).write(values)

class RepairService(models.Model):
    _name = 'repair.service'
    _description = 'Reparaciones Services'
    order_id = fields.Many2one('sale.order', 'Repair Order Reference',index=True, ondelete='cascade', required=True)
    name = fields.Text('Description', index=True, required=True)
    product_id = fields.Many2one('product.product', 'Product')
    product_uom_qty = fields.Float('Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price')
    product_uom = fields.Many2one('uom.uom', 'Product Unit of Measure', required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', store=True, digits=0)
    tax_id = fields.Many2many('account.tax',relation = 'tax_repair_service_rel', column1 = 'id1', column2 = 'id2', string = 'Taxes')
    invoice_line_id = fields.Many2one('account.move.line', 'Invoice Line', copy=False, readonly=True)
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    tecnico=fields.Many2one(comodel_name='res.users',string='Tecnico')
    sale_line_id=fields.Many2one('sale.order.line')
    
    @api.depends('price_unit', 'order_id', 'product_uom_qty', 'product_id')
    def _compute_price_subtotal(self):
        for fee in self:
            taxes = fee.tax_id.compute_all(fee.price_unit, fee.order_id.pricelist_id.currency_id, fee.product_uom_qty, fee.product_id, fee.order_id.partner_id)
            fee.price_subtotal = taxes['total_excluded']

    @api.onchange('order_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        """ On change of product it sets product quantity, tax account, name,
        uom of product, unit price and price subtotal. """
        if not self.product_id:
            return

        partner = self.order_id.partner_id
        pricelist = self.order_id.pricelist_id

        if partner and self.product_id:
            fp = partner.property_account_position_id
            if not fp:
                # Check automatic detection
                pass
                #fp_id = self.env['account.fiscal.position'].get_fiscal_position(partner.id, delivery_id=self.repair_id.address_id.id)
                #fp = self.env['account.fiscal.position'].browse(fp_id)
            taxes = self.product_id.taxes_id.filtered(lambda x: x.company_id == self.order_id.company_id)
            self.tax_id = fp.map_tax(taxes, self.product_id, partner).ids
        if self.product_id:
            if partner:
                self.name = self.product_id.with_context(lang=partner.lang).display_name
            else:
                self.name = self.product_id.display_name
            self.product_uom = self.product_id.uom_id.id
            if self.product_id.description_sale:
                if partner:
                    self.name += '\n' + self.product_id.with_context(lang=partner.lang).description_sale
                else:
                    self.name += '\n' + self.product_id.description_sale

        warning = False
        #if not pricelist:
        #    warning = {
        #        'title': _('No pricelist found.'),
        #        'message':
        #            _('You have to select a pricelist in the Repair form !\n Please set one before choosing a product.')}
        #    return {'warning': warning}
        #else:
        self._onchange_product_uom()

    def unlink(self):
        if(self.order_id.state in ['sale','done']):
            raise UserError(_('You can not remove an order line once the sales order is confirmed.\nYou should rather set the quantity to 0.'))
        else:
            self.sale_line_id.unlink()
        return super(RepairService, self).unlink()

    def write(self,values):
        if(self.sale_line_id):
            v=values
            if('sale_line_id' in v):
                del v['sale_line_id']
            self.sale_line_id.write(v)
        return super(RepairService,self).write(values)

    @api.onchange('product_uom')
    def _onchange_product_uom(self):
        partner = self.order_id.partner_id
        pricelist = self.order_id.pricelist_id
        if pricelist and self.product_id:
            price = pricelist.get_product_price(self.product_id, self.product_uom_qty, partner, uom_id=self.product_uom.id)
            #if price is False:
                #warning = {
                #    'title': _('No valid pricelist line found.'),
                 #   'message':
                 #       _("Couldn't find a pricelist line matching this product and quantity.\nYou have to change either the product, the quantity or the pricelist.")}
                #return {'warning': warning}
            #else:
            self.price_unit = price

