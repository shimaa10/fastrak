# -*- coding: utf-8 -*-
{
    'name': "trial_balance_report",
    'summary': """Trial Balance Report""",
    'description': """Trial Balance Report""",
    'author': "Mina Samy",
    'website': "",
    'category': 'Invoicing',
    'version': '13.0.0.1',
    'depends': ['base', 'accounting_pdf_reports'],
    'data': [
        'reports/report_trial_balance.xml',
        'reports/report.xml',
        'wizard/trial_balance.xml',
    ]
}
