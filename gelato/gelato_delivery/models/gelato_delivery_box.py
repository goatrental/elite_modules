from odoo import _, fields, models


class GelatoDeliveryBox(models.Model):
    _name = "gelato.delivery.box"
    _description = "Thermal Box"
    _order = "sequence, price"

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
        help="Shown on the card on the website, for example “1 l”.",
    )
    subtitle = fields.Char(
        string="Subtitle",
        translate=True,
        help="The line under the name, for example “about 8 servings”.",
    )
    price = fields.Float(
        string="Price",
        required=True,
        digits=(10, 2),
    )
    vat_rate = fields.Float(
        string="VAT rate (%)",
        default=12.0,
        digits=(5, 2),
        help="The rate contained in the price above. Prices are entered the way "
        "the customer sees them, VAT included. In the Czech Republic food is "
        "usually 12%, other goods and services 21%. Enter 0 if you are not "
        "registered for VAT.",
    )
    volume_l = fields.Float(
        string="Volume (l)",
        digits=(5, 2),
        help="For your reference in Odoo only.",
    )
    portions = fields.Integer(
        string="Servings",
        help="For your reference in Odoo only.",
    )
    max_flavors = fields.Integer(
        string="Max. flavours",
        default=0,
        help="How many flavours the customer may pick for this box. "
        "0 means no limit.",
    )
    features = fields.Text(
        string="Bullet points on the card",
        translate=True,
        help="One bullet per line. Shown on the box card on the website.",
    )
    highlight = fields.Boolean(
        string="Highlight the card",
        help="The card gets a coloured border and a badge.",
    )
    highlight_label = fields.Char(
        string="Badge text",
        translate=True,
        default="Most popular",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )

    def flavor_limit_label(self):
        """How many flavours fit in the box, as a line for the website.

        Three separate strings on purpose. Odoo keeps one translation per
        source string, but Czech needs three number forms - "1 příchuť",
        "2 příchutě", "5 příchutí" - so the form has to be picked here and
        each one translated on its own.
        """
        self.ensure_one()
        count = self.max_flavors
        if count <= 0:
            return _("any number of flavours")
        if count == 1:
            return _("1 flavour")
        if count < 5:
            return _("up to %s flavours", count)
        return _("up to %s different flavours", count)

    def feature_list(self):
        """Bullet points split into lines. Called by the QWeb template."""
        self.ensure_one()
        if not self.features:
            return []
        return [line.strip() for line in self.features.splitlines() if line.strip()]
