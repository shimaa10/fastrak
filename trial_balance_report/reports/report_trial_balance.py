# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportTrialBalance(models.AbstractModel):
    _name = 'report.trial_balance_report.report_trial_balance_document'

    def _get_accounts(self, accounts, display_account):
        """ compute the balance, debit and credit for the provided accounts
            :Arguments:
                `accounts`: list of accounts record,
                `display_account`: it's used to display either all accounts or those accounts which balance is > 0
            :Returns a list of dictionary of Accounts with following key and value
                `name`: Account name,
                `code`: Account code,
                `credit`: total amount of credit,
                `debit`: total amount of debit,
                `balance`: total amount of balance,
        """

        account_result = {}
        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        # compute the balance, debit and credit for the provided accounts
        request = (
                "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" + \
                " FROM " + tables + " WHERE account_id IN %s " + filters + " GROUP BY account_id")
        params = (tuple(accounts.ids),) + tuple(where_params)
        self.env.cr.execute(request, params)
        for row in self.env.cr.dictfetchall():
            account_result[row.pop('id')] = row

        account_res = []
        for account in accounts:
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            currency = account.currency_id and account.currency_id or account.company_id.currency_id
            res['code'] = account.code
            res['name'] = account.name
            if account.id in account_result:
                res['debit'] = account_result[account.id].get('debit')
                res['credit'] = account_result[account.id].get('credit')
                res['balance'] = account_result[account.id].get('balance')
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)
            if display_account == 'movement' and (
                    not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])):
                account_res.append(res)
        return account_res

    def account_trial_bl(self, data):
        # display array
        lines = []
        # create array for all move before date from
        initSQL = """
            SELECT SUM(debit) as init_d, SUM(credit) as init_c, aa.*, ml.parent_state
            from account_account aa 
            LEFT join account_move_line ml 
            on aa.id = ml.account_id 
            GROUP BY aa.id ,ml.date, ml.parent_state
            HAVING ml.date < '{}'
            and ml.parent_state = '{}'
            ORDER BY aa.code ASC""".format(data['date_from'],"posted")
        self.env.cr.execute(initSQL)
        initAcc = self.env.cr.dictfetchall()
        # create array for all move between date from & to
        filterSQL = """
            SELECT SUM(debit) as filter_d, SUM(credit) as filter_c, aa.*, ml.parent_state
            from account_account aa 
            LEFT join account_move_line ml 
            on aa.id = ml.account_id 
            GROUP BY aa.id ,ml.date, ml.parent_state
            HAVING date between '{}' and '{}'
            and ml.parent_state = '{}'
            ORDER BY aa.code ASC""".format(data['date_from'], data['date_to'],"posted")
        self.env.cr.execute(filterSQL)
        filterAcc = self.env.cr.dictfetchall()
        # create array for all move
        allAccount = """SELECT SUM(debit) as total_d, SUM(credit) as total_c, aa.* from account_account aa 
                   LEFT join account_move_line ml on aa.id = ml.account_id GROUP BY aa.id ORDER BY code ASC"""
        self.env.cr.execute(allAccount)
        allAccount = self.env.cr.dictfetchall()

        # merge three array
        # counter to move on array init and filter
        init = 0
        filter = 0

        # sum array
        init_d = init_c = filter_d = filter_c = total_d = total_c = 0
        for x in allAccount:
            # calculate Adjusted Balance
            if x['total_c'] != None or x['total_d'] != None:
                # calculate total balance debit or credit

                final_row = {
                    'code': x['code'],
                    'Account': x['name'],
                    'init_d': 0,
                    'init_c': 0,
                    'filter_d': 0,
                    'filter_c': 0,
                    'total_d': 0,
                    'total_c': 0,
                }

                # check if have same id marge and move one step on initAcc array else skip

                # check if in range
                if len(initAcc) > init:
                    # check same code
                    if initAcc[init]['code'] == x['code']:
                        # if initAcc[init]['parent_state'] == "posted":
                        # loop on all account in different date
                        while True:
                            final_row['init_d'] += initAcc[init]['init_d']
                            final_row['init_c'] += initAcc[init]['init_c']
                            init += 1
                            # check if in range
                            if len(initAcc) > init:
                                # check if have other date for this account
                                if initAcc[init]['code'] != x['code']:
                                    break
                            else:
                                break


                # check if have same id marge and move one step on filterAcc array else skip
                if len(filterAcc) > filter:
                    if filterAcc[filter]['code'] == x['code']:
                        # if filterAcc[filter]['parent_state'] == "posted":
                        while True:
                            final_row['filter_d'] += filterAcc[filter]['filter_d']
                            final_row['filter_c'] += filterAcc[filter]['filter_c']
                            filter += 1
                            if len(filterAcc) > filter:
                                if filterAcc[filter]['code'] != x['code']:
                                    break
                            else:
                                break

                td = final_row['init_d'] + final_row['filter_d']
                tc = final_row['init_c'] + final_row['filter_c']

                tsum = td - tc
                if tsum > 0:
                    td = tsum
                    tc = 0
                elif tsum < 0:
                    td = 0
                    tc = tsum * -1
                elif tsum == 0:
                    td = 0
                    tc = 0

                final_row['total_d'] = td
                final_row['total_c'] = tc

                # add to lines to display
                if final_row['init_d'] != 0 or final_row['init_c'] != 0 or final_row['filter_d'] != 0 or final_row['filter_c'] != 0:
                    lines.append(final_row)

                # add value to sum
                init_d += final_row['init_d']
                init_c += final_row['init_c']
                filter_d += final_row['filter_d']
                filter_c += final_row['filter_c']
                total_d += final_row['total_d']
                total_c += final_row['total_c']

        # create sum array
        sumArray = {
            'init_d': init_d,
            'init_c': init_c,
            'filter_d': filter_d,
            'filter_c': filter_c,
            'total_d': total_d,
            'total_c': total_c,
        }
        return sumArray, lines

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids', []))
        # display_account = data['form'].get('display_account')
        # accounts = docs if self.model == 'account.account' else self.env['account.account'].search([])
        # account_res = self.with_context(data['form'].get('used_context'))._get_accounts(accounts, display_account)

        account_sum, accountsa_cf = self.account_trial_bl(data['form'])

        return {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'Accounts_CF': accountsa_cf,
            'account_sum': account_sum,
            # 'Accounts': account_res,
        }
