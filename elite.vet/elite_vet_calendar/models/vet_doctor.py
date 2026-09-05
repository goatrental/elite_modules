from odoo import fields, models


class VetDoctor(models.Model):
    """Seznam lekarek pro vyber pri zadavani smeny.

    Vlastni model schvalne, ne res.partner: v nabidce maji byt jen lekarky
    kliniky, ne vsechny kontakty ze systemu.
    """

    _name = "elite.vet.doctor"
    _description = "Lékařka"
    _order = "name"

    name = fields.Char(string="Jméno", required=True)
    active = fields.Boolean(string="Aktivní", default=True)
