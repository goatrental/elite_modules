from . import models


def _seed_defaults(env):
    """Zaklada vychozi typy smen a jmena lekarek pri prvni instalaci.

    Zamerne se to nedela pres XML zaznamy v data/. XML zaznam ma svoje
    ir.model.data id, takze kdyz ho klinika v Odoo smaze, upgrade modulu ho
    zalozi znovu. Takhle vzniknou zaznamy jen jednou a od te chvile patri
    klinice - co smaze, to je smazane.
    """
    _seed_shift_types(env)
    _seed_doctors(env)


def _seed_shift_types(env):
    Type = env["elite.vet.shift.type"]
    if Type.search_count([]):
        return
    Type.create([
        {"name": "Ranní služba",     "sequence": 10, "time_from": 8.0,  "time_to": 14.0, "color": "green"},
        {"name": "Odpolední služba", "sequence": 20, "time_from": 14.0, "time_to": 20.0, "color": "orange"},
        {"name": "Noční služba",     "sequence": 30, "time_from": 20.0, "time_to": 8.0,  "color": "purple"},
        {"name": "Víkendová služba", "sequence": 40, "time_from": 10.0, "time_to": 18.0, "color": "pink"},
        {"name": "Zavřeno",          "sequence": 90, "color": "red", "is_note": True},
    ])


def _seed_doctors(env):
    Doctor = env["elite.vet.doctor"]
    if Doctor.search_count([]):
        return
    Doctor.create([
        {"name": "MVDr. Dominika Pražáková"},
        {"name": "MVDr. Sandra Mrázová"},
        {"name": "MVDr. Kateřina Kadavá"},
        {"name": "MVDr. Georgiana Chihaia"},
        {"name": "Silvie Tranta, DiS."},
        {"name": "Nikola Hejdová"},
        {"name": "Bc. Michala Dvořáková Szmigielská"},
        {"name": "Lucie Svobodová"},
    ])
