# -*- coding: utf-8 -*-
# © 2017 Christophe CHAUVET <christophe.chauvet@gmail.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Mooncard Exepnse',
    'version': '8.0.1.0.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Create HR exepnse from mooncard transactions',
    'author': 'Mirounga',
    'website': 'http://www.mirounga.fr',
    'depends': ['mooncard_base', 'hr_expense'],
    'data': [
        # 'data/partner.xml',
        # 'views/mooncard_transaction.xml',
        # 'views/mooncard_card.xml',
        # 'views/account_config_settings.xml',
        # 'views/company.xml',
    ],
    'images': [
        'static/description/banner_odoo_mooncard.jpg',
        'static/description/diagram_odoo_mooncard.jpg',
        ],
    'installable': True,
}
