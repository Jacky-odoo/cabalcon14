# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    serie = fields.Char(string='Serie del Comprobante', size=10, help="Será usado como información para actualizar la serie de la factura del cliente.")
    journal_tipocomprobante_id = fields.Many2one('einvoice.catalog.01', string='Tipo de Comprobante')
    eselectronica = fields.Boolean(string='Es Electrónica?', help="Determina si el comprobante se generará de manera electrónica o manual")
    journal_tipolibro = fields.Selection([
            ('01', '01 - LIBRO DE CAJA Y BANCOS'),
            ('02', '02 - REGISTRO DE ACTIVOS FIJOS'),
            ('03', '03 - REGISTRO DE VENTAS E INGRESOS'),
            ('04', '04 - REGISTRO DE COMPRAS'),
            ('05', '05 - REGISTRO DE CONSIGNACIONES'),
            ('06', '06 - REGISTRO DE INVENTARIO PERMANENTE EN UNIDADES FISICAS'),
            ('07', '07 - REGISTRO DE INVENTARIO PERMANENTE VALORIZADO'),
            ('08', '08 - REGISTRO DEL REGIMEN DE PERCEPCIONES'),
            ('09', '09 - REGISTRO DEL REGIMEN DE RETENCIONES'),
            ('10', '10 - REGISTRO DE RETENCIONES DEL IMPUESTO A LA RENTA'),
            ('11', '11 - REGISTRO DE PLANILLA'),
            ('12', '12 - REGISTRO DE RECIBOS POR HONORARIOS'),
            ], string='Tipo de Libro/Registro',
            help="Será usado como guía en la impresión de los libros contables, también para las Percepciones y Retenciones ...")
    sequence_tipolibro_id = fields.Many2one('ir.sequence', string='Secuencial Libro/Regristro Contable', copy=False,
        help="Secuencial de los Libros y Registros Contables.")
    esctadetracciones = fields.Boolean('Es Cuenta Detraccion?', help="Determina si el diario de pago bancario es de Detracciones")
    esnotacredito = fields.Boolean('Es Nota de Crédito?', help="Determina si el diario se comportará como Nota de Crédito")
    esnotadebito = fields.Boolean('Es Nota de Débito?', help="Determina si el diario se comportará como Nota de Débito")

    
class AccountTax(models.Model):
    _inherit = 'account.tax'
    
    type_tax_sunat = fields.Selection(
            [('10','10 - IGV'),
            ('20','20 - ISC'),
            ('30','30 - IMP'),
            ('40','40 - OTROS'),
            ('50', '50 - DETRACCION'),
            ('60', '60 - PERCEPCION'),
            ('100','100 - RENTA 1ra'),
            ('110','110 - RENTA 2da'),
            ('120','120 - RENTA 3ra'),
            ('130','130 - RENTA 4ta'),
            ('140','140 - RENTA 5ta')], string='Aplicación SUNAT',
            help="Utilizado para identificar el Impuesto según la SUNAT. Al crear move_line se asignará el tipo de impuesto para facilitar el calculo del total de impuestos del Asiento Contable")
    tax_sunat = fields.Many2one('einvoice.catalog.05', string='Tipo de Tributo') #Utilizado en Facturación Electrónica
    tax_sunat_effect = fields.Many2one('einvoice.catalog.07', string='Tipo de Afectación') #Utilizado en Facturación Electrónica