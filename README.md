
„Zavřeno" má zaškrtnutou **Celodenní poznámku**, takže se u něj nezadává lékařka
ani čas. Stejně se dá založit i `Den otevřených dveří` nebo `Sanitární den`.
# modules

Odoo 18 moduly a Docker sestava, která je používá. Moduly jsou seřazené
po projektech.

```
modules/
├── docker-compose.yml     Odoo 18 + PostgreSQL
├── config/odoo.conf       addons_path, připojení k databázi
└── elite.vet/             klinika Elite Vet
    └── rozpis/            Rozpis služeb lékařů
```

Celý repozitář je v kontejneru namountovaný do `/mnt/modules`.

**Nový modul stejného projektu** = nová podsložka v `elite.vet/`. Nic se nenastavuje.

**Nový projekt** = nová složka vedle `elite.vet/` a jeden záznam navíc
v `addons_path` v [config/odoo.conf](config/odoo.conf):

```ini
addons_path = /mnt/modules/elite.vet,/mnt/modules/dalsi-projekt,/usr/lib/python3/dist-packages/odoo/addons
```

## Spuštění

```bash
git clone https://github.com/goatrental/modules.git
cd modules
docker compose up -d
```

Odoo běží na `http://localhost:8069`. Nasazení na existující server je
v [DOCKER.md](DOCKER.md).

## elite.vet — klinika Elite Vet

### `rozpis` — Rozpis služeb

Aplikace **Rozpis služeb** a veřejná stránka `/rozpis-lekaru` s měsíčním
kalendářem. Aplikace má tři položky a nic víc.

**Rozpis** — jeden řádek má tři údaje:

| Pole | Hodnota |
|---|---|
| Datum | den služby |
| Lékařka | výběr ze seznamu |
| Směna | výběr z typů směn |

**Lékařky** — jméno a konec.

**Typy směn** — tady se mění čas i barva směny. Změna se hned promítne na web,
do vysvětlivek i do bublin u jmen.

| Název | Od | Do | Barva |
|---|---|---|---|
| Ranní služba | 8:00 | 14:00 | zelená |
| Odpolední služba | 14:00 | 20:00 | oranžová |
| Noční služba | 20:00 | 8:00 | fialová |
| Víkendová služba | 10:00 | 18:00 | růžová |
| Zavřeno *(celodenní poznámka)* | — | — | červená |

Typ se zaškrtnutou **Celodenní poznámkou** není služba lékařky — nezadává se u něj
lékařka ani čas a na webu se vypíše přes celou buňku. Stejně se dá založit
`Den otevřených dveří` nebo `Sanitární den`, každý ve své barvě.

Detaily v [elite.vet/rozpis/README.md](elite.vet/rozpis/README.md).
