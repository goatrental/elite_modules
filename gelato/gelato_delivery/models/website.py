from odoo import _, fields, models


class Website(models.Model):
    """Delivery settings belong to one specific website.

    A single database can host several websites. If these values lived in
    ir.config_parameter they would leak between them and the Gelato delivery
    would show up where it does not belong.
    """

    _inherit = "website"

    gelato_delivery_enabled = fields.Boolean(
        string="Delivery is running",
        default=True,
        help="When switched off, the /rozvoz page stays but shows a notice "
        "instead of the order form.",
    )
    gelato_delivery_site = fields.Boolean(
        string="Delivery lives on this website",
        default=False,
        help="Only the website with this ticked serves the /rozvoz page. "
        "One database can host several websites and the gelateria's delivery "
        "has no business appearing on somebody else's site.",
    )
    gelato_order_from = fields.Float(
        string="Orders from",
        default=11.0,
        help="Before this hour the website does not take orders. "
        "Set both hours to 0 to accept orders around the clock.",
    )
    gelato_order_to = fields.Float(
        string="Orders until",
        default=19.0,
        help="After this hour the website does not take orders.",
    )
    gelato_delivery_email = fields.Char(
        string="Email for orders",
        default="gelatokv@seznam.cz",
        help="Where new delivery orders are sent.",
    )
    gelato_delivery_fee = fields.Float(
        string="Delivery fee",
        digits=(10, 2),
        default=79.0,
    )
    gelato_delivery_free_from = fields.Float(
        string="Free delivery from",
        digits=(10, 2),
        default=800.0,
        help="Orders above this amount are delivered for free. "
        "0 means delivery is always free.",
    )
    gelato_delivery_fee_base = fields.Selection(
        selection=[
            ("before_discount", "On the price before the discount"),
            ("after_discount", "On the price after the discount"),
        ],
        string="Apply the free delivery threshold",
        default="before_discount",
        required=True,
        help="Decides whether a promo code can push an order below the free "
        "delivery threshold. “Before the discount” is the friendlier option: "
        "someone who orders above the threshold keeps free delivery even "
        "after applying a code.",
    )
    gelato_delivery_fee_vat_rate = fields.Float(
        string="Delivery VAT rate (%)",
        digits=(5, 2),
        default=21.0,
        help="The rate contained in the delivery fee. Enter 0 if you are not "
        "registered for VAT.",
    )
    gelato_delivery_min_days = fields.Integer(
        string="Earliest slot (days ahead)",
        default=0,
        help="0 means customers can order for today.",
    )
    gelato_delivery_promo_note = fields.Char(
        string="Note above the promo code field",
        translate=True,
        help="For example “Got a code from Instagram? Enter it here.” "
        "An empty field hides the note.",
    )

    def gelato_delivery_fee_for(self, subtotal, discount=0.0):
        """Work out the delivery fee.

        `subtotal` is the price of the goods before the discount and
        `discount` is the discount in CZK. Depending on the setting, the free
        delivery threshold is compared either against the price before the
        discount or against what the customer actually pays.
        """
        self.ensure_one()
        if not self.gelato_delivery_fee:
            return 0.0
        if not self.gelato_delivery_free_from:
            return self.gelato_delivery_fee

        base = subtotal
        if self.gelato_delivery_fee_base == "after_discount":
            base = subtotal - discount

        if base >= self.gelato_delivery_free_from:
            return 0.0
        return self.gelato_delivery_fee

    # ------------------------------------------------------------------
    # Ordering hours
    # ------------------------------------------------------------------
    def gelato_order_hours_label(self):
        """The hours as "11:00 - 19:00", or empty when they are switched off."""
        self.ensure_one()
        if not self._gelato_hours_set():
            return ""
        return "%s - %s" % (
            self._gelato_format_hour(self.gelato_order_from),
            self._gelato_format_hour(self.gelato_order_to),
        )

    def gelato_orders_open(self):
        """Is the website taking orders at this moment?

        Two things can close it: the switch in the settings, and the clock.
        Returns (open, reason) where the reason is already a sentence for the
        customer - empty when we are open.
        """
        self.ensure_one()
        if not self.gelato_delivery_enabled:
            return False, ""

        if not self._gelato_hours_set():
            return True, ""

        now = self._gelato_local_now()
        current = now.hour + now.minute / 60.0
        start = self.gelato_order_from
        end = self.gelato_order_to

        # An end before the start means the window runs over midnight,
        # for example 18:00-02:00.
        if start <= end:
            is_open = start <= current < end
        else:
            is_open = current >= start or current < end

        if is_open:
            return True, ""
        return False, _(
            "We take orders between %(from)s and %(to)s.",
            **{
                "from": self._gelato_format_hour(start),
                "to": self._gelato_format_hour(end),
            },
        )

    def _gelato_hours_set(self):
        """Both hours at zero means the check is off."""
        self.ensure_one()
        return bool(self.gelato_order_from or self.gelato_order_to)

    def _gelato_local_now(self):
        """Now, in the shop's own timezone.

        The public visitor has no timezone of their own, so the company's is
        what decides whether the gelateria is open.
        """
        self.ensure_one()
        tz = self.company_id.partner_id.tz or "Europe/Prague"
        return fields.Datetime.context_timestamp(
            self.with_context(tz=tz), fields.Datetime.now()
        )

    @staticmethod
    def _gelato_format_hour(value):
        hours = int(value)
        minutes = int(round((value - hours) * 60))
        return "%d:%02d" % (hours, minutes)
