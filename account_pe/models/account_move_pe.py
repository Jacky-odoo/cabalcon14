# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.one
    @api.depends('line_ids', 'line_ids.tax_line_id', 'line_ids.balance')
    def _compute_taxes_sunat(self):
        sumigv = sumisc = sumimp = sumotros = 0
        for aml in self.line_ids:
            if aml.tax_line_id:
                if aml.tax_line_id.tax_sunat.code == '1000': #IGV
                    if aml.amount_currency == 0: #Significa que la moneda es igual a la base.
                        sumigv += aml.balance
                    else: #Significa que la moneda es distinta a la base.
                        if aml.amount_currency > 0:
                            sumigv = aml.amount_currency
                        else:
                            sumigv = aml.amount_currency * -1
                elif aml.tax_line_id.tax_sunat.code == '2000': #ISC
                    if aml.amount_currency == 0: #Significa que la moneda es igual a la base.
                        sumisc += aml.balance
                    else: #Significa que la moneda es distinta a la base.
                        if aml.amount_currency > 0:
                            sumisc = aml.amount_currency
                        else:
                            sumisc = aml.amount_currency * -1
                #elif aml.tax_line_id.tax_sunat.code == '1000': #IMP
                #    sumimp += aml.balance
                else: #OTROS
                    if aml.amount_currency == 0: #Significa que la moneda es igual a la base.
                        sumotros += aml.balance
                    else: #Significa que la moneda es distinta a la base.
                        if aml.amount_currency > 0:
                            sumotros = aml.amount_currency
                        else:
                            sumotros = aml.amount_currency * -1
                    
        if sumigv < 0:
            sumigv = sumigv * -1
        if sumisc < 0:
            sumisc = sumisc * -1
        if sumimp < 0:
            sumimp = sumimp * -1
        if sumotros < 0:
            sumotros = sumotros * -1
            
        self.igv = sumigv
        self.isc = sumisc
        self.imp = sumimp
        self.otrostrib = sumotros

    @api.one
    @api.depends('tipo_operacion')
    def _get_tienedetraccion(self):
        tienedetraccion_val = False
        if self.tipo_operacion.code in ['1001','1002','1003','1004']:
            tienedetraccion_val = True
        self.detraccion = tienedetraccion_val

    #Relacion con Factura para armar los related
    invoice_ids = fields.One2many('account.invoice', 'move_id', string='Factura')
    
    account_tipolibro = fields.Selection([
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
            ('12', '12 - REGISTRO DE RECIBOS POR HONORARIOS')],
            string='Tipo de Libro/Registro', related='journal_id.journal_tipolibro', readonly=True, store=True,
            help="Será usado como guía en la impresión de los libros contables, también para las Percepciones y Retenciones ...")
    sec_journal_libro = fields.Char('Secuencia Libro/Registro', copy=False, help='Secuencia del Libro Contable')
    
    tipo_operacion = fields.Many2one('einvoice.catalog.51', string='Tipo de Operación')
    tipocomprobante_id = fields.Many2one('einvoice.catalog.01', string='Tipo de Comprobante', related='journal_id.journal_tipocomprobante_id', readonly=True, store=True,)
    estadocomprobante = fields.Selection([
            ('0', 'EMITIDO'),
            ('1', 'ANULADO')], 
        string='Estado Comprobante', states={'posted':[('readonly',True)]},
        help="Referencia del estado de la Factura de Venta")
    
    serie = fields.Char(string='Serie', size=10, states={'posted':[('readonly',True)]})
    correlativo = fields.Char(string='Correlativo', size=15, states={'posted':[('readonly',True)]})
    feccomprobante = fields.Date(string='Fecha Comprobante', states={'posted':[('readonly',True)]},
        help="Fecha del Comprobante del Cliente o Proveedor, usado para el Registro de Ventas y Compras y en el Libro de Caja y Bancos") 
        
    fecvencimiento = fields.Date(string='Fecha Vencimiento', states={'posted':[('readonly',True)]})

    doc_tipo = fields.Many2one('einvoice.catalog.06','Tipo Documento', readonly=True, store=True, related='partner_id.tipo_doc_id')
    doc_numero = fields.Char(string='Nro Documento', size=15, readonly=True, store=True, related='partner_id.vat')
    
    tipocambio = fields.Float('Tipo de Cambio', digits=(2, 7), default=1.0000000, states={'posted':[('readonly',True)]})
    
    baseimponible = fields.Monetary(string='Importe Afecto IGV', states={'posted':[('readonly',True)]})
    baseisc = fields.Monetary(string='Importe Afecto ISC', states={'posted':[('readonly',True)]})
    baseexonerada = fields.Monetary(string='Importe Exonerado', states={'posted':[('readonly',True)]})
    baseinafecta = fields.Monetary(string='Importe Inafecto', states={'posted':[('readonly',True)]})
    importesubtotal = fields.Monetary(string='Subtotal Factura', states={'posted':[('readonly',True)]})
    importetotal = fields.Monetary(string='Total Factura', states={'posted':[('readonly',True)]})
    
    igv =  fields.Monetary(string="IGV", store=True, compute='_compute_taxes_sunat', states={'posted':[('readonly',True)]})
    isc = fields.Monetary(string="ISC", store=True, compute='_compute_taxes_sunat', states={'posted':[('readonly',True)]})
    imp = fields.Monetary(string="IMP", store=True, compute='_compute_taxes_sunat', states={'posted':[('readonly',True)]})
    otrostrib = fields.Monetary(string="Otros Trib.", store=True, compute='_compute_taxes_sunat', states={'posted':[('readonly',True)]})
    totaltrib = fields.Monetary(string='Total Trib.', states={'posted':[('readonly',True)]})
    
    #Atributos a ser usados para el Libro de Caja y Bancos
    banco = fields.Char(string='Banco', size=10)
    codcta = fields.Char(string='Codigo de Cta.Corr.', size=10)
    mediodepago = fields.Char(string='Medio de Pago', size=10)
    numsustento = fields.Char(string='Num.Sustento', size=10)
    account_code = fields.Char(string='Cod.Cta.Cont.', size=10)
    account_name = fields.Char(string='Nom.Cta.Cont', size=10)
    deudor = fields.Char(string='Deudor', size=10)
    acreedor = fields.Char(string='Acreedor', size=10)
    
    #Falta Migrar
    #'bank_ids': fields.many2one('res.partner.bank', 'Cuenta Bancaria',
    #    ondelete='cascade', select=True),
    
    det_code = fields.Many2one('einvoice.catalog.54', string='Código Detracción', help='Catálogo 54 de Sunat')
    detraccion = fields.Boolean(string='Sujeto a Detracción?', compute='_get_tienedetraccion', store=True, copy=False)
    detraccion_id = fields.Many2one('account.tax', string='Porcentaje')
    det_fecpago = fields.Date('Fecha Pago Pago Det.')
    det_nropago = fields.Char('Número Pago Det.', size=15, help="Para registrar el Nro. de Comprobante de Pago de Detracción")



