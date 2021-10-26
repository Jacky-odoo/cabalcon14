# -*- coding: utf-8 -*-
{
    'name': "Localización para Perú v11",
    'summary': """Localiza Odoo para Perú v11""",

    'description': """Instala dependencias, plan de cuentas y modificaciones""",

    'author': "Jose Balbuena A. (Cabalcon S.A.C.)",
    'website': "http://www.cabalcon.com.pe",
    'category': "Customization",
    'version': "1.0",

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'contacts',
        'account',
        'l10n_pe',
        'account_tax_python',
        'odoope_einvoice_base',
        'account_invoice_dates',
        'account_group_menu',
        'validation_ruc_dni',
        'odoope_currency',
        ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/partner_view.xml',
        'views/account_view_pe.xml',
        'views/account_invoice_views_pe.xml',
        'views/account_payment_view_pe.xml',
        'wizard/account_invoice_refund_view.xml',
        'data/ir.sequence.xml',
        'data/account.journal.xml',
        ],

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
        ],
    
    'post_init_hook': "post_init_hook",
}







