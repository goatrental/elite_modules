import logging

_logger = logging.getLogger(__name__)

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
    _priradit_k_webu(env, "elite_vet_calendar.rozpis_lekaru_page")
    _uklidit_cizi_polozky_menu(env, "/rozpis-lekaru")
    _zalozit_polozku_menu(env, "Rozpis služeb", "/rozpis-lekaru")


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


def _zvol_web(env):
    """Vybere web, kteremu stranka patri.

    V databazi bezi vic webu vedle sebe (Elite Vet, Elite Arena, trafika,
    Jack, IMI). Stranka bez prirazeneho webu se v Odoo zobrazi na VSECH
    domenach, coz je presne to, co nechceme.

    Poradi hledani: domena obsahujici elite-vet, pak cokoli s "vet"
    v nazvu nebo domene, jinak jediny existujici web. Kdyz nic nesedi,
    vrati prvni a zapise to do logu - administrator to pak prepise
    v Web -> Konfigurace -> Stranky.
    """
    weby = env["website"].search([])
    if not weby:
        return False
    if len(weby) == 1:
        return weby

    for web in weby:
        if "elite-vet" in (web.domain or "").lower():
            return web
    for web in weby:
        popis = ((web.name or "") + " " + (web.domain or "")).lower()
        if "vet" in popis and "arena" not in popis:
            return web

    _logger.warning(
        "Nepodarilo se poznat, ktery web je Elite Vet. Stranka byla prirazena "
        "k webu '%s'. Zmenit ji jde v Web -> Konfigurace -> Stranky.",
        weby[0].name,
    )
    return weby[0]


def _priradit_k_webu(env, xml_id_stranky, xml_id_menu=None):
    """Priradi stranku (a volitelne polozku menu) ke konkretnimu webu.

    Bez toho je stranka spolecna pro vsechny weby v databazi a objevi se
    i na domenach, kam nepatri.
    """
    web = _zvol_web(env)
    if not web:
        return

    stranka = env.ref(xml_id_stranky, raise_if_not_found=False)
    if stranka:
        stranka.website_id = web.id

    if xml_id_menu:
        polozka = env.ref(xml_id_menu, raise_if_not_found=False)
        if polozka:
            polozka.website_id = web.id
            if web.menu_id:
                polozka.parent_id = web.menu_id.id

    _logger.info("Stranka %s prirazena k webu '%s'.", xml_id_stranky, web.name)


def _zalozit_polozku_menu(env, nazev, url):
    """Zalozi polozku v menu jednoho webu.

    Zamerne se to nedela XML zaznamem. Polozka bez prirazeneho webu je
    "obecna" a Odoo ji samo rozkopiruje do menu vsech webu v databazi -
    takze by odkaz na rozpis visel i na Arene, trafice a dalsich. Dodatecne
    nastaveni website_id uz kopie neodstrani.
    """
    web = _zvol_web(env)
    if not web or not web.menu_id:
        return

    Menu = env["website.menu"]
    if Menu.search_count([("url", "=", url), ("website_id", "=", web.id)]):
        return

    Menu.create({
        "name": nazev,
        "url": url,
        "parent_id": web.menu_id.id,
        "website_id": web.id,
        "sequence": 50,
    })
    _logger.info("Polozka menu %s zalozena na webu '%s'.", url, web.name)


def _uklidit_cizi_polozky_menu(env, url):
    """Smaze odkaz z menu webu, kam nepatri.

    Resi databaze, kde uz modul bezel a obecna polozka se stihla rozkopirovat
    do vsech webu.
    """
    web = _zvol_web(env)
    if not web:
        return
    cizi = env["website.menu"].search([("url", "=", url), ("website_id", "!=", web.id)])
    if cizi:
        _logger.info("Mazu %s polozek menu %s z cizich webu.", len(cizi), url)
        cizi.unlink()
