# -*- coding: utf-8 -*-
{
    'name': "reparaciones",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Cesar Lopez Robredo",
    'website': "cesarlopez173@yahoo.com.mx",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'sale',
        'product',
        'fleet',
        'sale_stock',
        'sale_management',
        'sales_team',
        'sale_account_taxcloud',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/reparaciones_view.xml'
    ],
    # only loaded in demonstration mode
    'installable': True,
    'application': True,
    'auto_install': False,
}
