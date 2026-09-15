"""Projde cely web krok za krokem a overi, ze to, co se zada v adminu,
se opravdu projevi na strance.

Nejde o cteni kodu, ale o skutecnou zkousku: skript zaznam zalozi, stahne
stranku, podiva se, jestli tam je, a pak ho zase smaze. Co po sobe zmeni,
to vraci zpatky.

Pousti se v kontejneru s Odoo:

    docker exec -i <kontejner> odoo shell -c /etc/odoo/odoo.conf -d <databaze> \
        --no-http < nasazeni/test-vseho.py
"""

import urllib.request

ZAKLAD = "http://localhost:8069"
JAZYKY = [("cs", "", "cs-CZ,cs", "cs-CZ"), ("de", "/de", "de-DE,de", "de-DE"),
          ("en", "/en", "en-US,en", "en-US"), ("ru", "/ru", "ru-RU,ru", "ru-RU")]
STRANKY = ["/", "/rezervacni-system", "/cenik", "/rozpis-lekaru", "/nas-tym"]

vysledky = []


def krok(nazev, podminka, detail=""):
    vysledky.append((bool(podminka), nazev, detail))
    print("%s  %s%s" % ("OK  " if podminka else "CHYBA", nazev,
                        ("  — " + detail) if detail and not podminka else ""))


def stahni(cesta, hlavicka="cs-CZ,cs"):
    zadost = urllib.request.Request(ZAKLAD + cesta, headers={
        "Accept-Language": hlavicka, "Accept": "text/html"})
    with urllib.request.urlopen(zadost, timeout=30) as odpoved:
        return odpoved.read().decode("utf-8", "replace")


print("\n===== 1. STRANKY A JAZYKY =====")
for stranka in STRANKY:
    for kod, predpona, hlavicka, ocekavany in JAZYKY:
        cesta = predpona + (stranka if stranka != "/" else "/")
        try:
            html = stahni(cesta, hlavicka)
            jazyk = html.split('<html', 1)[1].split('lang="', 1)[1].split('"', 1)[0]
            krok("%-20s %s" % (stranka, kod), jazyk == ocekavany, "vratilo jazyk " + jazyk)
        except Exception as chyba:
            krok("%-20s %s" % (stranka, kod), False, str(chyba)[:60])

print("\n===== 2. ADMIN =====")
APLIKACE = {
    "Hlavní stránka": ["elite.vet.page.section", "elite.vet.service", "elite.vet.species",
                       "elite.vet.gallery.photo", "elite.vet.opening.hours",
                       "elite.vet.contact"],
    "Nastavení kontaktu": ["elite.vet.setting"],
    "Rozpis služeb": ["elite.vet.shift", "elite.vet.doctor", "elite.vet.shift.type",
                      "elite.vet.team.specialization", "elite.vet.team.icon"],
    "Náš tým": ["elite.vet.team.member", "elite.vet.team.section",
                "elite.vet.team.fact.label"],
    "Ceník": ["elite.vet.price.item", "elite.vet.price.category"],
    "Rezervace": ["elite.vet.setting", "elite.vet.faq"],
}
Menu = env["ir.ui.menu"].with_context(lang="cs_CZ")
for aplikace, modely in APLIKACE.items():
    koren = Menu.search([("parent_id", "=", False), ("name", "=", aplikace)], limit=1)
    if not koren:
        krok("aplikace %s" % aplikace, False, "v nabidce neni")
        continue
    deti = Menu.search([("parent_id", "child_of", koren.id), ("id", "!=", koren.id)])
    nalezene = set()
    for d in deti:
        if not d.action:
            continue
        # okenni akce nese model v res_model, serverova (Nastaveni webu) v model_id
        model = getattr(d.action, "res_model", None)
        if not model and getattr(d.action, "model_id", None):
            model = d.action.model_id.model
        if model:
            nalezene.add(model)
    chybi = [m for m in modely if m not in nalezene]
    krok("aplikace %-14s (%s polozek)" % (aplikace, len(deti)), not chybi,
         "chybi " + ", ".join(chybi))

