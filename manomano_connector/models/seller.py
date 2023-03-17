from dataclasses import field
from odoo import fields,api, models,_
import requests
import pytz
import datetime
from odoo.exceptions import UserError, ValidationError
# import xmltodict
import pprint
import logging
_logger = logging.getLogger(__name__)

class Seller(models.Model):
    _name = 'manomano.seller'
    _description = 'ManoMano Seller Managment'

    name = fields.Char("name")
    seller_id = fields.Char("Seller Id")
    seller_token = fields.Char("Seller Access Token",store=True)
    product_count = fields.Integer("")
    state = fields.Selection([
        ('draft','Draft'),
        ('done','Confirmed'),
        ('cancel','Cancelled'),
    ])


    api_login = fields.Char("Login ID")
    api_password = fields.Char("Password")
    warehouse_id = fields.Many2one("stock.warehouse", "Warehouse",required=True)
    test_token = fields.Char("",default="")

    # Only authorize person view

    api_key = fields.Char("Seller API Key", required = True)
    # customer_id = fields.Char("Seller Id", required = True)
    geting_url = fields.Char("Seller URL", required = True) 
    activate = fields.Boolean("Activate")

    #order management field
    seller_contract_id = fields.Integer("Seller Id",required = True)
    order_reference = fields.Char("Order Refrence")
    status = fields.Selection([
        ('pending','Pending'),
        ('waiting','Wating Period'),
        ('refused','Refused'),
        ('shipped','Shipped'),
        ('preparation','Preparation'),
        ('refunded','Refunded'),
        ('refunding','Refunding'),
        ('remorse_period','Remorse Period'),

    ])
    carrier =fields.Char("Carrier")
    created_at_start = fields.Datetime("Create Date",default=fields.Datetime.now())
    created_at_end = fields.Date("End Date")
    status_updated_at_start = fields.Date("Status Start")
    status_updated_at_end = fields.Date("Status End")
    limit = fields.Integer("Limit")
    page = fields.Integer("Page")
    is_filter_activate = fields.Boolean("Activate Filters")
    # activate_shop = fields.Boolean("Activate Shop")


    def get_all_orders(self):
        call = self.geting_url+"/orders/v1/orders"

        # Add Seller Id 
        if self.seller_contract_id:
            call += "?seller_contract_id=" + str(self.seller_contract_id)

        _logger.info("Call~~~~~~~~%r ;;;;;", call)

        #Getting data
        try:
            response = requests.get(call,headers={'x-api-key': self.api_key,'Accept': 'application/json'}).json()
        except Exception as err:
            _logger.info("!!!!!Order Getting Error~~~~~~~~%r ;;;;;",err)
            response = {}
        _logger.info("Call~~~~~~~~%r ;;;;;", response)
        if response:
            for order in response.get("content"):
                self.create_sale_order_api(order)
    fetch = content[]
    def create_sale_order_api(self, order):
         
         sale_order_api = self.env['sale.order'].search([('seller_id', '=', order.get(''))], limit=1)
        


 
    def get_orders(self):
        pass


    @api.onchange('seller_token')
    def onchange_token(self):
        if not self.seller_token:
            self.write({'product_count': 0})

    def get_orders(self):
        print("Get Orders")

    def process_shipping_orders(self):
        sale_orders = self.env['sale.order'].search([ ('manomano_order_id', '!=', False), ('mirakl_order_state','=','shipping')])
        self.env['shop.integrator'].separate_warehouse_orders(sale_orders)
        return True
        
    def create_sale_order(self,order):
        sale_order = self.env['sale.order'].search([('cdiscount_order_id', '=', order.get('OrderNumber'))], limit=1) or False

        if not sale_order:
            customer_id = self._create_customer(order)
            # billing_id = self._create_billing_customer(order.get("BillingAddress"), customer_id)
            shipping_id = self._create_shipping_customer(order.get("ShippingAddress"), customer_id)
            order_line = self.get_sale_order_lines(order.get('OrderLineList'),sale_order)
            if customer_id and shipping_id and order_line:
                sale_order = self.env['sale.order'].sudo().create({
                        'partner_id': customer_id,
                        'partner_shipping_id': shipping_id ,
                        'cdiscount_order_id': order.get('OrderNumber'),
                        'order_line': order_line,
                    })
                _logger.info("Sale Order Created~~~~~~%r ;;;;;", sale_order)
                return sale_order
        else:
                _logger.info("Sale Order Already Exist~~~~~~%r ;;;;;", sale_order)


    def get_sale_order_lines(self, order_lines,sale_order):
        sale_order_lines = []
        if isinstance(order_lines['OrderLine'], list):
            for line in order_lines['OrderLine']:
                product_id =  self._create_product(line)
                if product_id and product_id > 0:
                    added_line = (0, 0, {
                            'product_id': product_id,
                            'commission_fee': line.get('commission_fee') if line.get('commission_fee') else False,
                            'description': line.get('Name') if line.get('Name') else False,
                            'offer_sku': line.get('offer_sku') if line.get('offer_sku') else False,
                            'offer_state_code': line.get('offer_state_code') if line.get('offer_state_code') else False,
                            'order_line_index': line.get('order_line_index') if line.get('order_line_index') else False,
                            'order_line_state_reason_code': line.get('order_line_state_reason_code') if line.get('order_line_state_reason_code') else False,
                            'order_line_state_reason_label': line.get('order_line_state_reason_label') if line.get('order_line_state_reason_label') else False,
                            'order_line_index': line.get('order_line_index') if line.get('order_line_index') else False,
                            'price_additional_info': line.get('price_additional_info') if line.get('price_additional_info') else False,
                            'shipping_price': line.get('shipping_price') if line.get('shipping_price') else False,
                            'shipping_price_additional_unit': line.get('shipping_price_additional_unit') if line.get('shipping_price_additional_unit') else False,
                            'shipping_price_unit': line.get('shipping_price_unit') if line.get('shipping_price_unit') else False,
                            'total_commission': line.get('total_commission') if line.get('total_commission') else False,
                        })

                    sale_order_lines.append(added_line)
            print(sale_order_lines)
            print(len(sale_order_lines))
        else:
            prod_id = self.env['product.product'].search([('name', '=', order_lines['OrderLine']['SellerProductId'])]).id
            line = order_lines['OrderLine']
            if prod_id > 0:
                added_line = (0, 0, {
                    'product_id': prod_id,
                            'commission_fee': line.get('commission_fee') if line.get('commission_fee') else False,
                            'description': line.get('Name') if line.get('Name') else False,
                            'offer_sku': line.get('offer_sku') if line.get('offer_sku') else False,
                            'offer_state_code': line.get('offer_state_code') if line.get('offer_state_code') else False,
                            'order_line_index': line.get('order_line_index') if line.get('order_line_index') else False,
                            'order_line_state_reason_code': line.get('order_line_state_reason_code') if line.get('order_line_state_reason_code') else False,
                            'order_line_state_reason_label': line.get('order_line_state_reason_label') if line.get('order_line_state_reason_label') else False,
                            'order_line_index': line.get('order_line_index') if line.get('order_line_index') else False,
                            'price_additional_info': line.get('price_additional_info') if line.get('price_additional_info') else False,
                            'shipping_price': line.get('shipping_price') if line.get('shipping_price') else False,
                            'shipping_price_additional_unit': line.get('shipping_price_additional_unit') if line.get('shipping_price_additional_unit') else False,
                            'shipping_price_unit': line.get('shipping_price_unit') if line.get('shipping_price_unit') else False,
                            'total_commission': line.get('total_commission') if line.get('total_commission') else False,
                        })
                sale_order_lines.append(added_line)
        return sale_order_lines

    def _create_product(self, line):
        product_env = self.env['product.product']

        prod = product_env.search([('name', '=', line.get('SellerProductId'))])
        return prod.id

    def _create_billing_customer(self, billing_address, customer_id):
        billing_customer = self.env['res.partner'].search([('type', '=', 'invoice'), ('parent_id', '=', customer_id)])
        if not billing_customer:
            country = state = full_name = False
            if billing_address['Country'] == "Espagne":
                country = self.env['res.country'].search([('name', '=', 'Spain')])
            else:
                country = self.env['res.country'].search([('code', '=', billing_address['Country'])])
            # if billing_address['state'] != "None":
            #     state = self.env['res.country.state'].search([('name', '=', billing_address['state']), ('country_id', '=', country.id)])
            if billing_address.get('FirstName'):
                full_name = billing_address.get('FirstName')
                if billing_address.get('LastName'):
                    full_name += " "+ billing_address.get('LastName')
            else:
                if billing_address.get('LastName'):
                    full_name = billing_address.get('LastName')
            billing_customer = self.env['res.partner'].create({
                'company_type': 'person',
                'type': 'invoice',
                'name': full_name,
                'parent_id': customer_id,
                'street': billing_address['Street'],
                # 'street2': billing_address['street_2'],
                # 'phone': billing_customer.get("Phone") if billing_customer.get("Phone") != "None" else False,
                'city': billing_address.get("City") if billing_address.get("City") != "None" else False,
                # 'state_id': state.id if state else False,
                'country_id': country.id if country else False,
                'country_code': country.code if country else False,
                'zip': billing_address.get("ZipCode") if billing_address.get("ZipCode") != "None" else False,
            })
        return billing_customer.id



    def _create_shipping_customer(self, shipping_address, customer_id):
        shipping_customer = self.env['res.partner'].search([('type', '=', 'delivery'), ('phone', '=', shipping_address.get("phone"))],limit=1)
        if not shipping_customer:
            country = state = full_name = False
            if shipping_address['country'] == "Espagne":
                country = self.env['res.country'].search([('name', '=', 'Spain')])
            else:
                country = self.env['res.country'].search([('name', '=', shipping_address['Country'])])
            # if shipping_address['state'] != "None":
            #     state = self.env['res.country.state'].search([('name', '=', shipping_address['state']), ('country_id', '=', country.id)])
            if shipping_address.get('FirstName'):
                full_name = shipping_address.get('FirstName')
                if shipping_address.get('LastName'):
                    full_name += " "+ shipping_address.get('LastName')
            else:
                if shipping_address.get('LastName'):
                    full_name = shipping_address.get('LastName')
            
            shipping_customer = self.env['res.partner'].create({
                'company_type': 'person',
                'type': 'delivery',
                'name': full_name,
                'parent_id': customer_id,
                'street': shipping_address['Street'],
                # 'street2': shipping_address['street_2'],
                # 'phone': shipping_address.get("phone"),
                'city': shipping_address['City'],
                # 'state_id': state.id if state else False,
                'country_id': country.id if country else False,
                'country_code': country.code if country else False,
                'zip': shipping_address['ZipCode'],
            })
        return shipping_customer.id

    def _create_customer(self, order):
        customer_data = order.get('Customer')
        if customer_data:
            customer_env = self.env['res.partner']
            customer = customer_env.search([('cdiscount_customer_id', '=', customer_data.get("CustomerId"))])
            if not customer:
                customer = customer_env.create({
                    'company_type': 'person',
                    'name': customer_data.get('FirstName') + ' ' + customer_data.get('LastName'),
                    'phone': customer_data.get("MobilePhone"),
                    'email': customer_data.get('Email'),
                    'cdiscount_customer_id': customer_data.get("CustomerId"),
                    # 'mirakl_locale': customer_data.get("locale"),
                })
            return customer.id
        return False

    
    def get_token(self):
        url = "https://sts.cdiscount.com/users/httpIssue.svc/?realm=https://wsvc.cdiscount.com/MarketplaceAPIService.svc"
        if not self.api_login or not self.api_password:
            raise UserError(_("Please Enter login ID and password for API"))
        else:
            response = requests.get(url, auth=(self.api_login, self.api_password))
        data = xmltodict.parse(response.text)
        self.write({'seller_token': data['string']['#text']})
        print(data)


    def action_view_cdiscount_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("%s's Manomano Orders", self.name),
            'view_mode': 'list,form',
            'res_model': 'manomano.orders',
            
            'context': {
                'search_default_group_status': 1,
                'search_default_today': 1,
                'warehouse_id': self.warehouse_id.id,
                'shop_id': self.id
            },
            'domain': [('shop_id','=',self.id)]
        }

    def action_view_sale_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Sales Orders Generated from ManoMano"),
            'view_mode': 'list,form',
            'res_model': 'sale.order',
            'context': {
                'search_default_groub_by_date': 1,
            },
            'domain': [('manomano_order_id', '!=', False),('market_place_shop','=',self.name)],
        }




            
                
            
