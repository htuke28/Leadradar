# Van laptop naar URL voor Gilbert — twee snelheden

## Nu meteen (0 minuten wachten, werkt vandaag)

Vereist: Python op één laptop (die van jou of van Gilbert). Geen installatie van iets
anders nodig.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Er opent automatisch een browsertab. Zolang dat terminalvenster openstaat, kan iedereen
op hetzelfde wifi-netwerk de "Network URL" gebruiken die Streamlit toont (bijv.
`http://192.168.x.x:8501`) — dus dit werkt ook al met Gilbert erbij aan tafel, zonder dat
er iets online staat.

Nadeel: stopt zodra het terminalvenster dicht gaat, en werkt alleen op hetzelfde netwerk.
Prima voor "vandaag laten zien", niet voor "Gilbert gebruikt dit elke week op kantoor".

## Deze week (een vaste URL, altijd aan, gratis)

**Streamlit Community Cloud** is de snelste weg naar een permanente link — geen server
beheren, geen kosten voor dit gebruiksvolume.

1. Zet deze map in een GitHub-repository (gratis account op github.com als je die nog niet
   hebt). Kan via de GitHub-website: nieuwe repository aanmaken → bestanden uploaden (sleep
   de hele map erin) → committen. Geen command line nodig.
2. Ga naar [share.streamlit.io](https://share.streamlit.io), log in met je GitHub-account.
3. Klik "New app", kies de zojuist aangemaakte repository, en zet `app.py` als hoofdbestand.
4. Klik "Deploy". Na ~2 minuten krijg je een vaste URL zoals
   `https://leadradar-salesia.streamlit.app` die je met Gilbert kan delen.

Dat is het — geen server, geen maandelijkse rekening voor dit volume. Totale tijd: een
kwartiertje, eenmalig.

## Als er straks meer nodig is

Zodra de KvK-key of contact-verrijking erbij komt: die vul je in via het "KvK-verrijking"-
vinkje in de app zelf (API-key invoerveld) — geen nieuwe deploy nodig, geen code-wijziging.
Als de tool bij meerdere klanten tegelijk gebruikt gaat worden, is een lichte upgrade van
"open URL" naar "URL met wachtwoord per klant" een kleine vervolgstap, geen herbouw.
