import logging
from datetime import date

from odoo import _, api, fields, models
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)

TIME_SLOTS = [
    ("asap", "As soon as possible"),
    ("11_13", "11:00 to 13:00"),
    ("13_15", "13:00 to 15:00"),
    ("15_17", "15:00 to 17:00"),
    ("17_19", "17:00 to 19:00"),
    ("19_20", "19:00 to 20:00"),
]


class GelatoDeliveryOrder(models.Model):
    _name = "gelato.delivery.order"
    _description = "Delivery Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "delivery_date desc, id desc"

    name = fields.Char(
        string="Order number",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    stage_id = fields.Many2one(
        comodel_name="gelato.delivery.stage",
        string="Stage",
        group_expand="_read_group_stage_ids",
        default=lambda self: self._default_stage(),
        ondelete="restrict",
        index=True,
        copy=False,
        tracking=True,
        help="Which column of the order board the order sits in.",
    )
    # Columns whose email has already gone out, so dragging a card back and
    # forth does not mail the customer twice.
    mailed_stage_ids = fields.Many2many(
        comodel_name="gelato.delivery.stage",
        relation="gelato_order_mailed_stage_rel",
        column1="order_id",
        column2="stage_id",
        string="Columns already emailed",
        copy=False,
    )
    # The same guard for text messages. Kept apart from the email list,
    # because a column can send one, the other, or both.
    texted_stage_ids = fields.Many2many(
        comodel_name="gelato.delivery.stage",
        relation="gelato_order_texted_stage_rel",
        column1="order_id",
        column2="stage_id",
        string="Columns already texted",
        copy=False,
    )

    # ------------------------------------------------------------------
    # Customer
    # ------------------------------------------------------------------
    customer_name = fields.Char(string="Customer name", required=True, tracking=True)
    customer_phone = fields.Char(string="Phone", required=True, tracking=True)
    customer_email = fields.Char(string="Email", tracking=True)

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------
    delivery_address = fields.Char(
        string="Delivery address",
        required=True,
        help="Street and number, floor, doorbell.",
    )
    delivery_postcode = fields.Char(
        string="Postcode",
        help="Only written down for the driver - the zone is decided by the "
        "address on the map.",
    )
    zone_id = fields.Many2one(
        comodel_name="gelato.delivery.zone",
        string="Zone",
        ondelete="set null",
        help="Which drawn zone the address landed in. Empty means the "
        "address could not be put on the map.",
    )
    latitude = fields.Float(string="Latitude", digits=(10, 7))
    longitude = fields.Float(string="Longitude", digits=(10, 7))
    address_located = fields.Boolean(
        string="Address found on the map",
        help="When this is off the address could not be located, the order "
        "was let through anyway and the fee needs confirming on the phone.",
    )
    delivery_date = fields.Date(string="Delivery date", required=True, tracking=True)
    delivery_time = fields.Selection(
        selection=TIME_SLOTS,
        string="Delivery time",
        default="asap",
        required=True,
    )
    note = fields.Text(
        string="Customer note",
        help="Split between flavours, allergies, gift wrapping and so on.",
    )
    internal_note = fields.Text(string="Internal note")

    # ------------------------------------------------------------------
    # What was ordered
    # ------------------------------------------------------------------
    box_id = fields.Many2one(
        comodel_name="gelato.delivery.box",
        string="Thermal box",
        required=True,
        ondelete="restrict",
    )
    box_price = fields.Float(string="Box price", digits=(10, 2))
    flavor_ids = fields.Many2many(
        comodel_name="gelato.flavor",
        string="Chosen flavours",
    )
    addon_line_ids = fields.One2many(
        comodel_name="gelato.delivery.order.addon",
        inverse_name="order_id",
        string="Extras",
    )

    # ------------------------------------------------------------------
    customer_id = fields.Many2one(
        comodel_name="gelato.customer",
        string="Customer record",
        ondelete="set null",
        index=True,
        help="The one row in Customers this order belongs to. Filled in "
        "automatically from the phone and the email.",
    )

    order_summary = fields.Char(
        string="What was ordered",
        compute="_compute_order_summary",
        store=True,
        help="Box, flavours and extras on one line.",
    )

    # ------------------------------------------------------------------
    # Amounts
    # ------------------------------------------------------------------
    amount_addons = fields.Float(
        string="Extras total",
        compute="_compute_amounts",
        store=True,
        digits=(10, 2),
    )
    amount_subtotal = fields.Float(
        string="Subtotal",
        compute="_compute_amounts",
        store=True,
        digits=(10, 2),
    )
    promo_code_id = fields.Many2one(
        comodel_name="gelato.promo.code",
        string="Promo code",
        ondelete="set null",
    )
    discount_percent = fields.Float(
        string="Discount (%)",
        digits=(5, 2),
        help="Written down when the order is created, so a later change to "
        "the code does not change the price of an old order.",
    )
    amount_discount = fields.Float(
        string="Discount",
        compute="_compute_amounts",
        store=True,
        digits=(10, 2),
    )
    delivery_fee = fields.Float(string="Delivery", digits=(10, 2))
    delivery_vat_rate = fields.Float(
        string="Delivery VAT rate (%)",
        digits=(5, 2),
        help="Written down when the order is created, so a later change to the "
        "setting does not alter an old order.",
    )
    amount_total = fields.Float(
        string="Total",
        compute="_compute_amounts",
        store=True,
        digits=(10, 2),
        tracking=True,
    )
    amount_vat = fields.Float(
        string="VAT",
        compute="_compute_amounts",
        store=True,
        digits=(10, 2),
        help="The VAT already contained in the total - prices are entered "
        "the way the customer sees them.",
    )
    amount_untaxed = fields.Float(
        string="Net of VAT",
        compute="_compute_amounts",
        store=True,
        digits=(10, 2),
    )
    box_vat_rate = fields.Float(
        string="Box VAT rate (%)",
        digits=(5, 2),
        help="Written down when the order is created, so a later change to the "
        "box does not alter an old order.",
    )

    website_id = fields.Many2one(
        comodel_name="website",
        string="Website",
        ondelete="set null",
    )
    source = fields.Selection(
        selection=[("website", "Website"), ("manual", "Entered by hand")],
        string="Source",
        default="manual",
        required=True,
    )

    # ------------------------------------------------------------------
    # Computations
    # ------------------------------------------------------------------
    @api.depends(
        "box_price",
        "box_vat_rate",
        "addon_line_ids.price_subtotal",
        "addon_line_ids.vat_rate",
        "discount_percent",
        "delivery_fee",
        "delivery_vat_rate",
    )
    def _compute_amounts(self):
        """Work out the totals and the VAT hidden inside them.

        Every price in this module is what the customer sees, VAT included -
        that is how prices have to be shown to consumers here. So VAT is not
        added on top, it is extracted from the total.

        The rates differ per item (gelato and alcohol are not taxed the same),
        so the extraction runs per line. A discount lowers every line by the
        same share, which lowers each rate's share of the VAT with it.
        """
        for order in self:
            addons = sum(order.addon_line_ids.mapped("price_subtotal"))
            subtotal = order.box_price + addons
            discount = subtotal * (order.discount_percent or 0.0) / 100.0
            delivery = order.delivery_fee or 0.0
            total = subtotal - discount + delivery

            # what is left of each line after the discount
            remaining = 1.0 - (order.discount_percent or 0.0) / 100.0
            taxed = [(order.box_price * remaining, order.box_vat_rate)]
            for line in order.addon_line_ids:
                taxed.append((line.price_subtotal * remaining, line.vat_rate))
            taxed.append((delivery, order.delivery_vat_rate))

            vat = 0.0
            for gross, rate in taxed:
                if rate:
                    vat += gross * rate / (100.0 + rate)

            order.amount_addons = addons
            order.amount_subtotal = subtotal
            order.amount_discount = discount
            order.amount_total = total
            order.amount_vat = vat
            order.amount_untaxed = total - vat

    def vat_breakdown(self):
        """VAT split by rate, for the email and for the accountant.

        Returns a list of {rate, base, vat, gross}, one row per rate used.
        """
        self.ensure_one()
        remaining = 1.0 - (self.discount_percent or 0.0) / 100.0
        rows = {}
        items = [(self.box_price * remaining, self.box_vat_rate)]
        for line in self.addon_line_ids:
            items.append((line.price_subtotal * remaining, line.vat_rate))
        items.append((self.delivery_fee or 0.0, self.delivery_vat_rate))

        for gross, rate in items:
            if not gross:
                continue
            key = round(rate or 0.0, 2)
            rows.setdefault(key, 0.0)
            rows[key] += gross

        out = []
        for rate in sorted(rows, reverse=True):
            gross = rows[rate]
            vat = gross * rate / (100.0 + rate) if rate else 0.0
            out.append({
                "rate": rate,
                "gross": round(gross, 2),
                "vat": round(vat, 2),
                "base": round(gross - vat, 2),
            })
        return out

    @api.onchange("box_id")
    def _onchange_box_id(self):
        if self.box_id:
            self.box_price = self.box_id.price
            self.box_vat_rate = self.box_id.vat_rate

    @api.onchange("promo_code_id")
    def _onchange_promo_code_id(self):
        self.discount_percent = self.promo_code_id.discount_percent or 0.0

    # ------------------------------------------------------------------
    # The board
    # ------------------------------------------------------------------
    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Show every column on the board, even the empty ones."""
        return self.env["gelato.delivery.stage"].search([])

    @api.model
    def _default_stage(self):
        return self.env["gelato.delivery.stage"].search([], limit=1)

    # ------------------------------------------------------------------
    # Numbering
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "gelato.delivery.order"
                ) or _("New")
        orders = super().create(vals_list)
        orders._link_customer()
        # A new order lands in the first column, which usually means the
        # customer gets their confirmation without anybody doing anything.
        orders._notify_stage()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if "stage_id" in vals:
            self._notify_stage()
        return res

    # ------------------------------------------------------------------
    # The on/off bar above the flavour board
    # ------------------------------------------------------------------
    # The switch and the hours live on the website record, which only an
    # administrator may write. These two run with sudo on purpose: the whole
    # point is that whoever is in the shop can close the delivery without
    # being let into Settings.
    SWITCH_FIELDS = (
        "gelato_delivery_enabled",
        "gelato_order_from",
        "gelato_order_to",
    )

    @api.model
    def gelato_switch_state(self):
        site = self.env["website"].sudo().get_current_website()
        open_now, note = site.gelato_orders_open()
        return {
            "enabled": site.gelato_delivery_enabled,
            "order_from": site.gelato_order_from,
            "order_to": site.gelato_order_to,
            "hours_label": site.gelato_order_hours_label(),
            "open_now": open_now,
            "note": note,
        }

    @api.model
    def gelato_switch_write(self, values):
        site = self.env["website"].sudo().get_current_website()
        # Only the three operational fields, never anything else that happens
        # to sit on the website record.
        site.write({
            key: value
            for key, value in (values or {}).items()
            if key in self.SWITCH_FIELDS
        })
        return self.gelato_switch_state()

    # ------------------------------------------------------------------
    # Email attached to a column
    # ------------------------------------------------------------------
    def _notify_stage(self):
        """Send what the column sends, at most once per column and order."""
        for order in self:
            stage = order.stage_id
            if not stage:
                continue

            if (
                stage.mail_enabled
                and order.customer_email
                and stage not in order.mailed_stage_ids
                and order._send_stage_mail(stage)
            ):
                order.mailed_stage_ids = [(4, stage.id)]

            if (
                stage.sms_enabled
                and order.customer_phone
                and stage not in order.texted_stage_ids
                and order._send_stage_sms(stage)
            ):
                order.texted_stage_ids = [(4, stage.id)]

    def _send_stage_sms(self, stage):
        self.ensure_one()
        try:
            body = self.env["mail.render.mixin"].sudo()._render_template(
                stage.sms_body or "",
                "gelato.delivery.order",
                [self.id],
                engine="inline_template",
            )[self.id]
            if not body.strip():
                return False
            self.env["sms.sms"].sudo().create({
                "body": body,
                "number": self.customer_phone,
            }).send()
            return True
        except Exception as error:
            # A text that will not go out must never block the board.
            _logger.warning(
                "Delivery board: the text message for column %s could not be "
                "sent: %s",
                stage.name,
                error,
            )
            return False

    def _send_stage_mail(self, stage):
        self.ensure_one()
        try:
            render = self.env["mail.render.mixin"].sudo()
            subject = render._render_template(
                stage.mail_subject or "",
                "gelato.delivery.order",
                [self.id],
                engine="inline_template",
            )[self.id]
            body = render._render_template(
                stage.mail_body or "",
                "gelato.delivery.order",
                [self.id],
                engine="inline_template",
            )[self.id]
            self.env["mail.mail"].sudo().create({
                "subject": subject,
                "body_html": body,
                "email_from": (
                    self.website_id.company_id.email_formatted
                    or self.env.company.email_formatted
                    or self.env.user.email_formatted
                ),
                "email_to": self.customer_email,
                "model": "gelato.delivery.order",
                "res_id": self.id,
                "auto_delete": False,
            }).send()
            return True
        except Exception as error:
            # A broken email must never block an order from being taken.
            _logger.warning(
                "Delivery board: the email for column %s could not be sent: %s",
                stage.name,
                error,
            )
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _link_customer(self):
        """Attach every order to its one row in Customers.

        Done here rather than in the controller so an order typed in by hand
        in Odoo builds the contact list too.
        """
        Customer = self.env["gelato.customer"].sudo()
        for order in self:
            if order.customer_id:
                continue
            if not (order.customer_phone or order.customer_email):
                continue
            order.customer_id = Customer.find_or_create(
                order.customer_name,
                order.customer_email,
                order.customer_phone,
            )

    def flavor_names(self):
        """Flavours separated by commas. Used by the email and overviews."""
        self.ensure_one()
        return ", ".join(self.flavor_ids.mapped("name"))

    @api.depends("box_id", "flavor_ids", "addon_line_ids.addon_id",
                 "addon_line_ids.quantity")
    def _compute_order_summary(self):
        """What was ordered, on one line.

        Stored so the board and the list can show it without opening every
        order, and so it can be searched - "who ordered pistachio" is a
        question the shop actually asks.
        """
        for order in self:
            parts = []
            if order.box_id:
                parts.append(order.box_id.name)
            if order.flavor_ids:
                parts.append(order.flavor_names())
            for line in order.addon_line_ids:
                parts.append("%d× %s" % (line.quantity, line.addon_id.name))
            order.order_summary = " · ".join(parts)

    def time_slot_label(self):
        self.ensure_one()
        return dict(
            self._fields["delivery_time"]._description_selection(self.env)
        ).get(self.delivery_time, "")

    def tracking_payload(self):
        """Data for GTM and the Meta Pixel, shaped like a purchase event.

        The item categories are deliberately left untranslated. GA4 and Meta
        group by the literal string, so a translated category would split one
        product line into a separate row per language of the visitor.
        """
        self.ensure_one()
        items = [
            {
                "item_id": f"box-{self.box_id.id}",
                "item_name": self.box_id.name,
                "item_category": "Thermal box",
                "price": round(self.box_price, 2),
                "quantity": 1,
            }
        ]
        for line in self.addon_line_ids:
            items.append(
                {
                    "item_id": f"addon-{line.addon_id.id}",
                    "item_name": line.addon_id.name,
                    "item_category": "Extra",
                    "price": round(line.price_unit, 2),
                    "quantity": line.quantity,
                }
            )
        return {
            "transaction_id": self.name,
            "value": round(self.amount_total, 2),
            "currency": "CZK",
            "shipping": round(self.delivery_fee, 2),
            "discount": round(self.amount_discount, 2),
            "coupon": self.promo_code_id.code or "",
            "items": items,
        }

    def _send_confirmation_email(self):
        """Send the email to the shop. Stays quiet if the template is missing."""
        template = self.env.ref(
            "gelato_delivery.mail_template_delivery_order", raise_if_not_found=False
        )
        if not template:
            return False
        for order in self:
            template.sudo().send_mail(order.id, force_send=False)
        return True


class GelatoDeliveryOrderAddon(models.Model):
    _name = "gelato.delivery.order.addon"
    _description = "Extra on a Delivery Order"
    _order = "id"

    order_id = fields.Many2one(
        comodel_name="gelato.delivery.order",
        string="Order",
        required=True,
        ondelete="cascade",
    )
    addon_id = fields.Many2one(
        comodel_name="gelato.delivery.addon",
        string="Extra",
        required=True,
        ondelete="restrict",
    )
    quantity = fields.Integer(string="Quantity", default=1, required=True)
    price_unit = fields.Float(string="Unit price", digits=(10, 2))
    vat_rate = fields.Float(
        string="VAT rate (%)",
        digits=(5, 2),
        help="Copied from the extra when the order is created, so a later "
        "change to the rate does not alter an old order.",
    )
    price_subtotal = fields.Float(
        string="Total",
        compute="_compute_price_subtotal",
        store=True,
        digits=(10, 2),
    )

    @api.depends("quantity", "price_unit")
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

    @api.onchange("addon_id")
    def _onchange_addon_id(self):
        if self.addon_id:
            self.price_unit = self.addon_id.price
            self.vat_rate = self.addon_id.vat_rate
