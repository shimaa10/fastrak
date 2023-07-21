# -*- coding: utf-8 -*-
{
    'name': "fastrak",

    'summary': """
        Fastrak Custom Module""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Mina Samy",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'base_automation', 'mail', 'account', 'om_account_accountant', 'hr', 'contacts'],

    # always loaded
    'data': [
        # Custom Layout
        'views/reports/fastrak_custom_external_layout.xml',
        'views/reports/custom_paper_format.xml',
        # Generic
        'views/generic_groups.xml',

        # Company
        'views/company/fastrak_custom_res_company.xml',
        # User
        'views/user/res_user_views.xml',

        # Product
        'views/product/product_views.xml',

        # Employee
        'views/hr/hr_employee_views.xml',
        'views/hr/hr_department_views.xml',

        # Account & Invoice
        'views/account/account_move_inherit_views.xml',
        'views/account/account_account_views.xml',
        'views/account/coa_groups.xml',
        'views/invoice/custom_invoice_view.xml',
        'views/invoice/custom_invoice_report.xml',

        'views/partner/partner_views.xml',
        'views/bank/bank_views.xml',
        # BOL
        'views/bill_of_loading/bill_of_loading_report.xml',
        'views/bill_of_loading/bill_of_loading_views.xml',
        # 'views/bill_of_loading/automated_actions.xml',

        # Group Invoice
        'views/group_invoice/wizards/group_invoice_discount_wizard_views.xml',
        'views/group_invoice/group_invoice_views.xml',
        'views/group_invoice/group_invoice_scheduled_action.xml',
        'views/group_invoice/group_credit_invoice_report.xml',

        # Customer Withdrawal Request
        'views/withdraw_request/withdraw_request_views.xml',
        'views/withdraw_request/withdraw_request_commission.xml',
        # 'views/withdraw_request/withdraw_request_report.xml',

        # Cancellation Reasons
        'views/cancellation_reason/cancellation_reason_views.xml',

        # Wizard Section
        'wizards/bill_of_loading.xml',
        'wizards/report_group_invoice.xml',

        # Custom Wizard Report Section
        'reports/reports.xml',
        'reports/report_bill_of_loading.xml',
        'reports/report_group_invoice.xml',

        # Logs
        'views/log/log_views.xml',
        'views/log/log_scheduler.xml',

        # Security File
        'security/ir.model.access.csv',

    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