print("\n===== 3. SLUZBY =====")
Sluzba = env["elite.vet.service"]
pred = Sluzba.search_count([])
nova = Sluzba.create({"name": "ZKOUSKA sluzba", "description": "Docasny zaznam z testu",
                      "icon_code": "prevence", "sequence": 999})
env.cr.commit()
html = stahni("/")
krok("pridana sluzba je na strance", "ZKOUSKA sluzba" in html)
krok("sluzba je v mrizce i v mobilnim seznamu", html.count("ZKOUSKA sluzba") >= 2,
     "nalezeno %sx" % html.count("ZKOUSKA sluzba"))
nova.active = False
env.cr.commit()
krok("vypnuta sluzba ze stranky zmizi", "ZKOUSKA sluzba" not in stahni("/"))
nova.unlink()
env.cr.commit()
krok("po smazani zustal puvodni pocet", Sluzba.search_count([]) == pred)

print("\n===== 4. GALERIE =====")
Foto = env["elite.vet.gallery.photo"]
pocet_fotek = Foto.search_count([])
vzor = Foto.search([], limit=1)
strany_pred = (pocet_fotek + 2) // 3
nova_fotka = Foto.create({"name": "ZKOUSKA fotka", "image": vzor.image, "sequence": 999})
env.cr.commit()
html = stahni("/")
strany_po = (pocet_fotek + 1 + 2) // 3
krok("fotka pribyla do pasu", html.count('class="ev-gal-item"') == pocet_fotek + 1,
     "v pasu %s" % html.count('class="ev-gal-item"'))
krok("pocet stran se prepocital na %s" % strany_po,
     ('id="ev-gal-s%s"' % strany_po) in html)
nova_fotka.unlink()
env.cr.commit()
html = stahni("/")
krok("po smazani je pas zpatky na %s fotkach" % pocet_fotek,
     html.count('class="ev-gal-item"') == pocet_fotek)
krok("a stran je zase %s" % strany_pred,
     ('id="ev-gal-s%s"' % (strany_pred + 1)) not in html)

print("\n===== 5. KOHO PRIJIMAME =====")
Druh = env["elite.vet.species"]
novy_druh = Druh.create({"name": "ZKOUSKA druh", "icon_code": "pes", "sequence": 999})
env.cr.commit()
krok("novy druh je na strance", "ZKOUSKA druh" in stahni("/"))
novy_druh.unlink()
env.cr.commit()
krok("po smazani zmizel", "ZKOUSKA druh" not in stahni("/"))

print("\n===== 6. OTEVIRACI DOBA =====")
radek = env["elite.vet.opening.hours"].search([], limit=1)
puvodni_cas = {j: radek.with_context(lang=j).time_text for j in ("cs_CZ", "de_DE", "en_US", "ru_RU")}
puvodni_kratce = {j: radek.with_context(lang=j).time_short for j in ("cs_CZ", "de_DE", "en_US", "ru_RU")}
for jazyk in puvodni_cas:
    radek.with_context(lang=jazyk).time_text = "5:55 – 21:11"
    radek.with_context(lang=jazyk).time_short = "5–21"
env.cr.commit()
domu, rozpis, rezervace = stahni("/"), stahni("/rozpis-lekaru"), stahni("/rezervacni-system")
krok("doba se zmenila v letaku", "5–21" in domu)
krok("doba se zmenila v kontaktech", "5:55 – 21:11" in domu)
krok("doba se zmenila v karte O klinice", domu.count("5:55 – 21:11") >= 2,
     "nalezeno %sx" % domu.count("5:55 – 21:11"))
krok("doba se zmenila na rozpisu", "5:55 – 21:11" in rozpis)
krok("doba se zmenila na rezervaci", "5:55 – 21:11" in rezervace)
for jazyk, hodnota in puvodni_cas.items():
    radek.with_context(lang=jazyk).time_text = hodnota
    radek.with_context(lang=jazyk).time_short = puvodni_kratce[jazyk]
env.cr.commit()
krok("doba se vratila do puvodniho stavu", "5:55" not in stahni("/"))

