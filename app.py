from __future__ import annotations

from pathlib import Path

import streamlit as st

from leadradar.enrich.kvk import KvkClient
from leadradar.enrich.website import WebsiteEnricher
from leadradar.outreach import STANDAARD_SJABLOON, genereer_bericht
from leadradar.output import schrijf_excel
from leadradar.profile import Profile
from leadradar.scoring import score_bedrijf
from leadradar.sources.csv_source import laad_csv
from leadradar.sources.google_places_source import GooglePlacesClient
from leadradar.sources.openkvk_source import OpenKvkClient

BASISPAD = Path(__file__).parent
PROFIELEN_MAP = BASISPAD / "profiles"

st.set_page_config(page_title="Leadradar", page_icon="⚡", layout="wide")


def laad_profielnamen() -> list[str]:
    return sorted(p.name for p in PROFIELEN_MAP.glob("*.yaml"))


st.title("⚡ Leadradar")
st.caption("Upload een gefilterde bedrijvenlijst, kies een profiel, krijg een gescoorde leadlijst terug.")

with st.sidebar:
    st.header("1. Profiel")
    profielnamen = laad_profielnamen()
    if not profielnamen:
        st.error("Geen profiel gevonden in de map 'profiles/'.")
        st.stop()
    gekozen = st.selectbox("Kies een profiel", profielnamen)
    profiel = Profile.from_yaml(PROFIELEN_MAP / gekozen)
    with st.expander("Profieldetails", expanded=False):
        st.write(f"**Sectoren:** {', '.join(profiel.sectoren) or '—'}")
        st.write(f"**SBI-codes:** {', '.join(profiel.sbi_codes) or '—'}")
        st.write(f"**Grootte:** {profiel.grootte_min}–{profiel.grootte_max} medewerkers")
        st.write(f"**Regio:** {', '.join(profiel.regio_plaatsen) or profiel.regio_omschrijving or '—'}")
        st.write(f"**Signalen:** {', '.join(profiel.signalen) or '—'}")

    st.header("2. KvK-verrijking (optioneel)")
    kvk_aan = st.checkbox(
        "Verrijk elk resultaat extra met de officiële KvK Basisprofiel-API",
        value=False,
        help="Vult officiële naam en medewerkersaantal aan. Vereist een KvK API-key voor echte "
        "resultaten — zonder key gebruikt dit de testomgeving met beperkte testdata.",
    )
    kvk_key = None
    if kvk_aan:
        kvk_key = st.text_input("KvK API-key", type="password")

    st.header("3. Contactpersoon + signalen (optioneel)")
    website_aan = st.checkbox(
        "Zoek per bedrijf op de eigen website naar een vacature-elektromonteur-signaal en een "
        "contactpersoon",
        value=False,
        help="Bezoekt alleen de eigen, publieke website van het bedrijf zelf (geen LinkedIn of "
        "andere platforms). Werkt alleen als er al een website-URL bekend is — Google Places "
        "vult die altijd, OpenKvK niet gegarandeerd. Dit is een heuristiek: behandel elk gevonden "
        "resultaat als 'te verifiëren', niet als vaststaand feit. 'Geen eigen elektrotechnicus' "
        "wordt hier niet gedetecteerd — dat blijft iets om zelf te bevestigen op de shortlist.",
    )

    st.header("4. Concept eerste bericht (optioneel)")
    outreach_aan = st.checkbox(
        "Genereer per bedrijf een concept eerste bericht",
        value=False,
        help="Nog geen 'Gilberts stijl' — een neutraal sjabloon om op te stellen. Altijd checken "
        "en aanpassen voor je het verstuurt.",
    )
    outreach_sjabloon = STANDAARD_SJABLOON
    if outreach_aan:
        outreach_sjabloon = st.text_area(
            "Sjabloon (placeholders: {aanhef}, {bedrijfsnaam}, {sector}, {signaal_zin})",
            value=STANDAARD_SJABLOON,
            height=220,
        )

st.header("5. Bedrijvenlijst")
bron_keuze = st.radio(
    "Hoe wil je bedrijven verzamelen?",
    [
        "Automatisch zoeken (OpenKvK)",
        "Automatisch zoeken (Google Places)",
        "CSV uploaden (handmatige export)",
    ],
    help="OpenKvK zoekt op officiële SBI-code — sterk voor B2B-industrie. Google Places "
    "zoekt op vrije tekst zoals een consument dat zou doen — sterker voor lokaal vindbare "
    "bedrijven (winkels, installateurs, dienstverleners). CSV kost geen account.",
)

openkvk_key = None
google_key = None
bestand = None
gebruik_voorbeeld = False

