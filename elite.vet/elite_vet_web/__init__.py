import logging

_logger = logging.getLogger(__name__)

from . import models


# Sluzby, se kterymi klinika startuje. Zaklada se jen pri prvni instalaci —
# od te chvile patri klinice a upgrade modulu do nich uz nesaha.
# Zdroj je anglicky, cestina a dalsi jazyky se dopisuji jako preklad; kdyby se
# zakladalo cesky, anglicky preklad by prepsal zdroj a cestina by ho zdedila.
VYCHOZI_SLUZBY = [
    {
        "kod": "prevence",
        "poradi": 10,
        "en": ("Preventive care",
               "Regular check-ups, vaccinations and deworming. Prevention is the foundation of your pet's health."),
        "cs": ("Preventivní péče",
               "Pravidelné prohlídky, vakcinace a odčervení. Prevence je základ zdraví vašeho mazlíčka."),
        "de": ("Präventivpflege",
               "Regelmäßige Untersuchungen, Impfungen und Entwurmung. Vorsorge ist die Grundlage der Gesundheit Ihres Tieres."),
        "ru": ("Профилактический уход",
               "Регулярные осмотры, вакцинация и дегельминтизация. Профилактика — основа здоровья вашего питомца."),
    },
    {
        "kod": "chirurgie",
        "poradi": 20,
        "en": ("Surgery",
               "Neutering and abdominal procedures. A modern operating theatre with anaesthesia monitoring."),
        "cs": ("Chirurgie",
               "Kastrační a abdominální zákroky. Moderní operační sál s anesteziologickým monitoringem."),
        "de": ("Chirurgie",
               "Kastrationen und abdominale Eingriffe. Moderner Operationssaal mit Anästhesie-Monitoring."),
        "ru": ("Хирургия",
               "Кастрация и абдоминальные вмешательства. Современная операционная с анестезиологическим мониторингом."),
    },
    {
        "kod": "interni",
        "poradi": 30,
        "en": ("Internal medicine",
               "Diagnosis and treatment of internal diseases, cardiology, endocrinology and gastroenterology."),
        "cs": ("Interní medicína",
               "Diagnostika a léčba vnitřních onemocnění, kardiologie, endokrinologie a gastroenterologie."),
        "de": ("Innere Medizin",
               "Diagnose und Behandlung innerer Erkrankungen, Kardiologie, Endokrinologie und Gastroenterologie."),
        "ru": ("Внутренние болезни",
               "Диагностика и лечение внутренних заболеваний, кардиология, эндокринология и гастроэнтерология."),
    },
    {
        "kod": "diagnostika",
        "poradi": 40,
        "en": ("Diagnostics",
               "RTG, ultrasound, laboratory blood and urine tests. Fast and accurate diagnostics for proper treatment.​"),
        "cs": ("Diagnostika",
               "RTG, ultrazvuk, laboratorní vyšetření krve a moči. Rychlá a přesná diagnostika pro správnou léčbu.​"),
        "de": ("Diagnostik",
               "Röntgen, Ultraschall, Labortests von Blut und Urin. Schnelle und genaue Diagnostik für die richtige Behandlung.​"),
        "ru": ("Диагностика",
               "Рентген, УЗИ, лабораторные анализы крови и мочи. Быстрая и точная диагностика для правильного лечения.​"),
    },
    {
        "kod": "stomatologie",
        "poradi": 50,
        "en": ("Dentistry",
               "Dental treatment, extractions, ultrasonic cleaning. Oral care for your pet's healthy teeth."),
        "cs": ("Stomatologie",
               "Ošetření zubů, extrakce, ultrazvukové čištění. Péče o dutinu ústní pro zdravý chrup vašeho mazlíčka."),
        "de": ("Zahnheilkunde",
               "Zahnbehandlung, Extraktionen, Ultraschallreinigung. Mundpflege für gesunde Zähne Ihres Tieres."),
        "ru": ("Стоматология",
               "Лечение зубов, удаления, ультразвуковая чистка. Уход за полостью рта для здоровых зубов вашего питомца."),
    },
    {
        "kod": "oftalmologie",
        "poradi": 60,
        "en": ("Ophthalmology",
               "Examination and treatment of eye diseases in small animals, including diagnostics and surgical procedures."),
        "cs": ("Oftalmologie",
               "Vyšetření a léčba očních onemocnění u malých zvířat, včetně diagnostiky a chirurgických zákroků."),
        "de": ("Ophthalmologie",
               "Untersuchung und Behandlung von Augenerkrankungen bei Kleintieren, einschließlich Diagnostik und chirurgischer Eingriffe."),
        "ru": ("Офтальмология",
               "Обследование и лечение глазных заболеваний у мелких животных, включая диагностику и хирургические вмешательства."),
    },
    {
        "kod": "dermatologie",
        "poradi": 70,
        "en": ("Dermatology",
               "Treatment of skin problems, allergies and parasitic diseases. Comprehensive care for skin and coat."),
        "cs": ("Dermatologie",
               "Léčba kožních problémů, alergií a parazitárních onemocnění. Komplexní péče o kůži a srst."),
        "de": ("Dermatologie",
               "Behandlung von Hautproblemen, Allergien und Parasitenerkrankungen. Umfassende Pflege von Haut und Fell."),
        "ru": ("Дерматология",
               "Лечение кожных проблем, аллергий и паразитарных заболеваний. Комплексный уход за кожей и шерстью."),
    },
    {
        "kod": "ultrazvuk",
        "poradi": 80,
        "en": ("Ultrasonography and sonological diagnostics",
               "We have doctors specialising in ultrasound diagnostics. We are developing this area further, including towards cardiology examinations."),
        "cs": ("Ultrasonografie a sonologická diagnostika",
               "Máme lékaře odborně zaměřené na ultrazvukovou diagnostiku. Tuto oblast dále rozvíjíme, a to i směrem ke kardiologickým vyšetřením."),
        "de": ("Ultrasonografie und sonologische Diagnostik",
               "Wir haben Ärzte mit Spezialisierung auf Ultraschalldiagnostik. Diesen Bereich bauen wir weiter aus, auch in Richtung kardiologischer Untersuchungen."),
        "ru": ("Ультрасонография и сонологическая диагностика",
               "У нас есть врачи, специализирующиеся на ультразвуковой диагностике. Мы развиваем это направление дальше, в том числе в сторону кардиологических исследований."),
    },
]