print("\n===== 7. KONTAKTY A NASTAVENI =====")
nastaveni = env["elite.vet.setting"].nastaveni()
puvodni_telefon = nastaveni.phone
puvodni_zobrazeni = nastaveni.phone_display
nastaveni.write({"phone": "+420111222333", "phone_display": "+420 111 222 333"})
env.cr.commit()
krok("telefon se zmenil na domovske strance", "+420111222333" in stahni("/"))
krok("telefon se zmenil na strance tymu", "+420111222333" in stahni("/nas-tym"))
krok("telefon se zmenil na ceniku", "+420111222333" in stahni("/cenik"))
nastaveni.write({"phone": puvodni_telefon, "phone_display": puvodni_zobrazeni})
env.cr.commit()
krok("telefon se vratil", "+420111222333" not in stahni("/"))

print("\n===== 8. POHOTOVOST 24/7 =====")
puvodni_stav = nastaveni.emergency_active
nastaveni.emergency_active = False
env.cr.commit()
html = stahni("/")
krok("vypnuta: tlacitko Volat je sede a neklikaci",
     'class="ev-coach-call" disabled=' in html and 'ev-coach-call ev-coach-call--zive' not in html)
krok("vypnuta: kolecko 24/7 nevola", 'class="ev-fab247" role="img"' in html)
nastaveni.write({"emergency_active": True, "emergency_phone": "+420999888777"})
env.cr.commit()
html = stahni("/")
krok("zapnuta: tlacitko je zelene s odkazem", "ev-coach-call--zive" in html
     and "tel:+420999888777" in html)
krok("zapnuta: kolecko 24/7 vola", html.count("tel:+420999888777") >= 2)
nastaveni.write({"emergency_active": puvodni_stav, "emergency_phone": puvodni_telefon})
env.cr.commit()
krok("pohotovost vracena do puvodniho stavu",
     env["elite.vet.setting"].nastaveni().emergency_active == puvodni_stav)


print("\n===== 8b. TEXTY VYPNUTE POHOTOVOSTI =====")
# Dokud jsou pole prazdna, plati puvodni veta ze sablony — a ta je prelozena.
# Jakmile klinika neco napise, prebije ji to.
puvodni_texty = {p: nastaveni[p] for p in
                 ("emergency_active", "emergency_off_button",
                  "emergency_off_text", "emergency_off_note")}
nastaveni.write({"emergency_active": False, "emergency_off_button": False,
                 "emergency_off_text": False, "emergency_off_note": False})
env.cr.commit()

# Ocekavane vety vzaty z opravdu vykreslene stranky, ne z hlavy.
PUVODNI = {
    "cs-CZ,cs": ["Volat již brzy", "pohotovostní linku", "V blízké době plánujeme"],
    "de-DE,de": ["Anrufen demnächst", "Notfallnummer", "Öffnungszeiten"],
    "en-US,en": ["Call SOON", "emergency line", "opening hours"],
    "ru-RU,ru": ["Позвонить скоро", "линию", "часы"],
}
for jazyk, vety in PUVODNI.items():
    html = stahni("/", jazyk)
    chybejici = [v for v in vety if v not in html]
    krok("prazdna pole, %s: puvodni prelozene vety zustaly %s"
         % (jazyk[:2], chybejici or ""), not chybejici)

nastaveni.write({"emergency_off_button": "ZKOUSKA tlacitko",
                 "emergency_off_text": "ZKOUSKA bublina, momentalne mimo provoz.",
                 "emergency_off_note": "ZKOUSKA poznamka pod hodinami."})
env.cr.commit()
html = stahni("/")
krok("napis na tlacitku se prepsal",
     "ZKOUSKA tlacitko" in html and "Volat již brzy" not in html)
krok("text v bubline se prepsal", "ZKOUSKA bublina" in html)
krok("veta pod ordinacnimi hodinami se prepsala", "ZKOUSKA poznamka" in html)

nastaveni.emergency_active = True
env.cr.commit()
krok("po zapnuti pohotovosti texty vypnute varianty zmizely", "ZKOUSKA" not in stahni("/"))

nastaveni.write(puvodni_texty)
env.cr.commit()
krok("texty vraceny do puvodniho stavu", "ZKOUSKA" not in stahni("/"))
print("\n===== 9. CASTE DOTAZY =====")
Dotaz = env["elite.vet.faq"]
novy_dotaz = Dotaz.create({"name": "ZKOUSKA dotaz", "answer": "<p>Docasna odpoved.</p>",
                           "sequence": 999})
