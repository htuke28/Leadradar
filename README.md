# Leadradar

Profielgestuurde lead-generatie: je stelt een ideale-klantprofiel in (sector, grootte,
regio, signalen), de tool verrijkt en scoort een lijst bedrijven daartegen, en levert een
sorteerbaar Excel-bestand op. Eén profiel = één klant of klanttype — de tool zelf is niet
gebonden aan één klant.

Dit is een werkende MVP, geen mockup. Hieronder staat expliciet wat er al écht draait,
wat een bewuste placeholder is, en wat je moet regelen voordat dit bij een klant live gaat.

## Wat is er al echt

- **De hele pipeline (CSV inladen → verrijken → scoren → Excel wegschrijven)** is werkende
  Python-code, gedraaid en getest — zie `leads_voorbeeld.xlsx` in deze levering, gegenereerd
  uit `data/voorbeeld_export.csv` met `profiles/voorbeeld_machinebouw_twente.yaml`.
- **De scoringslogica** (`leadradar/scoring.py`) is regelgebaseerd en transparant: elk
  bedrijf krijgt een leesbare match-reden per criterium, geen black box. 6 unit tests
  dekken de score- en KvK-verrijkingslogica (`pytest`, allemaal groen).
- **De KvK-adapter** (`leadradar/enrich/kvk.py`) is een echte integratie tegen de officiële
  KvK-API's (Zoeken + Basisprofiel), inclusief de publieke testomgeving-key van de KvK
  developer portal. De aanroepen en veldnamen zijn gebaseerd op de actuele documentatie op
  developers.kvk.nl (geraadpleegd 20-08-2026) en met gemockte responses getest
  (`tests/test_kvk_mock.py`) — **niet live getest**, want dit sandbox-netwerk staat geen
  uitgaande verbindingen naar `api.kvk.nl` toe. Draai `pytest` en de CLI vanaf een omgeving
  mét internettoegang (jouw eigen laptop/server) om de live call te zien werken; verifieer
  bij die eerste live run de exacte veldnamen in de respons tegen de Swagger-UI op
  developers.kvk.nl, voor het geval de API is doorontwikkeld.

## Belangrijke correctie t.o.v. het oorspronkelijke plan

De bouwbrief noemde de KvK als één van de databronnen voor het *vinden* van bedrijven.
Uit de officiële documentatie blijkt dat de KvK Zoeken-API **niet** filtert op SBI-code,
regio-straal of aantal medewerkers — hij zoekt alleen op naam, plaats, postcode of
KvK-nummer (bevestigd via de KvK developer-FAQ). De KvK is dus geschikt om een al-gevonden
bedrijf te *verifiëren en verrijken* (officiële naam, KvK-nummer, SBI-activiteiten,
medewerkersaantal) — niet om zelf een sector+regio+grootte-lijst te genereren. Die rol is
in deze tool bij de CSV-bron gelegd (stap hieronder), precies zoals de bouwbrief het al
voorstelde met bedrijvenopdekaart.nl als primaire zoekbron.

## Wat een bewuste placeholder is

- **Discovery-bron (`data/voorbeeld_export.csv`)**: fictieve voorbeelddata. In de praktijk
  exporteer je die lijst handmatig vanaf bedrijvenopdekaart.nl (heeft ingebouwde filters op
  provincie/branche en een export-naar-Excel-knop — geen scraping nodig) en laad je dat
  bestand in met dezelfde kolomstructuur. `leadradar/sources/csv_source.py` verwacht die
  kolommen; als de export van bedrijvenopdekaart.nl er anders uitziet, is een kleine
  kolom-mapping nodig voordat je 'm inleest.
- **Contactpersoon**: leeg, met een duidelijke placeholder-tekst in de Excel-output.
  Zoals besproken: geen LinkedIn-scraping (in strijd met hun voorwaarden, risico op
  accountban). Koppel hiervoor een compliant contact-verrijkingstool (Apollo.io, Lusha,
  Dropcontact, Kaspr) of een handmatige Sales Navigator-export — dat is een aparte
  beslissing die nog gemaakt moet worden, geen technisch obstakel.
- **SBI-codes in `profiles/voorbeeld_machinebouw_twente.yaml`**: illustratief, nog niet
  geverifieerd tegen de officiële CBS/KvK SBI-lijst. Zoek de juiste codes op voordat dit
  live gaat — staat ook als comment in het bestand.
- **Outreach-conceptbericht**: zat in de eerdere visuele preview, staat nog niet in deze
  code-MVP. Logische volgende stap zodra de discovery- en verrijkingsstap bewezen goed
  werken (zelfde MVP-filosofie als de bouwbrief: één werkend onderdeel tegelijk).

## Het profiel is het product

`profiles/voorbeeld_machinebouw_twente.yaml` is één voorbeeld, geen vaste configuratie.
Voor een nieuwe klant kopieer je het bestand en pas je de criteria aan:

```yaml
profiel:
  naam: "Klant X — Sector Y, regio Z"
  sectoren: ["..."]
  sbi_codes: ["..."]
  grootte_min: 5
  grootte_max: 50
  regio:
    omschrijving: "..."
  type: "eindklant"
  signalen: ["..."]
  gewichten: { sector: 30, grootte: 20, regio: 20, signaal: 30 }
```

## Gebruik — met scherm (voor Gilbert, geen terminal-kennis nodig)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opent een browserpagina: profiel kiezen, CSV uploaden (of voorbeelddata proberen), op
"Genereer leadlijst" klikken, Excel downloaden. Zie `DEPLOY.md` voor hoe je hier binnen een
kwartier een vaste, deelbare URL van maakt (Streamlit Community Cloud, gratis).

## Gebruik — command line (voor testen/automatiseren)

```bash
pip install -r requirements.txt

# zonder KvK-verrijking (werkt altijd, ook zonder netwerktoegang):
python -m leadradar.cli \
  --profiel profiles/voorbeeld_machinebouw_twente.yaml \
  --input data/voorbeeld_export.csv \
  --output leads.xlsx \
  --geen-kvk-verrijking

# mét live KvK-verrijking (vanaf een omgeving met internettoegang):
python -m leadradar.cli \
  --profiel profiles/voorbeeld_machinebouw_twente.yaml \
  --input data/voorbeeld_export.csv \
  --output leads.xlsx

pytest   # 6 tests, scoring + gemockte KvK-integratie
```

## Wat nodig is voordat dit bij een klant live gaat

1. Een echte KvK API-key aanvragen (betaald per opvraging boven de testomgeving) en
   `KvkClient(apikey=..., base_url="https://api.kvk.nl/api")` gebruiken i.p.v. de
   testomgeving.
2. Een keuze voor de contactpersoon-bron (Apollo/Lusha/Dropcontact/Kaspr of handmatige
   Sales Navigator-export) en die als nieuwe `enrich`-module toevoegen — dezelfde vorm als
   `enrich/kvk.py`.
3. De SBI-codes per profiel controleren tegen de officiële lijst.
4. Een vaste werkwijze voor de bedrijvenopdekaart.nl-export (wie downloadt 'm, hoe vaak,
   welke kolom-mapping) — dit is nu een handmatige stap, bewust, conform de MVP-aanpak uit
   de bouwbrief ("controleer handmatig of de output klopt").
5. Wie deze operationele/lopende kosten draagt (KvK API, verrijkingstool) — hoort in de
   prijsafspraak met de klant, niet in de bouwkosten.
