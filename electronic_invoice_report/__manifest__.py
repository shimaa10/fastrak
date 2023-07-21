# -*- coding: utf-8 -*-
{
    'name': "Electronic Invoice Report",
    'summary': """ Electronic Invoice Report for egyptian institution of tax """,
    'description': """ Electronic Invoice Report """,
    'author': "Mina Samy",
    'website': "http://www.yourcompany.com",
    'category': 'accounting',
    'version': '0.1',
    'depends': ['base', 'account'],

    'data': [
        'report/electronic_invoice_report.xml',
        'customer_report/customer_report.xml',
    ],

    'external_dependencies': {
        'python': ['xlwt']
    }

}