env.cr.commit()
krok("dotaz je na strance rezervace", "ZKOUSKA dotaz" in stahni("/rezervacni-system"))
novy_dotaz.unlink()
env.cr.commit()
krok("po smazani zmizel", "ZKOUSKA dotaz" not in stahni("/rezervacni-system"))

print("\n===== 9b. TEXTY REZERVACE =====")
# Pole jsou prekladatelna, takze zapis plati jen pro jazyk, ve kterem se pise.
# Test proto zapisuje cesky a cesky i cte — jinak by porovnaval dva jazyky.
cesky = nastaveni.with_context(lang="cs_CZ")
puvodni_hlaska = cesky.booking_loading_title
puvodni_tlacitko = cesky.schedule_link_button
cesky.write({"booking_loading_title": "ZKOUSKA hlaska",
             "schedule_link_button": "ZKOUSKA tlacitko"})
env.cr.commit()
krok("hlaska pri nacitani jde zmenit z adminu",
     "ZKOUSKA hlaska" in stahni("/rezervacni-system"))
krok("stejna hlaska se propsala i na rozpis",
     "ZKOUSKA hlaska" in stahni("/rozpis-lekaru"))
krok("tlacitko na rozpis jde zmenit",
     "ZKOUSKA tlacitko" in stahni("/rezervacni-system"))
cesky.write({"booking_loading_title": puvodni_hlaska,
             "schedule_link_button": puvodni_tlacitko})
env.cr.commit()
krok("texty vraceny", "ZKOUSKA" not in stahni("/rezervacni-system"))
krok("nemcina zustala nedotcena",
     "Reservierungssystem" in stahni("/rezervacni-system", "de-DE,de"))

print("\n===== 10. CENIK =====")
Cena = env["elite.vet.price.item"]
novy_ukon = Cena.create({"name": "ZKOUSKA ukon", "price": "1 Kč", "icon_code": "kocka",
                         "sequence": 999})
env.cr.commit()
html = stahni("/cenik")
krok("ukon je na ceniku", "ZKOUSKA ukon" in html)
krok("i s cenou", "1 Kč" in html)
novy_ukon.unlink()
env.cr.commit()
krok("po smazani zmizel", "ZKOUSKA ukon" not in stahni("/cenik"))

print("\n===== 11. BLOKY STRANKY =====")
Blok = env["elite.vet.page.section"].with_context(active_test=False)
tym = Blok.search([("qweb_template", "=", "elite_vet_web.sekce_tym")])
puvodni_poradi = tym.sequence
tym.active = False
env.cr.commit()
krok("vypnuty blok ze stranky zmizi", 'id="tym"' not in stahni("/"))
tym.write({"active": True, "sequence": 5})
env.cr.commit()
html = stahni("/")
krok("blok je zpatky", 'id="tym"' in html)
krok("presunuty blok je vyse nez leták", html.index('id="tym"') < html.index('id="odpocet"'))
tym.sequence = puvodni_poradi
env.cr.commit()
html = stahni("/")
krok("poradi vraceno", html.index('id="odpocet"') < html.index('id="tym"'))

print("\n===== 12. REZERVACE A ROZPIS =====")
rezervace = stahni("/rezervacni-system")
krok("kolecko nacitani je pod rameckem", "evrez-spinner" in rezervace)
krok("tlacitko na rozpis je nad castymi dotazy",
     "evrez-rozpis-btn" in rezervace
     and rezervace.index("evrez-rozpis-lead") < rezervace.index('class="ev-faq-list"'))
rozpis = stahni("/rozpis-lekaru")
krok("na rozpisu je legenda specializaci", "rs-leg" in rozpis)
# Smajlik se ukaze jen u lekarky, ktera ma specializaci a zrovna slouzi.
# Obojí si zkouska zaridi sama, at nestoji na tom, co je zrovna v rozpisu,
# a po sobe to zase uklidi.
import datetime

