from odoo import models,api,fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    manomano_customer_id = fields.Char("Manomano Customer Id")
    company= fields.Char("company")