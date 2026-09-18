from odoo import fields, models


class GelatoImageFrame(models.AbstractModel):
    """How a product photo sits in its frame on the website.

    Every card has the same frame so the rows line up, but photos do not
    all have the same shape. A square photo of a thermal box fills it
    nicely; a tall bottle of prosecco filled the same way gets its neck
    and its base cut off. Rather than making the shop crop pictures
    before uploading them, these two settings say what to do with what
    they have.
    """

    _name = "gelato.image.frame"
    _description = "Photo framing on the website"

    image_fit = fields.Selection(
        selection=[
            ("cover", "Fill the frame (crops the edges)"),
            ("contain", "Whole photo (leaves space around it)"),
        ],
        string="Photo in the frame",
        default="cover",
        required=True,
        help="Fill the frame looks best for a photo shot square. Choose "
        "the whole photo for a tall bottle or anything that must not be "
        "cut off.",
    )
    image_focus = fields.Selection(
        selection=[
            ("top", "Top"),
            ("center", "Middle"),
            ("bottom", "Bottom"),
        ],
        string="Keep in view",
        default="center",
        required=True,
        help="Which part of the photo to keep when the frame crops it. "
        "Has no effect when the whole photo is shown.",
    )

    def image_style(self):
        """The inline style for the <img> on the card."""
        self.ensure_one()
        return "object-fit: %s; object-position: center %s;" % (
            self.image_fit or "cover",
            self.image_focus or "center",
        )
