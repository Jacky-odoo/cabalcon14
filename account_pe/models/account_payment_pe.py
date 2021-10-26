# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class account_payment(models.Model):
    _inherit = "account.payment"

    def _get_move_vals(self, journal=None):
        """ Return dict to create the payment move
        """
        journal = journal or self.journal_id
        if not journal.sequence_id:
            raise UserError(_('Configuration Error !'), _('The journal %s does not have a sequence, please specify one.') % journal.name)
        if not journal.sequence_id.active:
            raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
        name = self.move_name or journal.with_context(ir_sequence_date=self.payment_date).sequence_id.next_by_id()
        
        #Traigo el tipo de cambio
        from_currency = self.env['res.currency'].search([('name', '=', 'PEN')])
        print (from_currency)
        to_currency = self.env['res.currency'].search([('name', '=', 'USD')])
        print (to_currency)
        rate_val = 1 / self.env['res.currency']._get_conversion_rate(from_currency, to_currency)
        print (rate_val)
        
        #Genero el secuencial del Libro/Registro Contable
        sec_journal_libro_val = sec_journal_libro_code_val = None
        if self.journal_id.sequence_tipolibro_id:
            sec_journal_libro_code_val = self.journal_id.sequence_tipolibro_id.code or None
            if sec_journal_libro_code_val:
                if self.company_id:
                    sec_journal_libro_val = self.env['ir.sequence'].with_context(force_company=self.company_id.id).next_by_code(sec_journal_libro_code_val) or 'ERR'
                else:
                    sec_journal_libro_val = self.env['ir.sequence'].next_by_code(sec_journal_libro_code_val) or 'ERR'
        self.write({'sec_journal_libro': sec_journal_libro_val})
                                
        return {
            'name': name,
            'date': self.payment_date,
            'ref': self.communication or '',
            'company_id': self.company_id.id,
            'journal_id': journal.id,
            'tipocambio': rate_val,
            'sec_journal_libro': sec_journal_libro_val,
#            'sisc_num_comprob': sisc_num_comprob_val,
        }
    
    #sisc_num_comprob = fields.Char('Siscont Voucher', size=4, copy=False, help='Secuencial mensual interno por Diario. Número de Comprobante en Siscont')
    sec_journal_libro = fields.Char('Secuencia Libro/Registro', copy=False, help='Secuencia del Libro Contable')
    