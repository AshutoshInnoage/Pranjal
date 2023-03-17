from asyncio.log import logger
from email.policy import default
from math import prod
from select import select
from odoo.tools import float_compare
# import imp
from odoo import fields, models,api
import datetime



class AmazonOrder(models.Model):
    _name = 'manomano.orders'
    _description = 'ManoMano Orders Managment'


    name = fields.Char("Item Title")
    manomano_order_id = fields.Char("Order reference")
    # partner_id = fields.Many2one("res.partner", "Customer")
    first_name = fields.Char("First name")
    email = fields.Char("E-mail")
    last_name = fields.Char("Last name")
    order_status = fields.Char('Order Status')
    shipping_method = fields.Char("Ship Method")
    # date_order = fields.Datetime("Order Date")
    shipping_address = fields.Char("Delivery address 1")
    shipping_zip = fields.Char("Postal Code Delivery")
    shipping_company = fields.Char("delivery company")
    billing_company = fields.Char("Company Billing")
    delivery_city = fields.Char("City Delivery")
    delivery_country = fields.Char("Country Delivery")
    product_id = fields.Many2one("product.product","Product")
    full_name = fields.Char("Delivery name")
    product_status = fields.Char("Product Status")
    product_ref = fields.Char("Ref. product")
    product_name = fields.Char("Product title")
    quantity = fields.Char("Amount")
    unit_price = fields.Char("Unit Price HT")
    total_price = fields.Char("Total price including tax")
    delivery_cost = fields.Char("Shipping costs excluding VAT")
    phone = fields.Char('Telephone free')
    line_id = fields.Char('Line ID')
    name_billing = fields.Char("Name Billing")
    first_name_billing = fields.Char("First Name Billing")
    billing_add1 = fields.Char("Billing Address 1")
    billing_add2 = fields.Char("Billing Address 2")
    billing_add3 = fields.Char("Billing Address 3")
    billing_zip = fields.Char("ZIP Code Billing")
    billing_city = fields.Char("City Billing")
    billing_country = fields.Char("Country Billing")
    order_id = fields.Many2one('sale.order',"Sale Order")
    sku = fields.Char('SKU')
    warehouse = fields.Char('Warehouse Code')
    carrier = fields.Char("Carrier")
    is_pdf = fields.Char("Pdf invoice")
    phone_billing = fields.Char("Telephone billing")
    reciept_code = fields.Char("Recipient code")
    dni = fields.Char("DNI/NIF/CIF/NIE")
    payment_ref = fields.Char("Payment in 3X")
    con_gurantee = fields.Char("Concrete Guarantee Status")

    

    #new fields
    order_date = fields.Char("Date")
    req_ship_date = fields.Char("Required Ship Date")
    ship_method_code = fields.Char("Ship Method Code")
    shipping_address2 = fields.Char("Delivery Address 2")
    shipping_address3 = fields.Char("Delivery Address 3")
    shipping_state = fields.Char("Ship To State")
    tracking_id = fields.Char("Tracking ID")
    ship_date = fields.Char("Delivery date")
    new_added_so = fields.Integer("New Added count",default=0)
    new_added_line = fields.Integer("New Added Line",default=0)
    existing_updated_line = fields.Integer("Existing Updated Line",default=0)
    warehouse_id = fields.Many2one('stock.warehouse', "Warehouse ID")
    shop_id = fields.Many2one('manomano.seller', "Shop")

    @api.model_create_multi
    def create(self,vals):
        result = super(AmazonOrder,self).create(vals)
        for res in result:
            res.warehouse_id = self.env.context.get('warehouse_id')
            res.shop_id = self.env.context.get('shop_id')
            res.line_id = res.id
            res.name = res.manomano_order_id
        return result
    
 

    def map_sale_orders(self):
        total_count = 0
        new_added_so = new_added_line = 0
        sale_orders = self.env['sale.order'].search([]).ids
        for order in self:
            res = self.create_sale_order(order)
            if res:
                total_count +=1
                if res[0].id not in sale_orders:
                    new_added_so += 1
                order.order_id = res[0].id
                if len(res) > 2:
                    new_added_line += 1
                self.check_for_delivery_validation(res[0])

        return self.env['amazon.wizard'].sudo().show_wizard_message(new_added_so, new_added_line, total_count - (new_added_line + new_added_so))

    def validate_pickings(self,order):
        print("Hello")
    
    def check_for_delivery_validation(self, sale_order):
        if sale_order.mirakl_order_state in ["shipped" ,"closed", "received"]:
            if len(sale_order.picking_ids) > 0:

                for delivery in sale_order.picking_ids:
                    if delivery.products_availability == "Available":
                        delivery.action_assign()
                        for move in delivery.move_lines.filtered(lambda m: m.state not in ["done", "cancel"]):
                            rounding = move.product_id.uom_id.rounding
                            if (
                                float_compare(
                                    move.quantity_done,
                                    move.product_qty,
                                    precision_rounding=rounding,
                                )
                                == -1
                            ):
                                for move_line in move.move_line_ids:
                                    move_line.qty_done = move_line.product_uom_qty
                        delivery.with_context(skip_immediate=True, skip_sms=True).button_validate()

    def create_sale_order(self,order):
        new_added_so = new_added_line = existing_line_update = 0
        sale_order = self.env['sale.order'].search([('manomano_order_id', '=', order.manomano_order_id)], limit=1) or False
        product = self.env['product.product'].search([('name','=',order.product_ref)])
        if not sale_order:
            customer_id = self._create_customer(order)
            billing_id = self._create_billing_customer(order, customer_id)
            shipping_id = self._create_shipping_customer(order, customer_id)
            #State Filter for sale order logs
            mirakl_state = None
            odoo_state = None
            if order.order_status:
                if order.order_status == 'Shipped':
                    mirakl_state = 'shipped'
                    odoo_state = 'sale'
                elif order.order_status == 'awaiting_collection':
                    mirakl_state = 'to_collect'
                elif order.order_status == 'Cancelled':
                    mirakl_state = 'canceled'
                    odoo_state = 'cancel'
                elif order.order_status == 'Order refunded':
                    mirakl_state = 'closed'
                    odoo_state = 'sale'
                elif order.order_status == 'Canceled':
                    mirakl_state = 'canceled'
                    odoo_state = 'cancel'
                elif order.order_status == 'Order in preparation' or order.order_status == 'preparation':
                    odoo_state = 'sale'
                    mirakl_state = 'shipping'
                else:
                    mirakl_state = 'closed'
                    odoo_state = 'sale'
                    
            if customer_id:
                sale_order = self.env['sale.order'].sudo().create({
                        'partner_id': customer_id,
                        'partner_invoice_id': billing_id,
                        'partner_shipping_id': shipping_id ,
                        'manomano_order_id': order.manomano_order_id,
                        'market_place_shop': self.shop_id.name,
                        'state': odoo_state,
                        'sku': order.sku,
                        'type_id': self.env['sale.order.type'].search([('id','=', 1)]).id,
                        'warehouse': order.warehouse,
                        'warehouse_id': order.warehouse_id.id,
                        'order_status': order.order_status,
                        'shipping_method': order.shipping_method,
                        'mirakl_order_state': mirakl_state,
                        'shipping_zip': order.shipping_zip,
                        'delivery_city': order.delivery_city,
                        'delivery_country': order.delivery_country,
                        'full_name': order.first_name if order.first_name else '' + '' + order.last_name if order.last_name else '',
                        'total_price': order.total_price,
                        'delivery_cost': order.delivery_cost,
                        'phone': order.phone,
                        'carrier': order.carrier,
                        'first_name': order.name_billing,
                        'last_name': order.last_name,
                        'order_date': order.order_date,
                        'date_order': datetime.datetime.strptime(order.order_date, '%d-%m-%Y').strftime('%Y-%m-%d'),
                        'ship_method_code': order.ship_method_code,
                        'shipping_address2': order.shipping_address2,
                        'shipping_address3': order.shipping_address3,
                        'shipping_state': order.shipping_state,
                        'tracking_id': order.tracking_id,
                        'ship_date': order.ship_date,
                        'billing_zip': order.billing_zip,
                        'billing_city': order.billing_city,
                        'payment_ref': order.payment_ref,
                        'email': order.email,
                    })
                new_added_so += 1
                order_line = self.get_sale_order_lines(sale_order,order)

                logger.info("Calling sale order lines")
                return (sale_order)
        
        elif sale_order and order.line_id not in  sale_order.order_line.ids:
            product = self.env['product.product'].search([('name','=',order.product_ref)])
            ex_product_ids = [line.product_id.id for line in sale_order.order_line]
            if product and product.id not in ex_product_ids:
                line = self.env['sale.order.line'].create({
                    'product_id': product.id,
                                'description': product.name,
                                'name': product.name,
                                'order_id': sale_order.id,
                                'product_uom_qty': order.quantity,
                                # 'price_subtotal': order.total_price,
                                'price_unit': order.total_price,


                })
                logger.info("***LIne added to existing Order :" + sale_order.name + " with ID " + str(line.id))
                new_added_line += 1
                return sale_order, new_added_line
            else:
                mirakl_state = None
                odoo_state = None
                if order.order_status == 'Shipped':
                    mirakl_state = 'shipped'
                    odoo_state = 'sale'
                elif order.order_status == 'awaiting_collection':
                    mirakl_state = 'to_collect'
                elif order.order_status == 'Cancelled':
                    odoo_state = 'cancel'
                    mirakl_state = 'canceled'
                elif order.order_status == 'Order refunded':
                    mirakl_state = 'closed'
                    odoo_state = 'sale'
                elif order.order_status == 'Order in preparation' or order.order_status == 'preparation':
                    odoo_state = 'sale'
                    mirakl_state = 'shipping'
                else:
                    mirakl_state = 'closed'
                    odoo_state = 'sale'
                logger.info("****** Sale Order Already Exist WIth ID " + str(sale_order.id) + " Checking for update")
                for line in sale_order.order_line:
                    if line.product_id == product:
                        line.update({'product_uom_qty': order.quantity,'price_unit': order.total_price})
                existing_line_update += 1
                a = datetime.datetime.strptime(order.order_date, '%d-%m-%Y').strftime('%Y-%m-%d')
                customer_id = self._create_customer(order)
                billing_id = self._create_billing_customer(order, customer_id)
                shipping_id = self._create_shipping_customer(order, customer_id)
                logger.info("Before date change >>>> %s", str(sale_order.date_order))
                sale_order.write({'date_order': a})
                logger.info("After date change >>>> %s", str(sale_order.date_order))

                sale_order.write({'mirakl_order_state': mirakl_state, 'state': odoo_state,'order_status': order.order_status,'partner_id': customer_id, 'partner_invoice_id': billing_id, 'partner_shipping_id': shipping_id})
                return (sale_order)
        # else:

    def get_sale_order_lines(self,order,order1):
        lines=[]
        if order1.product_ref and "<br/>" in order1.product_ref:
            prods = order1.product_ref.split("<br/>")
            for index in range(len(prods)):
                product = self.env['product.product'].search([('name','=',prods[index])])
                if product:
                    line = self.env['sale.order.line'].create({
                                        'product_id': product.id,
                                        'name': product.name,
                                        'order_id': order.id,
                                        'product_uom' : product.uom_id.id,
                                        'product_uom_qty': order1.quantity.split("<br/>")[index],
                                        'price_unit': order1.unit_price.split("<br/>")[index],
                    })
                    lines.append(line)
        elif order1.product_ref and ','  in order1.product_ref:
            prods = order1.product_ref.split("<br/>")
            for index in range(len(prods)):
                product = self.env['product.product'].search([('name','=',prods[index])])
                if product:
                    line = self.env['sale.order.line'].create({
                                        'product_id': product.id,
                                        'name': product.name,
                                        'order_id': order.id,
                                        'product_uom' : product.uom_id.id,
                                        'product_uom_qty': order1.quantity.split("<br/>")[index],
                                        'price_unit': order1.unit_price.split("<br/>")[index],
                    })
                    lines.append(line)
                
        else:
            product = self.env['product.product'].search([('name','=',order1.product_ref)])
            if product:
                line = self.env['sale.order.line'].create({
                                    'product_id': product.id,
                                    'name': product.name,
                                    'order_id': order.id,
                                    'product_uom' : product.uom_id.id,
                                    'product_uom_qty': order1.quantity,
                                    'price_unit': order1.total_price,
                                    # 'price_subtotal': order1.total_price,
                })
                lines.append(line)
        return lines

    def _create_customer(self, order):
        customer_env = self.env['res.partner']
        customer = customer_env.search([('phone', '=', order.phone)],limit=1) or False
        if not customer:
            customer = customer_env.create({
                    'company_type': 'person',
                    'name': (order.first_name if order.first_name else '') + ' ' + order.last_name if order.last_name else '',
                    'phone': order.phone,
                    'street': order.shipping_address,
                    # 'street2': order.billing_add2
                    'zip': order.billing_zip,
                    'city': order.billing_city,
                    'country_id': self.env['res.country'].search([('name','=', order.delivery_country)],limit=1).id,
            })
        else:
            customer.country_id = self.env['res.country'].search([('name','=',order.delivery_country)]).id
            customer.name = (order.first_name if order.first_name else '') + ' ' + order.last_name if order.last_name else ''
            customer.zip = order.billing_zip
            customer.city = order.billing_city
            customer.phone = order.phone
        return customer.id



    def _create_billing_customer(self,order, customer_id):
        billing_customer = self.env['res.partner'].search([('type', '=', 'invoice'), ('parent_id', '=', customer_id)]) or False
        if not billing_customer:
            country = state = full_name = False
            billing_customer = self.env['res.partner'].create({
                'company_type': 'person',
                'type': 'invoice',
                'name': (order.name_billing if order.name_billing else '') + ' ' + order.first_name_billing if order.first_name_billing else '',
                'parent_id': customer_id,
                'city': order.billing_city,
                'street': order.billing_add1,
                'street2': order.billing_add2,
                # 'state_id': state.id if state else False,
                'country_id': self.env['res.country'].search([('name', '=', order.billing_country)]).id or False,
                'country_code': country.code if country else False,
                'zip': order.billing_zip,
            })
        else:
            billing_customer.country_id = self.env['res.country'].search([('name','=',order.delivery_country)]).id
            billing_customer.zip = order.billing_zip or order.shipping_zip
            billing_customer.name = (order.name_billing if order.name_billing else '') + ' ' + order.first_name_billing if order.first_name_billing else ''
            billing_customer.city = order.delivery_city or order.billing_city
            billing_customer.phone = order.phone
            billing_customer.street = order.billing_add1
            billing_customer.parent_id =  customer_id

            billing_customer.street2 =  order.billing_add2
            
        return billing_customer.id



    def _create_shipping_customer(self, order, customer_id):
        shipping_customer = self.env['res.partner'].search([('type', '=', 'invoice'), ('parent_id', '=', customer_id)]) or False
        if not shipping_customer:
            country = state = full_name = False
            shipping_customer = self.env['res.partner'].create({
                'company_type': 'person',
                'type': 'delivery',
                'name': (order.first_name if order.first_name else '') + ' ' + order.last_name if order.last_name else '',
                'parent_id': customer_id,
                'street': order.shipping_address,
                'city': order.delivery_city,
                'street2': order.shipping_address2,
                # 'state_id': state.id if state else False,
                'country_id': self.env['res.country'].search([('name', '=', order.delivery_country)]).id,
                'country_code': country.code if country else False,
                'zip': order.shipping_zip,
            })
        else:
            shipping_customer.country_id = self.env['res.country'].search([('name','=',order.delivery_country)]).id
            shipping_customer.zip = order.shipping_zip or order.billing_zip
            shipping_customer.city = order.delivery_city or order.billing_city
            shipping_customer.name = (order.first_name if order.first_name else '') + ' ' + order.last_name if order.last_name else ''
            shipping_customer.phone = order.phone
            shipping_customer.street = order.shipping_address
            shipping_customer.parent_id =  customer_id

            shipping_customer.street2 =  order.shipping_address2
        return shipping_customer.id




