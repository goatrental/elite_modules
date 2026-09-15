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
    _nastav_homepage(env)
    _seed_sluzby(env)
    seed_galerie(env)
    seed_obsah(env)


def _nastav_homepage(env):
    """Prepne domovskou stranku Odoo na sablonu tohohle modulu.

    Nejde to udelat zaznamem v XML: `website.homepage_page` je v modulu website
    oznacena jako noupdate, takze ji cizi modul prepsat nesmi. A zalozit vlastni
    stranku na "/" taky ne — dve stranky na stejne adrese znamenaji, ze obsluha
    "/" sahne po te spatne a misto homepage presmeruje na prvni polozku menu.

    Zamerne saha JEN na obecnou stranku Odoo. Databaze muze hostit vic webu a
    prepnout homepage vsem by znamenalo prepsat cizi weby. Kdyz web pouziva
    vlastni stranku "/", prepoji se na tuhle sablonu rucne.
    """
    stranka = env.ref('website.homepage_page', raise_if_not_found=False)
    sablona = env.ref('elite_vet_web.homepage', raise_if_not_found=False)
    if not stranka or not sablona:
        return
    # Zamerne se nemeni 'name': website.page pri prejmenovani prepise i klic
    # pohledu, takze by sablona modulu prestala mit svuj vlastni klic.
    stranka.write({
        'view_id': sablona.id,
        'is_published': True,
        'website_indexed': True,
    })
