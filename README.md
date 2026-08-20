# Leadradar

Profielgestuurde lead-generatie: je stelt een ideale-klantprofiel in (sector/SBI, grootte,
regio, signalen), en de tool **haalt zelf bedrijven op** die daarbij passen, scoort ze, en
levert een sorteerbaar Excel-bestand op. Eén profiel = één klant of klanttype — de tool zelf
is niet gebonden aan één klant.

Dit is een werkende MVP, geen mockup. Hieronder staat expliciet wat er al écht draait,
wat een bewuste placeholder is, en wat je moet regelen voordat dit bij een klant live gaat.

## De twee manieren om aan bedrijven te komen

**1. Automatisch zoeken (standaard, aanbevolen) — OpenKvK/overheid.io**
`leadradar/sources/openkvk_source.py` doorzoekt live het Handelsregister op
SBI-code × plaats uit je profiel en levert echte bedrijfsnamen, KvK-nummers en adressen —
geen handmatige stap. Dit is de bron die de bouwbrief oorspronkelijk bedoelde met
"automatisch bedrijven verzamelen". Vereist een API-key van overheid.io: gratis registreren
geeft alleen een willekeurige testset van 10.000 bedrijven (handig om de tool te proberen,
niet om echt te targeten); voor echte, gefilterde resultaten op je profiel is het
"Small"-abonnement nodig — **€15/maand voor 2.500 calls**, ruim voldoende voor wekelijks
meerdere profielen. Aanmelden: overheid.io → account maken → abonnement → API-key uit je
dashboard. Eén ding is nog niet live geverifieerd: de exacte namen van filter-/response-
velden zijn gebaseerd op hun documentatie (geraadpleegd 20-08-2026), niet getest tegen een
echte sleutel omdat dit sandbox-netwerk geen uitgaande calls naar `api.overheid.io` toestaat.
Test dit bij de eerste echte run (`tests/test_openkvk_mock.py` dekt de logica met gemockte
responses) en pas zo nodig het filterveld voor SBI-code aan als het net anders blijkt te
heten.

**2. Handmatige CSV-import — bedrijvenopdekaart.nl of een andere export**
Blijft beschikbaar als gratis alternatief zonder enig account: exporteer een gefilterde
lijst en laad die in. Handig als startpunt zonder kosten, of als tweede bron naast OpenKvK.

Beide leveren dezelfde `Company`-objecten op en gaan door dezelfde scoring- en
Excel-stap — je kunt vrij wisselen of allebei gebruiken.

## Belangrijke correctie t.o.v. het oorspronkelijke plan (en t.o.v. de vorige versie hiervan)

De KvK Zoeken-API zelf kan **niet** filteren op SBI-code, regio of aantal medewerkers — hij
zoekt alleen op naam, plaats, postcode of KvK-nummer (bevestigd via de KvK developer-FAQ).
De KvK's eigen open dataset (bulkdownload, gratis, CC-BY) bevat wél SBI+postcode maar
bewust **geen bedrijfsnamen** (privacy) — dus ook niet bruikbaar om leads uit te halen.
OpenKvK (via overheid.io) zit daar tussenin: een doorzoekbare index van hetzelfde
Handelsregister die wél namen + SBI + plaats combineert, tegen een licht abonnement. Dat is
de reden dat de discovery-stap nu op OpenKvK draait, en de officiële KvK-API's
(`leadradar/enrich/kvk.py`) hun eerdere, kleinere rol behouden: een gevonden bedrijf
verifiëren/verrijken (medewerkersaantal, officiële naam) — optioneel, niet de motor achter
"leads binnenhalen".

## Wat is er al echt

- **De hele pipeline** (OpenKvK of CSV → optioneel KvK-verrijken → scoren → Excel
  wegschrijven) is werkende Python-code, gedraaid en getest — zie `leads_voorbeeld.xlsx`,
  gegenereerd uit `data/voorbeeld_export.csv` met `profiles/voorbeeld_machinebouw_twente.yaml`.