def _seed_sluzby(env):
    """Zalozi vychozi sluzby. Jen pri prvni instalaci — pak uz patri klinice."""
    Sluzba = env["elite.vet.service"]
    if Sluzba.search_count([]):
        return
    for radek in VYCHOZI_SLUZBY:
        nazev, popis = radek["en"]
        zaznam = Sluzba.create({
            "name": nazev,
            "description": popis,
            "sequence": radek["poradi"],
            "icon_code": radek["kod"],
        })
        for jazyk, klic in (("cs_CZ", "cs"), ("de_DE", "de"), ("ru_RU", "ru")):
            nazev_p, popis_p = radek[klic]
            if nazev_p:
                zaznam.with_context(lang=jazyk).name = nazev_p
            if popis_p:
                zaznam.with_context(lang=jazyk).description = popis_p


def _pri_instalaci(env):
    """Vse, co se ma stat po prvni instalaci modulu."""
    from .models.seed import seed_galerie, seed_obsah
    _priradit_stranky_k_webu(env)
    _nastav_homepage(env)
    _nastav_seo(env)
    _seed_sluzby(env)
    seed_galerie(env)
    seed_obsah(env)


def _priradit_stranky_k_webu(env):
    """Prisije stranky modulu k webu Elite Vet.

    Stranka bez prirazeneho webu je v Odoo "obecna" a vykresli se na VSECH
    domenach v databazi. Ta hostuje i Elite Arenu, trafiku, Jacka a IMI —
    a na tech by cenik ani rezervace veterinarni kliniky nemely co delat.
    Uz jednou se to stalo, proto se to deje automaticky a ne rucne.
    """
    from odoo.addons.elite_vet_calendar import _priradit_k_webu
    for xml_id in ("elite_vet_web.rezervace_page", "elite_vet_web.cenik_page"):
        _priradit_k_webu(env, xml_id)