Smena = env["elite.vet.shift"]
Lekarka = env["elite.vet.doctor"]
typ_smeny = env["elite.vet.shift.type"].search([("is_note", "=", False)], limit=1)
specializace = env["elite.vet.team.specialization"].search([("icon_id", "!=", False)], limit=1)
lekarka = Lekarka.search([("specialization_ids", "!=", False)], limit=1)
pridana_specializace = False
if not lekarka and specializace:
    lekarka = Lekarka.search([("member_id", "!=", False)], limit=1)
    lekarka.member_id.specialization_ids = [(4, specializace.id)]
    pridana_specializace = True

if not lekarka or not typ_smeny or not specializace:
    krok("smajlik stoji pred jmenem", False,
         "v databazi chybi lekarka, typ smeny nebo specializace s ikonou")
else:
    zkusebni_smena = Smena.create({"date": datetime.date.today(),
                                   "doctor_id": lekarka.id,
                                   "type_id": typ_smeny.id})
    env.cr.commit()
    rozpis = stahni("/rozpis-lekaru")
    bunky = [b for b in rozpis.split('<span class="rs-doc">')[1:] if "rs-specs" in b]
    krok("smajlik stoji pred jmenem", bool(bunky) and all(
         b.index("rs-specs") < b.index(lekarka.name) for b in bunky if lekarka.name in b),
         "bunek se smajlikem: %s" % len(bunky))
    zkusebni_smena.unlink()
    if pridana_specializace:
        lekarka.member_id.specialization_ids = [(3, specializace.id)]
    env.cr.commit()
    krok("zkusebni smena i specializace uklizeny",
         not Smena.search_count([("id", "=", zkusebni_smena.id)])
         and (not pridana_specializace or not lekarka.specialization_ids))
krok("mesic je cesky", "Září" in rozpis or "Říjen" in rozpis)
krok("mesic je nemecky", "September" in stahni("/rozpis-lekaru", "de-DE,de")
     or "Oktober" in stahni("/rozpis-lekaru", "de-DE,de"))

print("\n===== 12b. DVE LEKARKY NA JEDNE SMENE =====")
Smena = env["elite.vet.shift"]
vzor = Smena.search([], limit=1, order="date")
druha = env["elite.vet.doctor"].search([("id", "!=", vzor.doctor_id.id)], limit=1)
zkusebni = Smena.create({"date": vzor.date, "type_id": vzor.type_id.id,
                         "doctor_id": druha.id})
env.cr.commit()
rozpis = stahni("/rozpis-lekaru")
krok("obe lekarky jsou na strance",
     vzor.doctor_id.name in rozpis and druha.name in rozpis)
krok("jmena jsou spojena plusem", " + " in rozpis)
# smena se ma vypsat jednou na skupinu, ne u kazde lekarky zvlast
bunka = rozpis[rozpis.find(druha.name) - 500:rozpis.find(druha.name) + 300]
nazev_smeny = vzor.type_id.with_context(lang="cs_CZ").name
krok("smena je v bunce uvedena jednou", bunka.count(nazev_smeny) == 1,
     "nalezeno %sx" % bunka.count(nazev_smeny))
zkusebni.unlink()
env.cr.commit()
krok("zkusebni smena uklizena",
     Smena.search_count([("date", "=", vzor.date), ("doctor_id", "=", druha.id)]) == 0)

print("\n===== 13. OBRAZKY A ODKAZY =====")
html = stahni("/")
chybne = []
for cast in html.split('src="')[1:]:
    adresa = cast.split('"', 1)[0]
    if not adresa.startswith("/elite_vet_web/static"):
        continue
    try:
        with urllib.request.urlopen(ZAKLAD + adresa, timeout=20) as odpoved:
            if odpoved.status != 200:
                chybne.append(adresa)
    except Exception:
        chybne.append(adresa)
krok("staticke obrazky se servuji", not chybne, ", ".join(chybne[:3]))
for polozka in env["website.menu"].search([("parent_id", "!=", False)]):
    pass
mimo = env["website.menu"].search([("url", "like", "winvet")])
krok("zadna polozka menu nevede mimo web", not mimo,
     ", ".join(mimo.mapped("url"))[:60])


