# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class Partner(models.Model):
    _inherit = "res.partner"

    is_gruped = fields.Boolean('Agrupar línea de factura por producto y precio?', copy=False)
