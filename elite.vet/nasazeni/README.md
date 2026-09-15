# Nasazení webu Elite Vet — postup na jeden zátah

Celý web běží na modulech: `elite_vet_team` (/nas-tym), `elite_vet_calendar`
(/rozpis-lekaru) a `elite_vet_web` (/ a /rezervacni-system). Instaluje se jen
`elite_vet_web`, zbytek si Odoo dotáhne přes závislosti.

## Než začneš

**Zálohuj databázi.** Kroky 3 a 4 přepisují texty a překlady.

Zkontroluj, jak je na tom web teď, ať máš s čím porovnávat:

```bash
node nasazeni/kontrola-prekladu.js https://www.elite-vet.cz
```

## 1. Nahrát moduly a nainstalovat

```bash
git pull                     # tam, kde je repozitář namountovaný do kontejneru
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d DATABAZE \
    -i elite_vet_web --stop-after-init --no-http
docker compose restart odoo
```

**Restart není volitelný.** Odoo si mapu statických souborů staví při startu,
takže do restartu by všechny fotky házely 404.

## 2. Přepnout domovskou stránku

Instalační hook přepne jen obecnou stránku Odoo. Elite Vet má na `/` vlastní
stránku svého webu, a tu je potřeba přepnout ručně:

**Nastavení → Technické → Web → Stránky**, najít `/`, v poli **Zobrazení**
vybrat `elite_vet_web.homepage`.

SEO titulek a popis zůstanou na záznamu stránky, ty se nemažou.

Stará stránka `/rezervacni-system` ze staré verze webu musí pryč, jinak budou na
stejné adrese dvě a Odoo si vybere špatnou.

## 3. Nahrát překlady stránek

```bash
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d DATABAZE \
    -u elite_vet_web,elite_vet_team,elite_vet_calendar \
    --i18n-overwrite --stop-after-init --no-http
```

**Bez `--i18n-overwrite` to neudělá skoro nic.** Odoo standardně nepřepisuje
překlad, který v databázi už je — a tam je zatím ten starý, nesprávný.

## 4. Doplnit překlady obsahu

Texty u lékařek, názvy sekcí, popisky údajů, typy směn a specializace nejsou
součástí šablon, ale záznamy v databázi. Doplní je tenhle skript:

```bash
docker compose exec -i odoo odoo shell -c /etc/odoo/odoo.conf -d DATABAZE \
    --no-http < nasazeni/preklady-dat.py
```

Jde pustit opakovaně — páruje podle současné hodnoty, takže co je už přeložené,
nechá být.

## 5. Zkontrolovat obsah v adminu

Instalace založí výchozí obsah (služby, galerii, hodiny, kontakty, časté dotazy,
ceník, nastavení) i s překlady do všech čtyř jazyků. Admin je rozdělený po
stránkách — každá aplikace obsahuje jen to, co se té stránky týká:

| aplikace | co v ní je |
|---|---|
| **Hlavní stránka** | bloky stránky, služby, koho přijímáme, galerie, ordinační hodiny, kontaktní karty |
| **Rozpis služeb** | rozpis, lékařky, typy směn, specializace, ikony |
| **Náš tým** | členové týmu, sekce, specializace, ikony, popisky podrobností |
| **Ceník** | úkony a ceny, skupiny |
| **Rezervace** | nastavení rezervace, časté dotazy |
| **Nastavení kontaktu** | telefony, adresa, sítě, pohotovost — propisuje se do všech stránek |

Projdi je a ověř, že je všechno na svém místě. Nabídka aplikací se kešuje
v prohlížeči, takže po instalaci dej **Ctrl+Shift+R**, jinak nové apky neuvidíš.

Zakládá se jen při **první** instalaci. Když už v databázi nějaké záznamy jsou,
skript je nechá být a nic nepřepíše.

Stránka `/cenik` je nová — pokud má být vidět v menu, přidej položku v
**Web → Upravit → Menu** a přelož ji stejně jako ostatní (tabulka níže).

## 6. Přeložit menu

Položky menu jsou taky data, a překládají se v administraci:
**Web → Upravit → Menu**, u každé položky přepnout jazyk a přepsat název.

| česky | německy | anglicky | rusky |
|---|---|---|---|
| Domovská stránka | Startseite | Home | Главная |
| Služby | Leistungen | Services | Услуги |
| Kontakt | Kontakt | Contact | Контакты |
| Náš tým | Unser Team | Our team | Наша команда |
| Rezervační systém | Terminbuchung | Booking | Запись на приём |
| Rozpis služeb | Dienstplan | Duty schedule | График работы |
| Ceník | Preisliste | Price list | Прайс-лист |

Pozor: **do angličtiny se zapisuje jako první**, protože je to zdrojový slot.
Čeština se pak musí vyplnit zvlášť, jinak zdědí angličtinu.

## 7. Zkontrolovat

```bash
node nasazeni/kontrola-prekladu.js https://www.elite-vet.cz
```

Projde pět stránek ve čtyřech jazycích a nahlásí každý text, který zůstal
anglicky tam, kde být nemá, nebo česky v cizojazyčné verzi. Na lokále to po
dokončení hlásilo **0 problémů z 20 kombinací**.

Kompletní zkoušku — projde admin, založí záznamy, ověří, že se objeví na webu,
a zase je smaže — pustíš takhle:

```bash
docker compose exec -i odoo odoo shell -c /etc/odoo/odoo.conf -d DATABAZE \
    --no-http < nasazeni/test-vseho.py
```

Na lokále hlásí **86 z 86 kontrol**. Skript po sobě uklízí, ale sahá do ostrých
dat — pouštěj ho až po záloze.

Ověř taky, že se u jazyka v adrese vrací i správný `<html lang>` — skript to
kontroluje sám, protože bez hlavičky `Accept-Language` Odoo vrací angličtinu
a člověk pak porovnává angličtinu samu se sebou.

## Na co si dát pozor později

**Změna textu v šabloně mění zdroj.** Šablony jsou anglicky právě proto, aby se
úpravou nerozbily ostatní jazyky. Když přidáš nový text, je potřeba doplnit ho
i do `i18n/*.po` příslušného modulu — jinak se v ostatních jazycích ukáže
anglicky.

**Nikdy nezakládej `en_US.po`.** To není jeden z jazyků, ale zdroj. Zápisem do
něj se přepíše originál a čeština, která vlastní překlad nemá, zdědí angličtinu.
Přesně tohle jednou shodilo celý rozpis do angličtiny.

**Smazání položky menu si vyžádá restart.** Když v Web → Upravit → Menu smažeš
položku, Odoo si drží starou nabídku v paměti a stránky začnou vracet 500.
Spraví to `docker compose restart odoo`, nic víc. Stalo se to dvakrát, pokaždé
to vypadalo jako rozbitý web.

**Nová složka `static/` nebo změna Pythonu potřebuje restart, ne jen `-u`.**
Upgrade modulu přenačte data a šablony, ale mapu statických souborů a kód
v paměti ne.
