# -*- encoding: UTF-8 -*-

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def get_moves_ordered(self):
        for move in self:
            if move.type == 'out_invoice':
                # Added extra .filtered(lambda line: line.credit or line.debit) to remove lines with CR=0  & DR=0
                return move.line_ids.sorted(key=lambda r: r.credit).filtered(lambda line: line.credit or line.debit)
            else:
                return move.line_ids.sorted(key=lambda r: r.credit)

    def total_debit_credit(self):
        res = {}
        for move in self:
            dr_total = 0
            cr_total = 0
            for line in move.line_ids:
                dr_total += line.debit
                cr_total += line.credit

            res.update({'cr_total': cr_total, 'dr_total': dr_total})

        return res