def _nastav_homepage(env):
    """Prepne domovskou stranku na sablonu tohohle modulu.

    Nejde to udelat zaznamem v XML: `website.homepage_page` je v modulu website
    oznacena jako noupdate, takze ji cizi modul prepsat nesmi.

    Poradi je schvalne opatrne, protoze obecna stranka "/" patri vsem webum
    v databazi:

    1. Kdyz ma web Elite Vet vlastni stranku na "/", prepne se jen ta.
    2. Kdyz je v databazi jediny web, je obecna stranka jeho a prepne se.
    3. Kdyz je webu vic a Elite Vet vlastni "/" nema, NEPREPNE se nic. Prepsat
       obecnou stranku by znamenalo hodit veterinarni homepage i Arene
       a trafice. Zapise se to do logu a dodela se rucne podle nasazeni/README.

    Vlastni stranka na "/" se zamerne nezaklada. Dve stranky na stejne adrese
    znamenaji, ze si obsluha "/" vybere tu spatnou a misto homepage presmeruje
    na prvni polozku menu.
    """
    from odoo.addons.elite_vet_calendar import _zvol_web

    sablona = env.ref('elite_vet_web.homepage', raise_if_not_found=False)
    if not sablona:
        return

    # Zamerne se nemeni 'name': website.page pri prejmenovani prepise i klic
    # pohledu, takze by sablona modulu prestala mit svuj vlastni klic.
    zmena = {
        'view_id': sablona.id,
        'is_published': True,
        'website_indexed': True,
    }

    web = _zvol_web(env)
    if web:
        vlastni = env['website.page'].search(
            [('url', '=', '/'), ('website_id', '=', web.id)], limit=1)
        if vlastni:
            vlastni.write(zmena)
            _logger.info("Homepage webu '%s' prepnuta na sablonu modulu.", web.name)
            return

    if env['website'].search_count([]) <= 1:
        obecna = env.ref('website.homepage_page', raise_if_not_found=False)
        if obecna:
            obecna.write(zmena)
            _logger.info("Obecna homepage prepnuta na sablonu modulu.")
        return

    _logger.warning(
        "Homepage se neprepnula. V databazi je vic webu a Elite Vet nema vlastni "
        "stranku na '/'. Prepsat obecnou stranku by zmenilo homepage i ostatnim "
        "webum, takze to necham na cloveku: Nastaveni -> Technicke -> Web -> "
        "Stranky, najit '/' webu Elite Vet a v poli Zobrazeni vybrat "
        "elite_vet_web.homepage.")


def _nastav_seo(env):
    """Zapise SEO titulek a popis na zaznamy stranek, ve vsech ctyrech jazycich.

    Odoo bere meta popis z pole `website_meta_description` na zaznamu stranky,
    ne z `<t t-set="meta_description">` v sablone — ten tise ignoruje. Stranky
    proto zadny popis do vyhledavacu nemely, ani cesky.

    Texty se neberou z hlavy: jsou to tytez vety, ktere uz v sablonach jsou,
    i s preklady z i18n/*.po. Vytazene jsou v data/seo.json.

    Vyplnene pole se nikdy neprepisuje — co si klinika napsala, zustane.
    """
    import json
    import os

    cesta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "seo.json")
    if not os.path.exists(cesta):
        _logger.warning("SEO: soubor %s nenalezen, preskakuji.", cesta)
        return
    with open(cesta, encoding="utf-8") as soubor:
        stranky = json.load(soubor)

    # en_US je zdroj, ne jeden z jazyku: zapisuje se prvni, jinak by ostatni
    # jazyky bez vlastniho prekladu zdedily to, co se do nej napsalo naposled.
    PORADI = ["en_US", "cs_CZ", "de_DE", "ru_RU"]
    zapsano = 0
    for radek in stranky:
        stranka = env.ref(radek["stranka"], raise_if_not_found=False)
        if not stranka:
            continue
        for pole, hodnoty in (("website_meta_title", radek.get("title") or {}),
                              ("website_meta_description", radek.get("description") or {})):
            if (stranka[pole] or "").strip():
                continue                      # klinika uz si to vyplnila
            for jazyk in PORADI:
                text = hodnoty.get(jazyk)
                if text:
                    stranka.with_context(lang=jazyk)[pole] = text
            zapsano += 1
    _logger.info("SEO: doplneno %s hodnot na strankach.", zapsano)
