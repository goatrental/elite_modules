from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    gelato_delivery_site = fields.Boolean(
        related="website_id.gelato_delivery_site",
        readonly=False,
    )
    gelato_delivery_email = fields.Char(
        related="website_id.gelato_delivery_email",
        readonly=False,
    )
    gelato_delivery_fee = fields.Float(
        related="website_id.gelato_delivery_fee",
        readonly=False,
    )
    gelato_delivery_free_from = fields.Float(
        related="website_id.gelato_delivery_free_from",
        readonly=False,
    )
    gelato_delivery_fee_base = fields.Selection(
        related="website_id.gelato_delivery_fee_base",
        readonly=False,
    )
    gelato_delivery_fee_vat_rate = fields.Float(
        related="website_id.gelato_delivery_fee_vat_rate",
        readonly=False,
    )
    gelato_delivery_min_days = fields.Integer(
        related="website_id.gelato_delivery_min_days",
        readonly=False,
    )
    gelato_delivery_promo_note = fields.Char(
        related="website_id.gelato_delivery_promo_note",
        readonly=False,
    )
