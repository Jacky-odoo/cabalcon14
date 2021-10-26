# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

# mapping invoice type to journal type + Refunds
TYPE2JOURNAL2 = {
    'out_invoice': False,
    'in_invoice': False,
    'out_refund': True,
    'in_refund': True,
}

# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Vendor Bill
    'out_refund': 'out_invoice',        # Customer Credit Note
    'in_refund': 'in_invoice',          # Vendor Credit Note
}




#Lineas de Factura agrupadas por producto, precio
class AccountInvoiceLineGroup(models.Model):
    _name = "account.invoice.line.group"
    _description = "Invoice Line Group"
    _order = "invoice_id,name,id"

    invoice_id = fields.Many2one('account.invoice', string='Factura', ondelete='cascade', index=True)
    #sequence = fields.Integer('Secuencia', default=10, help="Gives the sequence of this line when displaying the invoice.")
    product_id = fields.Many2one('product.product', string='Producto', ondelete='restrict', index=True)
    name = fields.Text(string='Descripción', required=True)
    quantity = fields.Float(string='Cant.', digits=dp.get_precision('Product Unit of Measure'), default=1)
    uom_id = fields.Many2one('product.uom', string='Unidad', ondelete='set null', index=True, oldname='uos_id')
    price_unit = fields.Float(string='P.U.')
    invoice_line_tax_ids = fields.Many2many('account.tax', 'account_invoice_line_tax_group', 'invoice_line_id', 'tax_id',
        ondelete='cascade', string='Impuestos', domain=[('type_tax_use','!=','none'), '|', ('active', '=', False), ('active', '=', True)], oldname='invoice_line_tax_id')
    price_subtotal = fields.Float(string='Sub total')
    price_total = fields.Float(string='Total')
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', store=True, related_sudo=False)
    company_currency_id = fields.Many2one('res.currency', related='invoice_id.company_currency_id', readonly=True, related_sudo=False)


class account_invoice_line2(models.Model):
    _name = "account.invoice.line2"
    _description = "Alternative Invoice Line"
    _order = "invoice_id,sequence,id"

    sequence = fields.Integer('Secuencia')
    name = fields.Text('Descripción', required=True)
    invoice_id = fields.Many2one('account.invoice', 'Factura', ondelete='cascade')
    price_unit = fields.Float('Importe', required=True)