- **De scoringslogica** (`leadradar/scoring.py`) is regelgebaseerd en transparant: elk
  bedrijf krijgt een leesbare match-reden per criterium. 8 unit tests dekken scoring, de
  KvK-verrijking en de OpenKvK-discovery (`pytest`, allemaal groen), allemaal met gemockte
  HTTP-responses — geen van beide externe API's is vanuit deze sandbox live bereikbaar, dus
  dat is de eerlijke grens van wat hier geverifieerd kon worden. Draai `pytest` en de CLI/app
  vanaf een omgeving met internettoegang om de live calls te zien werken.

## Wat een bewuste placeholder is

- **Grootte (medewerkersaantal)** komt niet uit OpenKvK — die bron levert het niet. Zonder
  KvK-verrijking (optie 2 hierboven, vereist een productie-KvK-key) blijft dit veld
  "onbevestigd" in de output, en telt het *niet* tegen een bedrijf mee bij scoring (zie
  `leadradar/scoring.py::_grootte_matcht`) — bewust, om geen valse zekerheid te suggereren.
- **Contactpersoon**: leeg, met een duidelijke placeholder-tekst in de Excel-output. Zoals
  besproken: geen LinkedIn-scraping. Koppel hiervoor een compliant contact-verrijkingstool
  (Apollo.io, Lusha, Dropcontact, Kaspr) of een handmatige Sales Navigator-export — een
  aparte beslissing, geen technisch obstakel.
- **SBI-codes in `profiles/voorbeeld_machinebouw_twente.yaml`**: illustratief, nog niet
  geverifieerd tegen de officiële CBS/KvK SBI-lijst.
- **Outreach-conceptbericht**: stond in de eerdere visuele preview, zit nog niet in deze
  code-MVP. Logische volgende stap zodra discovery + scoring bewezen goed werken.

## Het profiel is het product

```yaml
profiel:
  naam: "Klant X — Sector Y, regio Z"
  sectoren: ["..."]
  sbi_codes: ["..."]
  grootte_min: 5
  grootte_max: 50
  regio:
    omschrijving: "vrije tekst, alleen voor weergave"
    plaatsen: ["Enschede", "Hengelo", "..."]   # dit is wat OpenKvK daadwerkelijk gebruikt
  type: "eindklant"
  signalen: ["..."]
  gewichten: { sector: 30, grootte: 20, regio: 20, signaal: 30 }
```

## Gebruik — met scherm (voor Gilbert, geen terminal-kennis nodig)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opent een browserpagina: profiel kiezen, dan "Automatisch zoeken (OpenKvK)" of "CSV
uploaden", op "Genereer leadlijst" klikken, Excel downloaden. Zie `DEPLOY.md` voor hoe je
hier binnen een kwartier een vaste, deelbare URL van maakt (Streamlit Community Cloud,
gratis).

## Gebruik — command line

```bash
pip install -r requirements.txt

# automatisch zoeken (OpenKvK):
python -m leadradar.cli \
  --profiel profiles/voorbeeld_machinebouw_twente.yaml \
  --openkvk-key JOUW_OVERHEIDIO_KEY \
  --output leads.xlsx

# handmatige CSV, zonder enig account:
python -m leadradar.cli \
  --profiel profiles/voorbeeld_machinebouw_twente.yaml \
  --input data/voorbeeld_export.csv \
  --output leads.xlsx

# beide met extra KvK-verrijking (medewerkersaantal, officiële naam):
python -m leadradar.cli --profiel ... --openkvk-key ... --output leads.xlsx --kvk-verrijking

pytest   # 8 tests: scoring, KvK-verrijking, OpenKvK-discovery — allemaal gemockt
```

## Wat nodig is voordat dit bij een klant live gaat

1. Een overheid.io "Small"-abonnement (€15/maand) voor echte OpenKvK-resultaten — de
   operationele kost van "automatisch leads binnenhalen".
2. Bij de eerste echte run: het SBI-filterveld en de response-vorm in
   `leadradar/sources/openkvk_source.py` controleren tegen wat je dashboard/de live API
   teruggeeft, en zo nodig aanpassen.
3. (Optioneel) een echte KvK API-key voor de medewerkers-verrijking.
4. Een keuze voor de contactpersoon-bron (Apollo/Lusha/Dropcontact/Kaspr of handmatige
   Sales Navigator-export).
5. De SBI-codes per profiel controleren tegen de officiële lijst.
6. Wie deze operationele/lopende kosten draagt — hoort in de prijsafspraak met de klant,
   niet in de bouwkosten.
