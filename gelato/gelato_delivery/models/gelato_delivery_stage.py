from odoo import fields, models


class GelatoDeliveryStage(models.Model):
    """A column on the order board, plus the email that column sends.

    The columns are data, not code: the shop adds, renames and reorders them
    in Odoo. Each one can carry an email that goes to the customer the moment
    an order is dragged into it - that is how "we are on our way" gets sent
    without anybody writing it.
    """

    _name = "gelato.delivery.stage"
    _description = "Order Stage"
    _order = "sequence, id"

    name = fields.Char(
        string="Column name",
        required=True,
        translate=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    fold = fields.Boolean(
        string="Folded on the board",
        help="The column shows collapsed. Handy for end states like Cancelled.",
    )
    is_done = fields.Boolean(
        string="Counts as completed",
        help="Orders in this column are treated as finished. Use it for the "
        "last column, typically Delivered.",
    )

    # ------------------------------------------------------------------
    # Email sent when an order enters this column
    # ------------------------------------------------------------------
    mail_enabled = fields.Boolean(
        string="Email the customer",
        help="When an order is dragged into this column, the customer gets "
        "the email below. Leave it off for columns that are only your own "
        "internal step.",
    )
    mail_subject = fields.Char(
        string="Email subject",
        translate=True,
        help="You can use {{ object.name }} for the order number.",
    )
    mail_body = fields.Html(
        string="Email body",
        translate=True,
        sanitize=False,
        help="Placeholders: {{ object.customer_name }} the customer's name, "
        "{{ object.name }} the order number, "
        "{{ object.delivery_address }} the address.",
    )

    # ------------------------------------------------------------------
    # Text message sent when an order enters this column
    # ------------------------------------------------------------------
    sms_enabled = fields.Boolean(
        string="Text the customer",
        help="When an order is dragged into this column, the customer gets "
        "the text message below. Texts cost money with your SMS provider, so "
        "this is usually worth it only for “on the way”.",
    )
    sms_body = fields.Text(
        string="Text message",
        translate=True,
        help="Keep it under 160 characters, otherwise the provider charges "
        "for two messages. Placeholders: {{ object.customer_name }} the "
        "customer's name, {{ object.name }} the order number, "
        "{{ object.delivery_address }} the address.",
    )
