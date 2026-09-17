from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class GelatoPromoCode(models.Model):
    _name = "gelato.promo.code"
    _description = "Promo Code"
    _order = "date_to desc, code"

    code = fields.Char(
        string="Code",
        required=True,
        help="What the customer copies from a leaflet or from Instagram. "
        "Case does not matter.",
    )
    description = fields.Char(
        string="What the code is for",
        translate=True,
        help="A note for you. It is not shown on the website.",
    )
    discount_percent = fields.Float(
        string="Discount (%)",
        required=True,
        default=10.0,
        digits=(5, 2),
    )
    date_from = fields.Date(
        string="Valid from",
        help="Leave empty for no limit.",
    )
    date_to = fields.Date(
        string="Valid until",
        help="Leave empty for no limit. The last valid day is included.",
    )
    usage_limit = fields.Integer(
        string="Usage limit",
        default=0,
        help="How many times the code may be used in total. 0 means unlimited.",
    )
    usage_count = fields.Integer(
        string="Used",
        default=0,
        readonly=True,
    )
    usage_left = fields.Integer(
        string="Remaining",
        compute="_compute_usage_left",
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    order_ids = fields.One2many(
        comodel_name="gelato.delivery.order",
        inverse_name="promo_code_id",
        string="Orders using this code",
    )

    _sql_constraints = [
        (
            "code_uniq",
            "unique(code)",
            "This promo code already exists.",
        ),
    ]

    @api.depends("usage_limit", "usage_count")
    def _compute_usage_left(self):
        for record in self:
            if record.usage_limit:
                record.usage_left = max(record.usage_limit - record.usage_count, 0)
            else:
                record.usage_left = 0

    @api.constrains("discount_percent")
    def _check_discount_percent(self):
        for record in self:
            if not 0 < record.discount_percent <= 100:
                raise ValidationError(
                    _("The discount must be greater than 0 and at most 100%.")
                )

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError(
                    _("“Valid from” cannot be later than “Valid until”.")
                )

    @api.onchange("code")
    def _onchange_code(self):
        if self.code:
            self.code = self.code.strip().upper()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code"):
                vals["code"] = vals["code"].strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("code"):
            vals = dict(vals)
            vals["code"] = vals["code"].strip().upper()
        return super().write(vals)

    # ------------------------------------------------------------------
    # Validation from the website
    # ------------------------------------------------------------------
    @api.model
    def find_valid(self, code):
        """Return a valid code, or an empty recordset.

        This is called from the public website, so it reads through sudo -
        an anonymous visitor has no access to the promo code model.
        """
        if not code:
            return self.browse()
        normalized = code.strip().upper()
        if not normalized:
            return self.browse()

        today = fields.Date.context_today(self)
        promo = self.sudo().search(
            [
                ("code", "=", normalized),
                ("active", "=", True),
                "|", ("date_from", "=", False), ("date_from", "<=", today),
                "|", ("date_to", "=", False), ("date_to", ">=", today),
            ],
            limit=1,
        )
        if promo and promo.usage_limit and promo.usage_count >= promo.usage_limit:
            return self.browse()
        return promo

    def register_use(self):
        """Count one use. Called after an order is created."""
        for record in self.sudo():
            record.usage_count += 1
        return True