class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    _order = "date desc, sec_journal_libro desc, id desc"
    
    @api.one
    @api.depends('number', 'seriec', 'journal_id')
    def _get_serie(self):
        #No siempre se usará facturación electrónica por lo que éste método debe ser ampliado en esa clase
        #La idea es que: Trae el valor de la electrónica si lo es y sino del secuencial de la factura
        serie_val = ''
        if self.type == 'out_invoice' or self.type == 'out_refund':
            serie_val = self.journal_id.serie
        elif self.type == 'in_invoice' or self.type == 'in_refund':
            serie_val = self.seriec
        self.serie = serie_val
    
    @api.one
    @api.depends('number', 'correlativoc')
    def _get_correlativo(self):
        #No siempre se usará facturación electrónica por lo que éste método debe ser ampliado en esa clase
        #La idea es que: Trae el valor de la electrónica si lo es y sino del secuencial de la factura
        corr_val = ''
        if (self.type == 'out_invoice' or self.type == 'out_refund') and not self.eselectronica: #VENTA O NC NO ELECTRONICA
            number_val = self.number
            if number_val:
                corr_val = number_val.replace(self.journal_id.sequence_id.prefix,'') #Extrae el prefijo del string
        elif self.type == 'in_invoice' or self.type == 'in_refund': #COMPRA O NC NO ELECTRONICA
            corr_val = self.correlativoc
        self.correlativo = corr_val
    
    @api.one
    @api.depends('serie', 'correlativo')
    def _get_numdocproveedor(self):
        reference_val = ''
        if self.type == 'in_invoice' or self.type == 'in_refund': #COMPRA O NC DE PROVEEDOR
            if self.serie and self.correlativo:
                reference_val = self.serie + '-' + self.correlativo
            elif self.serie:
                reference_val = self.serie
            elif self.correlativo:
                reference_val = self.correlativo
        self.reference = reference_val
    
    @api.one
    @api.depends('invoice_line_ids2', 'invoice_line_ids2.price_unit')
    def _compute_amount2(self):
        subtotal2_val = 0
        if self.invoice_line_ids2:
            for ail2 in self.invoice_line_ids2:
                subtotal2_val += ail2.price_unit
        self.subtotal2 = subtotal2_val
    
    @api.one
    @api.depends('amount_total')
    def _get_amount_in_words(self):
        amount_in_words = self.currency_id.amount_to_text(self.amount_total)
        self.amount_in_text = amount_in_words
    
    #Lo traigo para modificar el domain y que Odoo seleccione correctamente el libro
    @api.model
    def _default_journal(self):
        domain = []
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        esnotacredito = self._context.get('esnotacredito', False)
        esnotadebito = self._context.get('esnotadebito', False)
        if inv_type == 'out_refund': #NC CLIENTE
            domain = [('type','=', 'sale'),('esnotacredito','=',True),('esnotadebito','=',False),('company_id', '=', company_id)]
        elif inv_type == 'in_refund': #NC PROVEEDOR
            domain = [('type','=', 'purchase'),('esnotacredito','=',True),('company_id', '=', company_id)]
        elif inv_type == 'out_invoice' and not esnotacredito and not esnotadebito: #FACTURA CLIENTE
            domain = [('type','=', 'sale'),('esnotacredito','=',False),('esnotadebito','=',False),('company_id', '=', company_id)]
        elif inv_type == ' in_invoice': #FACTURA PROVEEDOR
            domain = [('type','=', 'purchase'),('esnotacredito','=',False),('esnotadebito','=',False),('company_id', '=', company_id)]
        elif inv_type == 'out_invoice' and not esnotacredito and esnotadebito: #ND CLIENTE
            domain = [('type','=', 'sale'),('esnotacredito','=',False),('esnotadebito','=',True),('company_id', '=', company_id)]
        elif inv_type == 'in_invoice' and not esnotacredito and esnotadebito: #ND PROVEEDOR
            domain = [('type','=', 'purchase'),('esnotacredito','=',False),('esnotadebito','=',True),('company_id', '=', company_id)]
        return self.env['account.journal'].search(domain, limit=1)
    
    @api.model
    def _get_journal_domain(self):
        domain_val = None
        ctx = self.env.context
        #print (ctx)
        esnc_val = ctx.get('esnotacredito')
        esnd_val = ctx.get('esnotadebito')
        type_val = ctx.get('type')
        #print (esnc_val)
        #print (esnd_val)
        
        if type_val == 'out_invoice' and not esnc_val and not esnd_val: #Factura de Cliente
            domain_val = "[('type','=', 'sale'),('esnotacredito','=',False),('esnotadebito','=',False),('company_id', '=', company_id)]"
        elif type_val == 'out_refund': #Nota de Crédito Cliente
            domain_val = "[('type','=', 'sale'),('esnotacredito','=',True),('company_id', '=', company_id)]"
        elif type_val == 'out_invoice' and esnd_val: #Nota Debito Cliente
            domain_val = "[('type','=', 'sale'),('esnotadebito','=',True),('company_id', '=', company_id)]"
        elif type_val == 'in_invoice' and not esnc_val and not esnd_val: #Factura de Proveedor
            domain_val = "[('type','=', 'purchase'),('esnotacredito','=',False),('esnotadebito','=',False),('company_id', '=', company_id)]"
        elif type_val == 'in_refund': #Nota de Crédito Proveedor
            domain_val = "[('type','=', 'purchase'),('esnotacredito','=',True),('company_id', '=', company_id)]"
        elif type_val == 'in_invoice' and esnd_val: #Nota Debito Proveedor
            domain_val = "[('type','=', 'purchase'),('esnotadebito','=',True),('company_id', '=', company_id)]"
        return domain_val
    
    #@api.one
    #@api.depends('tipo_operacion')
    #def _get_tienedetraccion(self):
    #    tienedetraccion_val = False
    #    if self.tipo_operacion.code in ['1001','1002','1003','1004']:
    #        tienedetraccion_val = True
    #    self.tienedetraccion = tienedetraccion_val
    
    #Nombre a mostrar de la factura
    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Credit Note'),
            'in_refund': _('Vendor Credit note'),
        }
        result = []
        for inv in self:
            if inv.type in ['out_invoice', 'out_refund']: #Salientes
                result.append((inv.id, "%s" % (inv.number)))
            else:
                result.append((inv.id, "%s" % (inv.reference)))
        return result
    
    #Lo traigo para modificar el domain y que Odoo muestre los libros correctos
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain=_get_journal_domain)
        #domain="[('esnotacredito', '=', {'out_invoice': False, 'out_refund': True, 'in_invoice': False, 'in_refund': True}.get(type, [])), ('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")
        #domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")
    
    journal_tipocomprobante_id = fields.Many2one('einvoice.catalog.01', related='journal_id.journal_tipocomprobante_id', 
        string='Tipo de Comprobante', readonly=True, required=False, store=True)
    eselectronica = fields.Boolean(string='Es Electrónica?', related='journal_id.eselectronica', readonly=True, store=True)
    journal_libro = fields.Selection([
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
        ('12', '12 - REGISTRO DE RECBOS POR HONORARIOS'),
        ], string='Tipo de Libro/Registro', related='journal_id.journal_tipolibro', readonly=True, required=False, store=True,
        help="Será usado como guía en la impresión de los libros contables, también para las Percepciones y Retenciones ...")
    sec_journal_libro = fields.Char('Secuencia Libro/Registro', copy=False, help='Secuencia del Libro Contable')
    type_nc = fields.Many2one('einvoice.catalog.09', string='Tipo Nota Crédito', copy=False, help='Catálogo 09 de Sunat')
    esnotacredito = fields.Boolean('Es Nota de Crédito?', related='journal_id.esnotacredito', readonly=True, store=True, help="Determina si se comportará como Nota de Crédito")
    type_nd = fields.Many2one('einvoice.catalog.10', string='Tipo Nota Débito', copy=False, help='Catálogo 10 de Sunat')
    esnotadebito = fields.Boolean('Es Nota de Débito?', related='journal_id.esnotadebito', readonly=True, store=True, help="Determina si se comportará como Nota de Débito")
    
    serie = fields.Char(string='Serie', size=10, compute='_get_serie', store=True, copy=False)
    correlativo = fields.Char(string='Correlativo', size=15, compute='_get_correlativo', store=True, copy=False)
    seriec = fields.Char(string='Serie', size=10, readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    correlativoc = fields.Char(string='Correlativo', size=15, readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    reference = fields.Char(string='Vendor Reference', compute='_get_numdocproveedor', store=True, copy=False, help="The partner reference of this invoice.")
    
    det_code = fields.Many2one('einvoice.catalog.54', string='Código Detracción', copy=False, help='Catálogo 54 de Sunat')
    tienedetraccion = fields.Boolean(string='Sujeto a Detracción?', default=True, copy=False)
    #tienedetraccion = fields.Boolean(string='Sujeto a Detracción?', compute='_get_tienedetraccion', store=True, copy=False) #Se calcula en automático
    detraccion_id = fields.Many2one('account.tax', string='Porcentaje', copy=False)
    det_fecpago = fields.Date('Fecha Pago Pago Det.', copy=False)
    det_nropago = fields.Char('Número Pago Det.', size=15, help="Para registrar el Nro. de Comprobante de Pago de Detracción")
    
    tipo_operacion = fields.Many2one('einvoice.catalog.51', string='Tipo de Operación', required=True, default=1, readonly=True, states={'draft': [('readonly', False)]})
    
    
    #is_gruped = fields.Boolean('Agrupar línea de factura por producto y precio?', copy=False,
    is_gruped = fields.Boolean('Agrupar línea de factura por producto y precio?', related='partner_id.is_gruped', readonly=True, store=True, copy=False,
                               help="Esto se configura en Contactos/Facturación.")
    invoice_line_group_ids = fields.One2many('account.invoice.line.group', 'invoice_id', 'Líneas agrupadas', readonly=True, copy=False)
    
    invoice_line_ids2 = fields.One2many('account.invoice.line2', 'invoice_id', 'Impresión Alterna', readonly=True, states={'draft':[('readonly',False)]}, copy=False)
    subtotal2 = fields.Monetary(string='Subtotal Alterno', store=True, compute='_compute_amount2', copy=False)
    
    amount_in_text = fields.Char('Son:', compute='_get_amount_in_words', readonly=True, states={'draft': [('readonly', False)]})
    
    #MODULO OCA DE NOTA DE CREDITO INTEGRADO
    #DE NOTA E CREDITO
    refund_reason = fields.Text(string="Refund reason")
    origin_invoice_ids = fields.Many2many(
        comodel_name='account.invoice', column1='refund_invoice_id',
        column2='original_invoice_id', relation='account_invoice_refunds_rel',
        string="Original invoice", readonly=False,
       help="Original invoice to which this refund invoice is referred to",
        copy=False,
    )
    refund_invoice_ids = fields.Many2many(
        comodel_name='account.invoice', column1='original_invoice_id',
        column2='refund_invoice_id', relation='account_invoice_refunds_rel',
        string="Refund invoices", readonly=False,
        help="Refund invoices created from this invoice",
        copy=False,
    )
    #DE NOTA DE DEBITO
    nd_invoice_ids = fields.Many2many(
        comodel_name='account.invoice', column1='nd_id',
        column2='nd_invoice_id', relation='account_invoice_nd_rel',
        string="Factura Original",
        help="Factura Original a la que se esta Nota de Débito está referida.",
        copy=False,
    )
    nd_ids = fields.Many2many(
        comodel_name='account.invoice', column1='nd_invoice_id',
        column2='nd_id', relation='account_invoice_nd_rel',
        string="Notas de Débito",
        help="Notas de Débito creadas para esta factura",
        copy=False,
    )
    
    #Guias Remision Remitente y Transportista, podrá ser usado para el envío de la Facturación electrónica
    sender_referral_guide = fields.Char('G.R. Remitente', size=13, readonly=True, states={'draft':[('readonly',False)]}, copy=False)
    sender_referral_guide_code = fields.Char('Tipo G.Rem.Remit.', size=2, default="09")
    carrier_referral_guide = fields.Char('G.R. Transportista', size=30, readonly=True, states={'draft':[('readonly',False)]}, copy=False)
    carrier_referral_guide_code = fields.Char('Tipo G.Rem.Transp.', size=2, default="31")
    
    #Información Extra
    comment_extra = fields.Char('Información Adicional', readonly=True, states={'draft':[('readonly',False)]}, copy=False)
    #Orden de Compra
    purchase_order = fields.Char(string='Orden de Compra', size=20)
    
    
    #Metodo que llena la tabla lineas agrupadas
    #Este metodo es invocado desde la facturacion electrónica
    @api.multi
    def invoice_line_group(self):
        
        print('Metodo ailg')
        print(self)
        print(self.is_gruped)
        
        if self.is_gruped == False:
            print(len(self.invoice_line_group_ids))
            if len(self.invoice_line_group_ids) > 0:
                print('Borra por Falso')
                for ilg_ids in self.invoice_line_group_ids:
                    ilg_ids.unlink()
                    
        else: #TRUE
            print('Gruped is True')
            print(self.invoice_line_ids)
            if self.invoice_line_ids: #Si tiene lineas se ejecuta
                #Elimino las lineas agrupadas de haber
                if len(self.invoice_line_group_ids) > 0:
                    print('Elimino las lineas')
                    for ilg_ids in self.invoice_line_group_ids:
                        ilg_ids.unlink()
                
                #Lleno las lineas agrupadas
                for ail in self.invoice_line_ids: #Recorro las lineas de la factura
                    # Busco el producto en la linea agrupada
                    ailg_o = self.env['account.invoice.line.group']
                    ailg_ids = self.env['account.invoice.line.group'].search([('invoice_id', '=', ail.invoice_id.id),('product_id', '=', ail.product_id.id),('price_unit', '=', ail.price_unit)])
                    
                    print(self.id)
                    print(ail.invoice_id.id)
                    
                    print(ailg_ids)
                    print(len(ailg_ids))
                    
                    if len(ailg_ids) > 0: #Si existe el producto con el mismo precio
                        print('Prod Existe')
                        for ailg in ailg_ids:
                            print('Prod Existe Acumulo')
                            print(ailg.quantity)
                            print(ail.quantity)
                            quantity_val = ailg.quantity + ail.quantity
                            price_subtotal_val = ailg.price_subtotal + ail.price_subtotal
                            price_total_val = ailg.price_total + ail.price_total
                            print('Actualiza')
                            ailg.write({'quantity': quantity_val,
                                        'price_subtotal': price_subtotal_val,
                                        'price_total': price_total_val})
                            
                    else: #No existe el producto, hay que crearlo
                        print('No existe')
                        #Traemos los impuestos por defecto
                        prodtaxes = ail.product_id.product_tmpl_id.taxes_id
                        print(prodtaxes)
                        prodtaxes_filter = prodtaxes.search([('id', 'in', prodtaxes.ids),('company_id', '=', ail.invoice_id.company_id.id)])
                        print(prodtaxes_filter)
                        
                        prod_taxes = prodtaxes_filter.ids
                            
                        print(prod_taxes)
                            
                        #taxesobj_ids = self.env['account.product_taxes_rel'].search([('invoice_id', '=', ail.invoice_id.id),('product_id', '=', ail.product_id.id),('price_unit', '=', ail.price_unit)])
                        print('Crea Nuevo')
                        
                        ailg_o.create({'invoice_id': self.id, 
                                       'product_id': ail.product_id.id,
                                       'name': ail.name,
                                       'quantity': ail.quantity,
                                       'uom_id': ail.uom_id.id,
                                       'price_unit': ail.price_unit,
                                       'price_subtotal': ail.price_subtotal,
                                       'price_total': ail.price_total,
                                       'invoice_line_tax_ids': [(6, 0, prod_taxes)],
                                       })
            
    
    #DEL MODULO OCA INTEGRADO
    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None,
                        description=None, journal_id=None):
        """Add link in the refund to the origin invoice and origin lines."""
        res = super(AccountInvoice, self)._prepare_refund(
            invoice, date_invoice=date_invoice, date=date,
            description=description, journal_id=journal_id,
        )
        res['origin_invoice_ids'] = [(6, 0, invoice.ids)]
        res['refund_reason'] = description
        refund_lines_vals = res['invoice_line_ids']
        for i, line in enumerate(invoice.invoice_line_ids):
            if i + 1 > len(refund_lines_vals):  # pragma: no cover
                # Avoid error if someone manipulate the original method
                break
            refund_lines_vals[i][2]['origin_line_ids'] = [(6, 0, line.ids)]
        return res
    
    #No debe verificar aquellos con estado cancelado.
    @api.multi
    def _check_duplicate_supplier_reference(self):
        for invoice in self:
            # refuse to validate a vendor bill/credit note if there already exists one with the same reference for the same partner,
            # because it's probably a double encoding of the same bill/credit note
            if invoice.type in ('in_invoice', 'in_refund') and invoice.reference:
                if self.search([('type', '=', invoice.type), ('reference', '=', invoice.reference), ('company_id', '=', invoice.company_id.id), ('commercial_partner_id', '=', invoice.commercial_partner_id.id), ('id', '!=', invoice.id), ('state', '!=', 'cancel')]):
                    raise UserError(_("Duplicated vendor reference detected. You probably encoded twice the same vendor bill/credit note."))
    
    @api.multi
    @api.returns('self')
    def refund(self, date_invoice=None, date=None, description=None, journal_id=None):
        new_invoices = self.browse()
        for invoice in self:
            # create the new invoice
            values = self._prepare_refund(invoice, date_invoice=date_invoice, date=date,
                                    description=description, journal_id=journal_id)
            refund_invoice = self.create(values)
            
            #Agrego la validacion del agrupamiento, de agruparse se deben borrar las invoice lines de la NC
            #print(refund_invoice.is_gruped)
            #print(refund_invoice.partner_id.is_gruped)
            if refund_invoice.partner_id.is_gruped:
                #print('es agrupado')
                #print(refund_invoice.invoice_line_ids)
                if refund_invoice.invoice_line_ids:
                    lines = refund_invoice.invoice_line_ids
                    #print('Borro')
                    lines.unlink()
                    
            
            invoice_type = {'out_invoice': ('customer invoices credit note'),
                'in_invoice': ('vendor bill credit note')}
            message = _("This %s has been created from: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a>") % (invoice_type[invoice.type], invoice.id, invoice.number)
            refund_invoice.message_post(body=message)
            new_invoices += refund_invoice
        return new_invoices
    
    @api.model
    def create(self, vals):
        #Obtengo el ID del nuevo registro a guardarse
        new_id = super(AccountInvoice, self).create(vals)
        
        #Verifico el total de las Líneas Alternativas
        if vals.get('invoice_line_ids2'):
            if vals.get('invoice_line_ids'):
                if new_id.amount_untaxed != new_id.subtotal2:
                    raise UserError(_('Error de Creación!\nNo puedes crear una Factura que tenga el Sub-Total de la Factura Alterna distinto al Sub-Total de las Lineas de Factura.'))
            else:
                raise UserError(_('Error de Creación!\nNo puedes crear una Factura que tenga Sub-Total de Factura Alterna y no tenga Lineas de Factura.'))
        
        return new_id
    
    @api.one
    @api.multi
    def write(self, vals):
        #Obtengo el ID de la factura guardada
        super(AccountInvoice, self).write(vals)
        #print (self.subtotal2)
        if self.subtotal2 > 0:
            print (self.amount_untaxed)
            if self.amount_untaxed > 0:
                if self.amount_untaxed != self.subtotal2:
                    raise UserError(_('Error de Actualización!\nNo puedes actualizar una Factura que tenga el Sub-Total de la Factura Alterna distinto al Sub-Total de las Lineas de Factura.'))
            else:
                raise UserError(_('Error de Actualización!\nNo puedes actualizar una Factura que tenga Sub-Total de Factura Alterna y no tenga Lineas de Factura.'))
        
        #Controla la Fecha de Vencimiento en los move lines.
        #Verifico si date_due viene en vals y si la factura tiene un move asignado para actualizarle la fecha de vencimiento
        if vals.get('date_due') and self.move_id:
            date_due_val = vals.get('date_due')
            for am in self.move_id:
                am.write({'fecvencimiento': date_due_val})
                if am.line_ids:
                    for aml in self.move_id.line_ids:
                        aml.write({'date_maturity': date_due_val})
        return True
    
    def tax_line_move_line_get(self):
        res = []
        # keep track of taxes already processed
        done_taxes = []
#        # loop the invoice.tax.line in reversal sequence
        for tax_line in sorted(self.tax_line_ids, key=lambda x: -x.sequence):
            if tax_line.amount_total or (len(self.tax_line_ids) == 1 and not tax_line.amount_total):
                tax = tax_line.tax_id
                if tax.amount_type == "group":
                    for child_tax in tax.children_tax_ids:
                        done_taxes.append(child_tax.id)
                res.append({
                    'invoice_tax_line_id': tax_line.id,
                    'tax_line_id': tax_line.tax_id.id,
                    'type': 'tax',
                    'name': tax_line.name,
                    'price_unit': tax_line.amount_total,
                    'quantity': 1,
                    'price': tax_line.amount_total,
                    'account_id': tax_line.account_id.id,
                    'account_analytic_id': tax_line.account_analytic_id.id,
                    'invoice_id': self.id,
                    'tax_ids': [(6, 0, list(done_taxes))] if tax_line.tax_id.include_base_amount else []
                })
                done_taxes.append(tax.id)
        return res
    
    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            if not inv.date_due:
                inv.with_context(ctx).write({'date_due': inv.date_invoice})
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml = inv.invoice_line_move_line_get()
            iml += inv.tax_line_move_line_get()

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, iml)

            name = inv.name or '/'
            if inv.payment_term_id:
                totlines = inv.with_context(ctx).payment_term_id.with_context(currency_id=company_currency.id).compute(total, inv.date_invoice)[0]
                res_amount_currency = total_currency
                ctx['date'] = inv._get_currency_rate_date()
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id
                })
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            line = inv.finalize_invoice_move_lines(line)

            date = inv.date or inv.date_invoice
            
            
            #Calculo Bases Imponibles IGV e ISC, Exoneradas e Inafectas desde tabla Line_Tax hacia Move
            baseimponible_val = baseisc_val = baseexonerada_val = baseinafecta_val = 0.00
            if inv.tax_line_ids:
                for tline in inv.tax_line_ids:
                    if tline.tax_id.tax_sunat.code == "1000": #IGV
                        if tline.tax_id.tax_sunat_effect.code == "10": # OPERACION ONEROSA
                            baseimponible_val = tline.base
                            
                    elif tline.tax_id.tax_sunat.code == "9997": #EXONERADO
                        if tline.tax_id.tax_sunat_effect.code == "20": # OPERACION ONEROSA
                            baseexonerada_val = tline.base
                    
                    elif tline.tax_id.tax_sunat.code == "9998": #INAFECTO
                        if tline.tax_id.tax_sunat_effect.code == "30": # OPERACION ONEROSA
                            baseinafecta_val = tline.base
                            
                    elif tline.tax_id.tax_sunat.code == "2000": #ISC
                        baseisc_val = tline.base


            #Traigo el tipo de cambio en formato peruano
            to_currency = self.env['res.currency'].search([('name', '=', 'USD')])
            rate_val = to_currency.rate_pe
            #from_currency = self.env['res.currency'].search([('name', '=', 'PEN')])
            #print (from_currency)
            #to_currency = self.env['res.currency'].search([('name', '=', 'USD')])
            #print (to_currency)
            #rate_val = 1 / self.env['res.currency']._get_conversion_rate(from_currency, to_currency)
            #print (rate_val)
            
            #Genero el secuencial del Libro/Registro Contable
            if not self.sec_journal_libro: #En caso de Compra y volver a borrador, no debe cambiar al reemitirla
                sec_journal_libro_val = sec_journal_libro_code_val = None
                if self.journal_id.sequence_tipolibro_id:
                    sec_journal_libro_code_val = self.journal_id.sequence_tipolibro_id.code or None
                    if sec_journal_libro_code_val:
                        if self.company_id:
                            sec_journal_libro_val = self.env['ir.sequence'].with_context(force_company=self.company_id.id).next_by_code(sec_journal_libro_code_val) or 'ERR'
                            self.write({'sec_journal_libro': sec_journal_libro_val})
                        else:
                            sec_journal_libro_val = self.env['ir.sequence'].next_by_code(sec_journal_libro_code_val) or 'ERR'
                            self.write({'sec_journal_libro': sec_journal_libro_val})
            else: #Si existe lo vuelvo a mandar al move
                sec_journal_libro_val = self.sec_journal_libro
            
            move_vals = {
                'estadocomprobante': '0',
                'feccomprobante': inv.date_invoice,
                'fecvencimiento': inv.date_due,
                'serie': inv.serie,
                #'correlativo': inv.correlativo,
                'detraccion': inv.tienedetraccion,
                'det_code': inv.det_code.id,
                'detraccion_id': inv.detraccion_id.id,
                'det_fecpago': inv.det_fecpago,
                'det_nropago': inv.det_nropago,
                'tipocambio': rate_val,
                
                'sec_journal_libro': sec_journal_libro_val,
                
                'baseimponible': baseimponible_val,
                'baseisc': baseisc_val,
                'baseexonerada': baseexonerada_val,
                'baseinafecta': baseinafecta_val,
                'totaltrib': inv.amount_tax or 0,
                'importesubtotal': inv.amount_untaxed or 0,
                'importetotal': inv.amount_total or 0,
                
                'tipo_operacion': inv.tipo_operacion.id,
                
                'ref': inv.reference,
                'line_ids': line,
                'journal_id': journal.id,
                'date': date,
                'narration': inv.comment,
            }
            ctx['company_id'] = inv.company_id.id
            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
            #move.with_context(ctx).write({'correlativo': inv.correlativo}) #+ Para tener el correlativo luego de creada la factura
            move.write({'correlativo': inv.correlativo}) #+ Para tener el correlativo luego de creada la factura
        return True
    
    @api.multi
    def action_invoice_draft(self):
        #Elimina el move para poder reemitir la factura de venta con los mismos correlativos, en compras se eimina en el cancel.
        if self.move_id:
            am = self.move_id
            self.write({'move_id': False})
            am.button_cancel()
            am.unlink()
            
        return super(AccountInvoice, self).action_invoice_draft()
    
    @api.multi
    def action_cancel(self):
        moves = self.env['account.move']
        moves_lines = self.env['account.move.line'] #+
        for inv in self:
            if inv.move_id:
                moves += inv.move_id
                if inv.move_id.line_ids: #+
                    moves_lines += inv.move_id.line_ids #+ 
            if inv.payment_move_line_ids:
                raise UserError(_('You cannot cancel an invoice which is partially paid. You need to unreconcile related payment entries first.'))
        
        #El proceso es diferente en ventas y compras.
        if self.type in ['out_invoice', 'out_refund']: #Venta o NC Cliente Física
            # First, set the invoices as cancelled and detach the move ids
    #        self.write({'state': 'cancel', 'move_id': False}) #-
            self.write({'state': 'cancel'}) #+
            if moves:
                # second, invalidate the move(s)
                moves.button_cancel()
                # delete the move this invoice was pointing to
                # Note that the corresponding move_lines and move_reconciles
                # will be automatically deleted too
    #            moves.unlink() #-
                
                # Elimino las líneas
                #print (moves_lines)
                moves_lines.unlink() #+
                
                #Cambio el estado y limpio acumuladores
                moves.write({'estadocomprobante': '1', 'baseimponible': 0, 'baseexonerada': 0, 'baseinafecta': 0, 'totaltrib': 0, 'importetotal': 0})
                
                #Creo un move line donde indico el partner especial de DOCUMENTO ANULADO (00000000000) de paso que sirve para el import al Siscont
                for move in moves:
                    #Buscamos el Partner Pivote de Documento Anulado
                    partner_id_aux = self.env['res.partner'].search([('tipo_doc_id.code', '=', '0'), ('vat', '=', '00000000000')])
                    if partner_id_aux:
                        partner_id_val = partner_id_aux
                    else:
                        raise UserError(_('En Contactos no existe el Partner para Documento Anulado. Debe tener tipo de Documento con código 0 - Sin Documento, RUC con 00000000000 y nombre DOCUMENTO ANULADO'))
                    
                    #Buscamos la cuenta contable pivote, debe ser del tipo impuesto = IGV y que sea Gravado. Por compañia.
                    company_id_val = inv.company_id.id
                    tax_id_aux = self.env['account.tax'].search([('tax_sunat.code', '=', '1000'), ('tax_sunat_effect.code', '=', '10'), ('company_id', '=', company_id_val)], limit=1)
                    if tax_id_aux:
                        account_id_val = tax_id_aux.account_id
                    else:
                        raise UserError(_('Es necesario que se cree un Impuesto tipo IGV y que sea del tipo gravado para poder tomar la cuenta contable correcta.'))
                    
                    #Armamos el move.line para crearlo
                    linea = {
                             'name': 'ANULADO',
                             'account_id': account_id_val.id,
                             'move_id': move.id,
                             'date_maturity': move.feccomprobante,
                             'partner_id': partner_id_val.id,
                             'company_id': move.company_id.id #Para que soporte el multicompany
                             }
                    
                    self.env['account.move.line'].create(linea)
                
                moves.post()
        else: #Compra o NC Cliente Físicas, como no pasa al Registro de Compras, borro los AML y AM
            # First, set the invoices as cancelled and detach the move ids
            self.write({'state': 'cancel', 'move_id': False})
            if moves:
                # second, invalidate the move(s)
                moves.button_cancel()
                # delete the move this invoice was pointing to
                # Note that the corresponding move_lines and move_reconciles
                # will be automatically deleted too
                moves.unlink()
            
        return True


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    _order = "name"

    origin_line_ids = fields.Many2many(
        comodel_name='account.invoice.line', column1='refund_line_id',
        column2='original_line_id', string="Original invoice line",
        relation='account_invoice_line_refunds_rel',
        help="Original invoice line to which this refund invoice line "
             "is referred to",
        copy=False,
    )
    refund_line_ids = fields.Many2many(
        comodel_name='account.invoice.line', column1='original_line_id',
        column2='refund_line_id', string="Refund invoice line",
        relation='account_invoice_line_refunds_rel',
        help="Refund invoice lines created from this invoice line",
        copy=False,
    )
    date = fields.Date('Fecha Contable', related='invoice_id.date', store=True, copy=False)
    reference = fields.Char('Num. Comprobante', related='invoice_id.reference', store=True, copy=False)
    state = fields.Selection([
            ('draft','Draft'),
            ('open', 'Open'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', related='invoice_id.state', store=True, copy=False)
   
    
   
    
    
    
    
    
    
    
    