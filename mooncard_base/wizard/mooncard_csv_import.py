# -*- coding: utf-8 -*-
# © 2016-2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import unicodecsv
from tempfile import TemporaryFile
import logging
import pycountry

logger = logging.getLogger(__name__)


class MooncardCsvImport(models.TransientModel):
    _name = 'mooncard.csv.import'
    _description = 'Import Mooncard Transactions'

    mooncard_file = fields.Binary(string='CSV file', required=True)
    filename = fields.Char(string='Filename')

    @api.model
    def convert_datetime_to_utc(self, date_time_str):
        # %z can only be used in strptime() starting from python 3.2
        if date_time_str[-2:].isdigit():
            date_time_dt = datetime.strptime(
                date_time_str[:19], '%Y-%m-%d %H:%M:%S')
            if date_time_str[20] == '+':
                date_time_dt -= timedelta(
                    hours=int(date_time_str[21:23]),
                    minutes=int(date_time_str[23:]))
            elif date_time_str[20] == '-':
                date_time_dt += timedelta(
                    hours=int(date_time_str[21:23]),
                    minutes=int(date_time_str[23:]))
        else:
            date_time_dt = datetime.strptime(
                date_time_str, '%Y-%m-%d %H:%M:%S %Z')
        return date_time_dt

    @api.model
    def _prepare_transaction(self, line, speeddict, action='create'):
        product_id = False
        if line.get('expense_category_code'):
            product_id = speeddict['products'].get(
                line['expense_category_code'])
        vals = {
            'transaction_type': line.get('transaction_type'),
            'description': line.get('title'),
            'expense_categ_code': line.get('expense_category_code'),
            'expense_categ_name': line.get('expense_category_name'),
            'product_id': product_id,
            'vat_company_currency': float(
                line.get('vat_eur').replace(',', '.')),
            'image_url': line.get('attachment'),
            }

        if action == 'update':
            return vals

        # Continue with fields required for create
        country_id = False
        if line.get('country_code') and len(line['country_code']) == 3:
            logger.debug(
                'search country with code %s with pycountry',
                line['country_code'])
            pcountry = pycountry.countries.get(alpha_3=line['country_code'])
            if pcountry:
                countries = self.env['res.country'].search(
                    [('code', '=', pcountry.alpha_2)])
                if countries:
                    country_id = countries[0].id
        currencies = self.env['res.currency'].search(
            [('name', '=', line.get('original_currency'))])
        currency_id = currencies and currencies[0].id or False
        card_id = False
        if line.get('card_token'):
            card_id = speeddict['tokens'].get(line['card_token'])
            if not card_id:
                raise UserError(_(
                    "The CSV file contains the Moon Card '%s'. This "
                    "card is not registered in Odoo, cf menu "
                    "Accounting > Configuration > Miscellaneous > "
                    "Moon Cards)") % line.get('card_token'))

        vals.update({
            'unique_import_id': line.get('id'),
            'date': self.convert_datetime_to_utc(line['date_transaction']),
            'card_id': card_id,
            'country_id': country_id,
            'merchant': line.get('merchant'),
            'total_company_currency': float(
                line.get('amount_eur').replace(',', '.')),
            'total_currency': float(
                line.get('amount_currency').replace(',', '.')),
            'currency_id': currency_id,
        })
        return vals

    @api.model
    def _prepare_speeddict(self):
        company = self.env.user.company_id
        token_res = self.env['mooncard.card'].search_read(
            [('company_id', '=', company.id)], ['name'])
        speeddict = {'tokens': {}, 'products': {}}
        for token in token_res:
            speeddict['tokens'][token['name']] = token['id']

        partner_id = self.env.ref('mooncard_base.mooncard_supplier').id
        product_sinfos = self.env['product.supplierinfo'].search([
            ('name', '=', partner_id),
            '|', ('company_id', '=', False), ('company_id', '=', company.id)])
        for product_sinfo in product_sinfos:
            speeddict['products'][product_sinfo.product_code] =\
                product_sinfo.product_tmpl_id.product_variant_ids[0].id
        return speeddict

    @api.multi
    def mooncard_import(self):
        self.ensure_one()
        mto = self.env['mooncard.transaction']
        speeddict = self._prepare_speeddict()
        logger.info('Importing Mooncard transactions.csv')
        fileobj = TemporaryFile('w+')
        fileobj.write(self.mooncard_file.decode('base64'))
        fileobj.seek(0)
        reader = unicodecsv.DictReader(
            fileobj, delimiter=';',
            quoting=unicodecsv.QUOTE_MINIMAL, encoding='utf8')
        i = 0
        exiting_transactions = {}
        existings = mto.search([])
        for l in existings:
            exiting_transactions[l.unique_import_id] = l
        mt_ids = []
        for line in reader:
            i += 1
            # replace '' by False, so as to make the domains such as
            # ('image_url', '!=', False) work
            # and strip regular strings
            for key, value in line.iteritems():
                if value:
                    line[key] = value.strip()
                else:
                    line[key] = False
            logger.debug("line=%s", line)
            if not line.get('id'):
                raise UserError(_(
                    "Missing ID in CSV file line %d.") % i)
            if line['id'] in exiting_transactions:
                transaction = exiting_transactions[line['id']]
                logger.debug(
                    'Existing line with unique ID %s (odoo ID %s, state %s)',
                    line['id'], transaction.id, transaction.state)
                if transaction.state == 'draft':
                    # update existing lines
                    wvals = self._prepare_transaction(
                        line, speeddict, action='update')
                    transaction.write(wvals)
                    mt_ids.append(transaction.id)
                continue
            vals = self._prepare_transaction(line, speeddict)
            transaction = mto.create(vals)
            mt_ids.append(transaction.id)
        fileobj.close()
        if not mt_ids:
            raise UserError(_("No Mooncard transaction created nor updated."))
        action = self.env['ir.actions.act_window'].for_xml_id(
            'mooncard_base', 'mooncard_transaction_action')
        action.update({
            'domain': "[('id', 'in', %s)]" % mt_ids,
            'views': False,
            'nodestroy': False,
            })
        return action
