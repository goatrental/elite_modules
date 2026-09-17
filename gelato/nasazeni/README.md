# Nasazení Gelato! na server

Postup pro Odoo 18. Počítá s tím, že na serveru už Odoo běží v Dockeru
a má nějakou složku pro vlastní moduly (typicky `extra-addons`).

Odhad času: **30 minut**, z toho většinu zabere překreslení zón.

---

## 1. Moduly na server

Zkopírovat **obsah** složky `gelato/` do addons složky. Moduly musí ležet
**jednu úroveň** pod addons cestou:

```
extra-addons/
├── gelato_delivery/
├── gelato_flavors/
├── gelato_tracking/
└── theme_gelato/
```

Ne `extra-addons/gelato/gelato_delivery/` — tak je Odoo nenajde.

```bash
scp -r gelato/gelato_* gelato/theme_gelato root@SERVER:/cesta/extra-addons/
ssh root@SERVER 'docker restart NAZEV_KONTEJNERU'
```

## 2. Instalace

```bash
docker exec -it NAZEV_KONTEJNERU odoo \
  -d NAZEV_DB \
  --addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons \
  -i theme_gelato,gelato_flavors,gelato_delivery,gelato_tracking \
  --load-language=cs_CZ --without-demo=all --stop-after-init
docker restart NAZEV_KONTEJNERU
```

Na databázi, kde už moduly jsou, se místo `-i` použije `-u`. **Nikdy `-i` na
ostré databázi** — přepsalo by to výchozí data (boxy, ceny, texty e-mailů).

## 3. Téma přiřadit webu

Samotná instalace tématu nic nezobrazí, Odoo ho musí přiřadit webu.
V Odoo: **Web → Vzhled → Vybrat téma → Gelato**.

Nebo z příkazové řádky:

```bash
docker exec -i NAZEV_KONTEJNERU odoo shell -d NAZEV_DB --no-http <<'EOF'
w = env["website"].search([], limit=1)
t = env["ir.module.module"].search([("name", "=", "theme_gelato")], limit=1)
w.theme_id = t.id
t._theme_load(w)
env.cr.commit()
EOF
docker restart NAZEV_KONTEJNERU
```

Pokud po tom `/` ukazuje prázdnou stránku, leží na té adrese ještě původní
prázdná `website.homepage`. Smazat ji a **restartovat** (bez restartu hodí
`MissingError` ze staré mezipaměti):

```bash
docker exec -i NAZEV_KONTEJNERU odoo shell -d NAZEV_DB --no-http <<'EOF'
for p in env["website.page"].search([("url", "=", "/")]):
    if p.view_id.key == "website.homepage":
        p.unlink()
env.cr.commit()
EOF
```

## 4. Odchozí pošta

**Bez tohohle kroku neodejde ani jeden e-mail.** Objednávky se budou vytvářet,
ale potvrzení zákazníkovi ani přehled do obchodu se jen odloží do fronty.

Odoo → Nastavení → Technické → **Odchozí poštovní servery**. Vyplnit SMTP
poskytovatele a dát **Otestovat spojení**.

Odesílatele bere Odoo z e-mailu firmy, proto Nastavení → Uživatelé a firmy →
**Firmy** musí mít vyplněný e-mail.

## 5. Co nastavit v Odoo

| Kde | Co |
|---|---|
| Nastavení → Firmy | název, adresa, telefon, e-mail, měna **CZK** |
| Nastavení → Jazyky | jen **čeština**, angličtinu nechat neaktivní |
| Web → Nastavení → E-mail pro objednávky | kam chodí nové objednávky |
| Web → Nastavení → Doprava | paušální dopravné pro adresy mimo zóny |
| Web → Nastavení → Lišta cookies | **zapnout** (jinak se GTM ani Pixel nespustí) |
| Web → Nastavení → GTM / Meta Pixel | vyplnit ID; dokud jsou prázdná, neměří se nic |
| Rozvoz → Nastavení → Zóny rozvozu | **překreslit**, viz níže |
| Rozvoz → Dnešní nabídka | hodiny pro objednávky a vypínač rozvozu |

### Zóny je potřeba překreslit

V datech jsou dva **hrubé prstence okolo Karlových Varů**, jen aby mapa nebyla
prázdná. Otevřít každou zónu, dát **Nakreslit zónu** a poklikat skutečnou
hranici. Pak zkontrolovat ceny, hranici dopravy zdarma a minimální objednávku.

Zóny se můžou překrývat, vyhrává ta výš v seznamu. **Žádná zóna znamená žádnou
kontrolu** — projde každá adresa a platí paušální dopravné z nastavení.

### Sloupce boardu

Rozvoz → Nastavení → Sloupce boardu. Ve výchozím stavu posílá e-mail
**Přijatá** (potvrzení zákazníkovi) a **Na cestě**. Potvrzená a Doručená mají
text připravený, ale vypnutý.

SMS jsou všude vypnuté a bez připojeného operátora stejně neodejdou. Text pro
„Na cestě" je nachystaný.

## 6. Server musí ven na internet

Zóny potřebují dvě adresy. Když je firewall zavře, adresy se nepřevedou na
souřadnice a objednávky projdou bez zóny s paušálním dopravným.

| Adresa | K čemu |
|---|---|
| `nominatim.openstreetmap.org` | převod adresy na souřadnice (server) |
| `*.tile.openstreetmap.org` | dlaždice mapy při kreslení zón (prohlížeč) |

## 7. Ověřit, že to jede

1. `/rozvoz` se načte v Gelato vzhledu, v hlavičce je logo.
2. Vybrat příchutě, napsat **skutečnou karlovarskou adresu** — pod polem se
   musí objevit název zóny a cena dopravy.
3. Odeslat objednávku. Musí přijít **číslo objednávky** na stránce.
4. V Odoo → Rozvoz → Board objednávek přibyla karta s obsahem objednávky.
5. Nastavení → Technické → E-maily: dvě zprávy ve stavu **Odesláno**, jedna
   zákazníkovi, jedna do obchodu. Otevřít je a zkontrolovat, že v textu nejsou
   vidět `{{ }}`.
6. Přetáhnout kartu do **Na cestě** — zákazníkovi odejde další e-mail.
7. Zkusit adresu mimo zóny (třeba pražskou). Musí ji odmítnout.
8. Rozvoz → Zákazníci: objednávající se tam objevil právě jednou.
9. Testovací objednávky a zákazníky pak smazat.

## Na co si dát pozor

**Heslo pro správu databází.** V `config/odoo.conf` je `admin_passwd =
zmente-me`. Před zveřejněním změnit.

**Přihlášení admina.** Odoo ho zakládá s výchozími údaji, nastavit vlastní
heslo.

**Sloupce boardu posílají zákazníkům e-maily.** Než se pustí ostrý provoz, dát
si pozor, aby v boardu nezůstaly testovací objednávky se skutečnými adresami.