print("\n===== 14. NIC NEPROSAKUJE NA CIZI WEBY =====")
# Databaze hostuje vic webu (Arena, trafika, Jack, IMI). Stranka bez prirazeneho
# webu je v Odoo "obecna" a vykresli se na vsech domenach — presne to se uz
# jednou stalo a rozpis sluzeb visel i tam, kam nepatri.
pocet_webu = env["website"].search_count([])
print("webu v databazi: %s" % pocet_webu)

for xml_id in ("elite_vet_web.rezervace_page", "elite_vet_web.cenik_page",
               "elite_vet_calendar.rozpis_lekaru_page", "elite_vet_team.nas_tym_page"):
    stranka = env.ref(xml_id, raise_if_not_found=False)
    krok("stranka %s patri jednomu webu" % (stranka.url if stranka else xml_id),
         bool(stranka and stranka.website_id))

obecne_menu = env["website.menu"].search([
    ("url", "in", ["/rozpis-lekaru", "/nas-tym", "/cenik", "/rezervacni-system"]),
    ("website_id", "=", False)])
krok("zadna polozka menu kliniky neni obecna",
     not obecne_menu, ", ".join(obecne_menu.mapped("url")))

if pocet_webu > 1:
    # Obecna homepage patri vsem webum, takze na ni sablona kliniky nesmi.
    obecna_domu = env["website.page"].search([("url", "=", "/"), ("website_id", "=", False)])
    krok("obecna homepage neukazuje na sablonu kliniky",
         not obecna_domu or obecna_domu.view_id.key != "elite_vet_web.homepage")
else:
    krok("jediny web v databazi, obecna homepage je v poradku", True)

print("\n===== 15. PREPINAC JAZYKU =====")
# Prepinac vede primo na jazykovou adresu. Pres /website/lang/ to stalo na cookie
# frontend_lang a in-app prohlizec Instagramu a Facebooku ho neposila tak, jak
# Odoo ceka — klik na jazyk skoncil zpatky na puvodni strance.
import re

for cesta in ("/", "/de", "/en", "/ru", "/de/cenik", "/ru/rozpis-lekaru", "/en/nas-tym"):
    html = stahni(cesta)
    zacatek = html.find('class="ev-lang-panel"')
    panel = html[zacatek:zacatek + 600] if zacatek > -1 else ""
    odkazy = re.findall(r'href="([^"]*)"', panel)
    krok("%s: prepinac ma vsechny ctyri jazyky" % cesta, len(odkazy) == 4,
         "nalezeno %s" % len(odkazy))
    krok("%s: zadny odkaz neni prazdny" % cesta,
         bool(odkazy) and all(o.strip() for o in odkazy), str(odkazy))
    krok("%s: nejde pres /website/lang/" % cesta,
         not any("website/lang" in o for o in odkazy), str(odkazy))

# Klik na jazyk opravdu prepne, i kdyz prohlizec neposila Accept-Language.
import urllib.request
import http.cookiejar

def prejdi(kroky):
    """Projde adresy se sdilenymi cookies a vrati <html lang> te posledni."""
    cookies = http.cookiejar.CookieJar()
    otevirac = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
    html = ""
    for cesta in kroky:
        with otevirac.open(ZAKLAD + cesta, timeout=30) as odpoved:
            html = odpoved.read().decode("utf-8", "replace")
    nalez = re.search(r'<html[^>]*lang="([^"]+)"', html)
    return nalez.group(1) if nalez else "?"

for start, cil, ocekavano in (("/de", "/cs", "cs-CZ"), ("/en", "/cs", "cs-CZ"),
                              ("/ru", "/cs", "cs-CZ"), ("/", "/de", "de-DE"),
                              ("/de", "/ru", "ru-RU")):
    mam = prejdi([start, cil])
    krok("z %s na %s prepne na %s" % (start, cil, ocekavano), mam == ocekavano, mam)
print("\n===== SHRNUTI =====")
prosle = sum(1 for ok, _, _ in vysledky if ok)
print("proslo %s z %s kontrol" % (prosle, len(vysledky)))
for ok, nazev, detail in vysledky:
    if not ok:
        print("  CHYBA: %s — %s" % (nazev, detail))
