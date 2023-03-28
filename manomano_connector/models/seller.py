from dataclasses import field
from odoo import fields,api, models,_
import requests
import pytz
import datetime
from odoo.exceptions import UserError, ValidationError, MissingError
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
    geting_url = fields.Char("Seller URL", required = True) 
    activate = fields.Boolean("Activate")

    #order management field
    seller_contract_id = fields.Integer("Seller Id",required = True)
    order_reference = fields.Char("Order Refrence")

    manomano_status = fields.Selection([
        ('PENDING','Pending'),
        ('WAITING_PAYMENT','Waiting Period'),
        ('REFUSED','Refused'),
        ('PREPARATION','Preparation'),
        ('SHIPPED','Shipped'),
        ('REFUNDED','Refunded'),
        ('REFUNDING','Refunding'),
        ('REMORSE_PERIOD','Remorse Period'),
    ])
    
    carrier =fields.Char("Carrier")
    created_at_start = fields.Datetime("Create Date",default=fields.Datetime.now())
    created_at_end = fields.Date("End Date")
    status_updated_at_start = fields.Date("Status Start")
    status_updated_at_end = fields.Date("Status End")
    limit = fields.Integer("Limit", default="50")
    page = fields.Integer("Page")
    is_filter_activate = fields.Boolean("Activate Filters")
   
   #Method to convert Odoo date format to Manomanao date format.......
    def get_manomano_date_format(self, odoo_date_format):
        if odoo_date_format:
            date_time_string = fields.Datetime.to_string(odoo_date_format).replace(" ", "T")+ 'Z'
        else:
            date_time_string = False
        return date_time_string
    
    #method getting odoo date_time_format
    def get_odoo_date_format(self, manomano_date_format):
        if manomano_date_format:
            date_time_string = manomano_date_format.replace("T", " ")[0:manomano_date_format.find(":")+5] if manomano_date_format else False
        else:
            date_time_string = False
        return date_time_string

    # API Methods
    #############

    # Get Orders
    ############
    def get_all_orders(self):
        call = self.geting_url+"/orders/v1/orders"
        # Add Seller Id 
        if self.seller_contract_id:
            call += "?seller_contract_id=" + str(self.seller_contract_id)
            
            # filters
            if self.is_filter_activate:
                if self.limit:
                    call += "&limit=" + str(self.limit)
                if self.manomano_status:
                    call += "&status=" + self.manomano_status 
                if self.carrier:
                    call+= "&carrier=" + self.carrier

            if self.created_at_start:
                call += '&created_at_start='+ self.get_manomano_date_format(self.created_at_start)
                _logger.info("-----------------------------created at start____%r",call)
            
            # Pagingation 
            page = 0
            while(True):
                if "&page=" in call:
                    to_remove = "&page="+page
                    call.pop()
                page += 1
                call += "&page="
                call += str(page)
                _logger.info("_CAll ............... %r .......",call)
                response = self.get_new_order(call)
                if not response:
                    break
        
    
    def get_new_order(self,call):

        #Getting data
        try:
            response = requests.get(call,headers={'x-api-key': self.api_key,'Accept':'application/json'}).json()
        except Exception as err:
             _logger.info("!!!!!     NO new record Error~~~~~~~~%r ;;;;;",err)
             return False
        
        if not response.get("content"):
            return False
        else:
            _logger.info(" GEt all orders^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^   %r  ;;;;;", response.get("content"))
            for order in response.get("content"):
                self.create_sale_order_api(order)
            return True

    



    def get_product_api(self, line):
        product_env = self.env['product.product']
        prod = product_env.search([('default_code', '=', line.get("seller_sku"))])
        if len(prod) <= 0:
            prod = product_env.search([('barcode', '=', line.get('seller_sku'))])
        return prod


    def _get_warehouse(self):
        warehouse = self.warehouse_id
        if not warehouse:
            raise MissingError(_('Please assign a Warehouse to this shop first - (Shop: )'))
        else:
            return warehouse.id

    
    # Create SO API
    ###############
    def create_sale_order_api(self, order):

        sale_order_id = self.env['sale.order'].search([('manomano_order_id', '=', order.get('order_reference'))], limit=1)
        
        if  sale_order_id:
            _logger.info("~~Order Update~~~~~~~~~%r~~~~~~~~~~", sale_order_id)
            #Update ORder 
            return sale_order_id
        else:
            # Create Sale Order
            sale_order_id = False
            try:
                customer_id = self._create_customer_api(order)
               
                _logger.info("Customer Created .........   %r  .........",customer_id)
            except Exception as e:
                _logger.info("Customer creation error~~~~~~~   %r     %r;;;;;",order.get('customer'),e)
                customer_id = False
            if customer_id:
                try:
                    billing_id = self._create_billing_customer_api(order.get('addresses').get("billing"), customer_id)
                    _logger.info("Billing Customer Created --------------    %r    ---------",billing_id)  
                except Exception as e:
                    _logger.info("Billing creation error~~~~~~~   %r     %r;;;;;",order.get('addresses').get("billing"), e)
                    billing_id = False
                try:
                    shipping_id = self._create_shipping_customer_api(order.get('addresses').get("shipping"), customer_id)
                    _logger.info("Shipping Customer Created --------------    %r    ---------",shipping_id)  
                except Exception as e:
                    _logger.info("Shipping creation error~~~~~~   %r    %r    ;;;;", order.get('addresses').get("shipping"), e)
                    shipping_id = False

        #ASSIGNING WAREHOUSE            
        warehouse_id = False
        try:
            warehouse_id = self._get_warehouse()
            _logger.info("Warehouse created ---------------------            ;;;;;")

        except:
            _logger.info("Warehouse not assigned error in the shop ;;;;;")
            warehouse_id = False

        # Create Order Lines
        try:
            order_line = self.get_sale_order_lines_api(order.get('products'))
            _logger.info(" Create Order Lines ___________________________--------------------;;;;;")


        except:
            _logger.info("Order Line creation error ;;;;;")
            order_line = False

        # Order Status
        odoo_state = None
        if order.get("status"):
            if order.get("status") == 'SHIPPED':
                mirakl_state = 'shipped'
                odoo_state = 'sale'
            elif order.get("status") == 'PENDING':
                mirakl_state = 'waiting_acceptance'
                odoo_state = 'draft'
            elif order.get("status") == 'REFUNDED':
                mirakl_state = 'canceled'
                odoo_state = 'cancel'
            elif order.get("status") == 'REFUSED':
                mirakl_state = 'refused'
                odoo_state = 'cancel'
            elif order.get("status") == 'PREPARATION':
                odoo_state = 'sale'
                mirakl_state = 'shipping'
            else:
                mirakl_state = 'closed'
                odoo_state = 'sale'


        _logger.info("~~~~~~test    ~~~~~~~~~~%r~~~~%r~~~~%r~~~~~~~%r`~~~~~~`%r~~~~~", customer_id, shipping_id, billing_id, order_line, warehouse_id)
        # Create Order
        if customer_id and billing_id and shipping_id and warehouse_id and order_line:
            try:
                sale_order = self.env['sale.order'].create({
                    'partner_id': customer_id,
                    'partner_invoice_id': billing_id,
                    'partner_shipping_id': shipping_id,
                    'manomano_shop_id': self.id,
                    'market_place_shop': self.name,
                    'warehouse_id': warehouse_id,
                    'order_line': order_line,
                    'manomano_order_id': order.get("order_reference"),
                   
                    'status': order.get("status") if order.get("status") else False,
                    'created_at_start':self.get_odoo_date_format(order.get('created_at')) if self.get_odoo_date_format(order.get('created_at')) else False,
                    # 'status_updated_at':,
                    'state': odoo_state,
                    'total_price_amount':order.get("total_price").get("amount") if order.get("total_price").get("amount") else  False,
                    'total_price_currency':order.get("total_price").get("currency") if order.get("total_price").get("currency") else  False,
                    'total_price_vat_amount':order.get("total_price_vat").get("amount") if order.get("total_price").get("amount") else  False,
                    'total_price_vat_currency':order.get("total_price").get("currency") if order.get("total_price").get("currency") else  False,
                    'shipping_price_vat_rate':order.get("shipping_price_vat_rate") if order.get("shipping_price_vat_rate") else False,
                    'products_price_amount':order.get("products_price").get("amount") if order.get("products_price").get("amount")  else  False,
                    'products_price_currency':order.get("products_price").get("currency") if order.get("products_price").get("currency") else  False,
                    'products_price_excluding_vat_amount':order.get("products_price_excluding_vat").get("amount") if order.get("products_price_excluding_vat").get("amount") else  False,
                    'products_price_excluding_vat_currency':order.get("products_price_excluding_vat").get("currency") if order.get("products_price_excluding_vat").get("currency") else  False,
                    'products_price_vat_amount':order.get("products_price_vat").get("amount") if order.get("products_price_vat").get("amount") else  False,
                      'products_price_vat_currency':order.get("products_price_vat").get("currency") if order.get("products_price_vat").get("currency") else  False,
                      'manomano_discount_amount':order.get("manomano_discount").get("amount") if order.get("manomano_discount").get("amount") else  False,
                      'manomano_discount_currency':order.get("manomano_discount").get("currency") if order.get("manomano_discount").get("currency") else  False,
                      'order_reference':order.get("order_reference") if order.get("order_reference") else  False,
                      'shipping_discount_amount':order.get("shipping_discount").get("amount") if order.get("shipping_discount").get("amount") else  False,
                      'shipping_discount_currency':order.get("shipping_discount").get("currency") if order.get("shipping_discount").get("currency") else  False,
                     # 'total_discount':order.get("total_discount") if order.get("total_discount") else  False,
                      'customer_firstname':order.get("customer").get("firstname") if order.get("customer").get("firstname") else  False,
                      'customer_lastname':order.get("customer").get("lastname") if order.get("customer").get("lastname")  else  False,
                      'is_mmf':order.get("is_mmf") if order.get("is_mmf") else  False,
                      'is_professional':order.get("is_professional") if order.get("is_professional") else  False,
                      'billing_fiscal_number':order.get("billing_fiscal_number") if order.get("billing_fiscal_number") else  False,


                })
                _logger.info("Sale Order Created~~~~~~%r ;;;;;", sale_order)
            except Exception as err:
                _logger.info("Sale Order Creation Error~~~~~~~%r ;;;;;",err)


    # Create Customer
    def _create_customer_api(self, order):

        customer_data = order.get('customer')
        if customer_data:

            customer_env = self.env['res.partner']
            customer = customer_env.search([('manomano_customer_id', '=', (customer_data.get('firstname') + ' ' + customer_data.get('lastname')))], limit=1)
           
            if not customer:
                customer = customer_env.create({
                   'company_type': 'person',
                    'name': customer_data.get('firstname') + ' ' + customer_data.get('lastname'),
                    'phone': order.get('addresses').get('billing').get("phone") if customer_data.get('billing_address') else False,
                    'email': order.get('addresses').get('billing').get('email'),
                    'manomano_customer_id': customer_data.get('firstname') + ' ' + customer_data.get('lastname'),
                })
            _logger.info("---------create customer---------------------------%r          -----", customer.id)
            return customer.id
       
           
        
        return False
    

    # create billing address
    def _create_billing_customer_api(self, billing_addresses, customer_id):
        billing_customer = self.env['res.partner'].search([('type', '=', 'invoice'), ('parent_id', '=', customer_id)], limit=1)
        if not billing_customer:
            _logger.info("Billing Customer Created ------1--------    %r    ---------",billing_addresses)  

            country = state = full_name = False
            if billing_addresses.get("country"):
                country = self.env['res.country'].search([('name', '=', billing_addresses.get("country"))])  
            if len(country) <= 0 and billing_addresses.get("country_iso"):
                country = self.env['res.country'].search([('code', '=', billing_addresses.get("country_iso"))])
            if billing_addresses.get('firstname'):
                full_name = billing_addresses.get('firstname')
                if billing_addresses.get('lastname'):
                    full_name += " "+ billing_addresses.get('lastname')
            else:
                if billing_addresses.get('lastname'):
                    full_name = billing_addresses.get('lastname')
            _logger.info("Billing Customer Created -------2-------    %r    ---------",billing_addresses)  
              
            billing_customer = self.env['res.partner'].create({
                'company_type': 'person',
                'type': 'invoice',
                'name': full_name,
                'parent_id': customer_id,
                'phone': billing_addresses.get("phone") if billing_addresses.get("phone") else False,
                'city': billing_addresses.get("city") if billing_addresses.get("city") else False,
                'street':billing_addresses.get("address_line1"),
                'country_id': country.id if country else False,
                'zip': billing_addresses.get("zipcode") if billing_addresses.get("zipcode") else False,
            })
        return billing_customer.id
    
    # create shipping address
    def _create_shipping_customer_api(self, shipping_address, customer_id):
        shipping_customer = self.env['res.partner'].search([('type', '=', 'delivery'), ('parent_id', '=', customer_id)], limit=1)
        if not shipping_customer:
            country = state = full_name = False
            if shipping_address['country']:
                country = self.env['res.country'].search([('name', '=', shipping_address['country'])])
            if len(country) <= 0:
                country = self.env['res.country'].search([('code', '=', shipping_address['country_iso_code'])])
            if shipping_address.get('firstname'):
                full_name = shipping_address.get('firstname')
                if shipping_address.get('lastname'):
                    full_name += " "+ shipping_address.get('lastname')
            else:
                if shipping_address.get('lastname'):
                    full_name = shipping_address.get('lastname')
            
            shipping_customer = self.env['res.partner'].create({
                'company_type': 'person',
                'type': 'delivery',
                'name': full_name,
                'parent_id': customer_id,
                'street': shipping_address['address_line1'],
                'phone': shipping_address["phone"],
                'city': shipping_address['city'],
                'country_id': country.id if country else False,
                'zip': shipping_address['zipcode'],
            })
        return shipping_customer.id
    
    # get order lines
    def get_sale_order_lines_api(self, products):
        sale_order_lines = []   
        added_line = False
        for line in products:
            try:
                product_id = self.get_product_api(line)
                _logger.info("~~~~~~~~~~~%r~~~~~~~~~", product_id)
                if len(product_id) > 0:
                    added_line = (0, 0, {
                        'product_id': product_id.id,
                        'name':line.get('title') if line.get('title') else False,
                        'price_unit':line.get('price').get("amount") if line.get('price') else False,
                        'offer_sku': line.get('seller_sku') if line.get('seller_sku') else False,
                        'product_uom_qty':line.get('quantity') if line.get('quantity') else False,
                    })
            except Exception as err:
                _logger.info("Sale Order Line Creation Error~~~~~~~~~~~%r~~~~~~~~~~",err)
            sale_order_lines.append(added_line)
        return sale_order_lines

            

 
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




            
                
            
