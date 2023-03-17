from odoo import fields,api,models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    manomano_order_id = fields.Char("ManoMano Order ID")
    # amazon_order = fields.Many2one("manomano.orders","Amazon Order")
    first_name = fields.Char("First Name")
    last_name = fields.Char("Last Name")
    order_status = fields.Char('Order Status')
    shipping_method = fields.Char("Ship Method")
    # date_order = fields.Datetime("Order Date")
    shipping_address = fields.Char("Ship To Address Line 1")
    shipping_zip = fields.Char("Ship To ZIP Code")
    delivery_city = fields.Char("Ship To City")
    delivery_country = fields.Char("Ship To Country or Region")
    product_id = fields.Many2one("product.product","Product")
    full_name = fields.Char("Ship To Name")
    # product_status = fields.Char("Product Status")
    # product_ref = fields.Char("Vendor Reference")
    quantity = fields.Char("Item Quantity")
    total_price = fields.Char("Item Cost")
    delivery_cost = fields.Char("Amount Delivery costs (€ incl. VAT)")
    phone = fields.Char('Phone Number')
    line_id = fields.Char('Line ID')
    billing_zip = fields.Char("Billing postcode")
    billing_city = fields.Char("Billing city")
    billing_country = fields.Char("Billing country")
    order_id = fields.Many2one('sale.order',"Sale Order")
    sku = fields.Char('SKU')
    warehouse = fields.Char('Warehouse Code')


    #sale manomano fields
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
    
    total_price_amount = fields.Float(" Price Amount")
    total_price_currency = fields.Char("Price Currency")
    total_price_vat_amount= fields.Float("Vat Amount")
    total_price_vat_currency=  fields.Char(" Vat Currency")
    shipping_price_vat_rate = fields.Float("Shipping Price")

    products_price_amount = fields.Float("Shipping Price")
    products_price_currency = fields.Char(" Vat Currency")
    products_price_excluding_vat_amount =fields.Float("Product Amount")
    products_price_excluding_vat_currency = fields.Char("Product Currency")

    products_price_vat_amount = fields.Float("Product  vat amount")
    products_price_vat_currency = fields.Char("Product vat currency")
    manomano_discount_amount = fields.Float("Discount amount")
    seller_discount_currency = fields.Char()
    seller_contract_id = fields.Char("Seller Id")
    order_reference = fields.Char("Order Refrence")
    shipping_discount_amount = fields.Float("Order Refrence")
    shipping_discount_currency = fields.Char("Discount Currency")
    
    created_at = fields.Datetime("Created at")
    status_updated_at = fields.Datetime("Created at")
    total_discount = fields.Float("Total Discount")
    customer_firstname = fields.Char("First name")
    customer_lastname = fields.Char("Last name")
    is_mmf = fields.Char("")
    is_professional = fields.Char("")
    billing_fiscal_number = fields.Char("")
   # products = 
    #vat_rate =
    #shipping_vat_rate =
    #carrier =
    # seller_sku =
    # price =
    # price_excluding_vat =
    # title =
    # shipping_price =
    # sum_shipping_price = 
    # shipping_price_excluding_vat =
    # product_price =
    # product_price_excluding_vat = 
    # total_price = 
    # total_price_excluding_vat =
    # product_title =
    


    #addresses
    #shipping
    # phone = 
    # email =
    # firstname = 
    # lastname = 
    # company = 
    # address_line1 = 
    # city = 
    # zipcode = 
    # country = 
    # country_iso = 
            


    





    #new fields
    order_date = fields.Char("Order Place Date")
    req_ship_date = fields.Char("Required Ship Date")
    ship_method_code = fields.Char("Ship Method Code")
    shipping_address2 = fields.Char("Ship To Address Line 2")
    shipping_address3 = fields.Char("Ship To Address Line 3")
    shipping_state = fields.Char("Ship To State")
    is_gift = fields.Char("Is it Gift?")
    asin = fields.Char("ASIN")
    carrier = fields.Char("carrier")
    gift_meesage = fields.Char("Gift Message")
    tracking_id = fields.Char("Tracking ID")
    ship_date = fields.Char("Shipped Date")
    payment_ref = fields.Char("Payment Ref")
    email = fields.Char("email")

    def export_warehouse_orders(self):

        shipping_sale_orders = []
        for order in self:
            if order.mirakl_order_state and order.mirakl_order_state == "shipping" and order.manomano_order_id:
                shipping_sale_orders.append(order)
        if len(shipping_sale_orders) > 0:
            self.env['shop.integrator'].separate_warehouse_orders(shipping_sale_orders)
        return super(SaleOrder, self).export_warehouse_orders()

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    line_id = fields.Char("Line Id")