if bron_keuze == "Automatisch zoeken (OpenKvK)":
    openkvk_key = st.text_input(
        "OpenKvK / overheid.io API-key",
        type="password",
        help="Gratis account op overheid.io geeft alleen een willekeurige testset van 10.000 "
        "bedrijven. Voor echte, gefilterde resultaten op je profiel is het 'Small'-abonnement "
        "nodig (€15/maand, 2.500 calls) — zie overheid.io/abonnementen.",
    )
    st.caption(
        f"Zoekt op: sectoren/SBI {profiel.sbi_codes or profiel.sectoren} × plaatsen "
        f"{profiel.regio_plaatsen or '(geen plaatsen ingesteld in dit profiel)'}."
    )
elif bron_keuze == "Automatisch zoeken (Google Places)":
    google_key = st.text_input(
        "Google Places API-key",
        type="password",
        help="Aan te vragen via console.cloud.google.com/google/maps-apis — facturering moet "
        "aanstaan, maar er is doorgaans een maandelijks tegoed (controleer het actuele bedrag "
        "in je Cloud Console). Zoekt op vrije tekst, geen SBI-code nodig.",
    )
    st.caption(
        f"Zoekt op: sectoren {profiel.sectoren} × plaatsen "
        f"{profiel.regio_plaatsen or '(geen plaatsen ingesteld in dit profiel)'} "
        f"(bijv. \"{(profiel.sectoren or ['...'])[0]} in {(profiel.regio_plaatsen or ['...'])[0]}, Nederland\")."
    )
else:
    st.write(
        "Exporteer een gefilterde lijst vanaf bedrijvenopdekaart.nl (of een vergelijkbare bron) naar CSV, "
        "met kolommen: `bedrijfsnaam, plaats, postcode, sector, grootte_indicatie, "
        "vacature_elektromonteur, geen_eigen_elektrotechnicus, website, bron`."
    )
    bestand = st.file_uploader("CSV-bestand", type=["csv"])
    if bestand is None:
        gebruik_voorbeeld = st.checkbox("Ik heb nog geen export — gebruik voorbeelddata om de tool te proberen")

kan_genereren = bool(openkvk_key) or bool(google_key) or bestand is not None or gebruik_voorbeeld
genereer = st.button("Genereer leadlijst", type="primary", disabled=not kan_genereren)

if genereer:
    with st.spinner("Bezig met verwerken..."):
        if openkvk_key:
            client = OpenKvkClient(apikey=openkvk_key)
            bedrijven = client.zoek(profiel)
        elif google_key:
            client = GooglePlacesClient(apikey=google_key)
            bedrijven = client.zoek(profiel)
        elif bestand is not None:
            tijdelijk_pad = Path("/tmp/leadradar_upload.csv")
            tijdelijk_pad.write_bytes(bestand.getvalue())
            bedrijven = laad_csv(tijdelijk_pad)
        else:
            bedrijven = laad_csv(BASISPAD / "data" / "voorbeeld_export.csv")

        if kvk_aan:
            client = KvkClient(apikey=kvk_key) if kvk_key else KvkClient()
            bedrijven = [client.verrijk(b) for b in bedrijven]

        if website_aan:
            website_client = WebsiteEnricher()
            bedrijven = [website_client.verrijk(b, gewenste_signalen=profiel.signalen) for b in bedrijven]

        bedrijven = [score_bedrijf(b, profiel) for b in bedrijven]
        bedrijven.sort(key=lambda b: b.score or 0, reverse=True)

        if outreach_aan:
            for b in bedrijven:
                b.concept_bericht = genereer_bericht(b, profiel, sjabloon=outreach_sjabloon)

        excel_pad = Path("/tmp/leadradar_output.xlsx")
        schrijf_excel(bedrijven, excel_pad)

    st.success(f"{len(bedrijven)} bedrijven verwerkt — beste match bovenaan.")

    weergave = [
        {
            "Bedrijf": b.bedrijfsnaam,
            "Plaats": b.plaats,
            "Score": b.score,
            "Match-reden": "; ".join(b.match_redenen),
            "Contactpersoon": b.contactpersoon or ("— (niet gevonden)" if website_aan else "— (website-check uit)"),
            "KvK-status": b.kvk_status,
            "Website-verrijking": b.website_status,
        }
        for b in bedrijven
    ]
    st.dataframe(weergave, use_container_width=True, hide_index=True)

    if outreach_aan:
        with st.expander("Concept berichten bekijken (eerste 5)", expanded=False):
            for b in bedrijven[:5]:
                st.markdown(f"**{b.bedrijfsnaam}**")
                st.text(b.concept_bericht)
                st.divider()

    st.download_button(
        "⬇ Download Excel",
        data=excel_pad.read_bytes(),
        file_name="leads.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
