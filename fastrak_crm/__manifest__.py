# -*- coding: utf-8 -*-
{
    'name': "Fastrak CRM",

    'summary': """
        Fastrak Crm Module
        """,

    'description': """
        Fastrak Crm Module
    """,

    'author': "Minos@Elite's Hub",
    'website': "https://www.elites-hub.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales/CRM',
    'version': '13.0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'crm'],

    # always loaded
    'data': [
        'security/target_security/ir.model.access.csv',
        'views/target_views/target_views.xml',
        'views/crm/lead_views.xml',
        'views/crm/lead_to_opportunity_inherit.xml',

        # Reports
        # 'wizards/crm_report_wizard.xml',
        'wizards/crm_target_report_wizard.xml',
        'wizards/crm_lead_report_wizard.xml',
        'reports/reports.xml',
        # 'reports/crm_report.xml',
        'reports/crm_target_report.xml',
        'reports/crm_lead_report.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
