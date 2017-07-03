# -*- coding: utf-8 -*-
# © 2017 Christophe CHAUVET <christophe.chauvet@gmail.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError


class MooncardAccount(models.Model):
    _name = 'mooncard.account'
    _description = 'Moon Card Account'

    code = fields.Char(
        string='Short Name', help='Mooncard account from the website')
    name = fields.Char(
        string='Token Number', required=True, size=9, copy=False,
        help="Enter the 9 digits number written at the website")
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'mooncard.account'))
    card_ids = fields.One2many('mooncard.card', 'moonacc_id', string='Cards',
                               help='Cards link to this account')

    @api.one
    @api.constrains('name')
    def name_check(self):
        if self.name and not self.name.isdigit():
            raise ValidationError(
                _("'%s' is not a valid Mooncard Account token. "
                "It should only have digits") % self.name)

    _sql_constrains = [(
        'account_token_uniq',
        'unique(name)',
        'This Moon Card Account already exists in the database!'
        )]
