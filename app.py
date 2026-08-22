from __future__ import annotations

from pathlib import Path

import pandas as pd
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
from leadradar.store import STATUSSEN, LeadStore, row_naar_company

BASISPAD = Path(__file__).parent
PROFIELEN_MAP = BASISPAD / "profiles"

st.set_page_config(page_title="Leadradar", page_icon="⚡", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 2.5rem; max-width: 1150px; }
    h1 { font-weight: 700; letter-spacing: -0.02em; }
    [data-testid="stMetric"] {
        background: rgba(127, 127, 127, 0.07);
        border: 1px solid rgba(127, 127, 127, 0.15);
        border-radius: 0.75rem;
        padding: 0.9rem 1rem 0.6rem;
    }
    .stepnr {
        display: inline-flex; align-items: center; justify-content: center;
        width: 1.6rem; height: 1.6rem; border-radius: 50%;
        background: #FF4B4B; color: white; font-size: 0.85rem; font-weight: 700;
        margin-right: 0.5rem;
    }
    .step-title { font-size: 1.15rem; font-weight: 650; display: flex; align-items: center; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def _store() -> LeadStore:
    return LeadStore()


def laad_profielnamen() -> list[str]:
    return sorted(p.name for p in PROFIELEN_MAP.glob("*.yaml"))


def stap_titel(nummer: int, tekst: str) -> None:
    st.markdown(
        f'<div class="step-title"><span class="stepnr">{nummer}</span>{tekst}</div>',
        unsafe_allow_html=True,
    )


store = _store()

st.title("⚡ Leadradar")
st.caption(
    "Haal leads binnen op basis van een klantprofiel, en beheer ze daarna — status bijwerken, "
    "niet-interessante leads wegfilteren, gefilterd exporteren. Geen handmatig Excel-werk meer."
)

tab_zoeken, tab_beheren = st.tabs(["🔍 Nieuwe leads zoeken", "📋 Mijn leads"])

# ============================================================================
# TAB 1 — nieuwe leads zoeken en toevoegen aan "Mijn leads"
# ============================================================================
with tab_zoeken:
    st.write("")
    stap_titel(1, "Kies een klantprofiel")
    profielnamen = laad_profielnamen()
    if not profielnamen:
        st.error("Geen profiel gevonden in de map 'profiles/'.")
        st.stop()

    col_kies, col_details = st.columns([1, 2], gap="large")
    with col_kies:
        gekozen = st.selectbox("Profiel", profielnamen, label_visibility="collapsed")
        profiel = Profile.from_yaml(PROFIELEN_MAP / gekozen)
    with col_details:
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            c1.metric("Grootte", f"{profiel.grootte_min}–{profiel.grootte_max}", "medewerkers")
            c2.metric("Plaatsen", len(profiel.regio_plaatsen) or "—")
            c3.metric("Signalen", len(profiel.signalen) or "—")
            st.caption(
                f"**Sectoren:** {', '.join(profiel.sectoren) or '—'}  \n"
                f"**SBI-codes:** {', '.join(profiel.sbi_codes) or '—'}  \n"
                f"**Regio:** {', '.join(profiel.regio_plaatsen) or profiel.regio_omschrijving or '—'}"
            )

    st.write("")
    stap_titel(2, "Koppel een bron — hier komen je leads vandaan")
    bron_keuze = st.radio(
        "Bron",
        [
            "Automatisch zoeken (OpenKvK)",
            "Automatisch zoeken (Google Places)",
            "CSV uploaden (handmatige export)",
        ],
        horizontal=True,
        label_visibility="collapsed",
    )

    openkvk_key = None
    google_key = None
    bestand = None
    gebruik_voorbeeld = False

    with st.container(border=True):
        if bron_keuze == "Automatisch zoeken (OpenKvK)":
            openkvk_key = st.text_input(
                "OpenKvK / overheid.io API-key",
                type="password",
                placeholder="Plak hier je API-key",
                help="Gratis account op overheid.io geeft alleen een willekeurige testset van "
                "10.000 bedrijven. Voor echte, gefilterde resultaten op je profiel is het "
                "'Small'-abonnement nodig (€15/maand, 2.500 calls) — zie overheid.io/abonnementen.",
            )
            st.caption(
                f"Zoekt automatisch op **SBI-code** {profiel.sbi_codes or profiel.sectoren} × "
                f"**plaats** {profiel.regio_plaatsen or '(geen plaatsen ingesteld in dit profiel)'} "
                "— de gefilterde resultaten komen er direct uit en worden bewaard in 'Mijn leads'."
            )
        elif bron_keuze == "Automatisch zoeken (Google Places)":
            google_key = st.text_input(
                "Google Places API-key",
                type="password",
                placeholder="Plak hier je API-key",
                help="Aan te vragen via console.cloud.google.com/google/maps-apis — facturering "
                "moet aanstaan, maar er is doorgaans een maandelijks tegoed (controleer het "
                "actuele bedrag in je Cloud Console). Zoekt op vrije tekst, geen SBI-code nodig.",
            )
            st.caption(
                f"Zoekt automatisch op **sector** {profiel.sectoren} × "
                f"**plaats** {profiel.regio_plaatsen or '(geen plaatsen ingesteld in dit profiel)'} "
                f"(bijv. \"{(profiel.sectoren or ['...'])[0]} in "
                f"{(profiel.regio_plaatsen or ['...'])[0]}, Nederland\") — de gefilterde resultaten "
                "komen er direct uit en worden bewaard in 'Mijn leads'."
            )
        else:
            st.caption(
                "Exporteer een gefilterde lijst vanaf bedrijvenopdekaart.nl (of een vergelijkbare "
                "bron) naar CSV, met kolommen: `bedrijfsnaam, plaats, postcode, sector, "
                "grootte_indicatie, vacature_elektromonteur, geen_eigen_elektrotechnicus, "
                "website, bron`."
            )
            bestand = st.file_uploader("CSV-bestand", type=["csv"], label_visibility="collapsed")
            if bestand is None:
                gebruik_voorbeeld = st.checkbox(
                    "Ik heb nog geen export — gebruik voorbeelddata om de tool te proberen"
                )

    st.write("")
    with st.expander("3. Extra verrijking (optioneel)", expanded=False):
        t1, t2 = st.columns(2)
        with t1:
            kvk_aan = st.toggle("KvK Basisprofiel — officiële naam + medewerkersaantal")
            kvk_key = None
            if kvk_aan:
                kvk_key = st.text_input("KvK API-key", type="password", key="kvk_key_input")

            website_aan = st.toggle("Website-verrijking — vacature-signaal + contactpersoon")
            if website_aan:
                st.caption(
                    "Bezoekt alleen de eigen, publieke website van het bedrijf (geen LinkedIn of "
                    "andere platforms). Werkt alleen als er al een website-URL bekend is. Dit is "
                    "een heuristiek — behandel elk gevonden resultaat als 'te verifiëren'. 'Geen "
                    "eigen elektrotechnicus' wordt hier niet gedetecteerd, dat blijft handmatige "
                    "beoordeling."
                )

        with t2:
            outreach_aan = st.toggle("Concept eerste bericht per bedrijf")
            outreach_sjabloon = STANDAARD_SJABLOON
            if outreach_aan:
                st.caption(
                    "Nog geen 'Gilberts stijl' — altijd checken en aanpassen voor je verstuurt."
                )
                outreach_sjabloon = st.text_area(
                    "Sjabloon (placeholders: {aanhef}, {bedrijfsnaam}, {sector}, {signaal_zin})",
                    value=STANDAARD_SJABLOON,
                    height=180,
                )

    st.write("")
    kan_genereren = bool(openkvk_key) or bool(google_key) or bestand is not None or gebruik_voorbeeld
    genereer = st.button(
        "⚡ Zoek leads en voeg toe aan 'Mijn leads'",
        type="primary",
        disabled=not kan_genereren,
        use_container_width=True,
    )
    if not kan_genereren:
        st.caption("Vul een API-key in, upload een CSV, of kies voorbeelddata om te starten.")

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
                bedrijven = [
                    website_client.verrijk(b, gewenste_signalen=profiel.signalen) for b in bedrijven
                ]

            bedrijven = [score_bedrijf(b, profiel) for b in bedrijven]
            bedrijven.sort(key=lambda b: b.score or 0, reverse=True)

            if outreach_aan:
                for b in bedrijven:
                    b.concept_bericht = genereer_bericht(b, profiel, sjabloon=outreach_sjabloon)

            store.upsert_bedrijven(bedrijven, profiel_naam=profiel.naam)

        st.success(
            f"{len(bedrijven)} bedrijven verwerkt en opgeslagen onder 'Mijn leads' → profiel "
            f"'{profiel.naam}'. Bekijk, filter en beheer ze in de tab hiernaast."
        )
        scores = [b.score or 0 for b in bedrijven]
        m1, m2, m3 = st.columns(3)
        m1.metric("Bedrijven verwerkt", len(bedrijven))
        m2.metric("Gemiddelde score", f"{(sum(scores) / len(scores)):.0f}" if scores else "—")
        m3.metric("Beste match", f"{max(scores):.0f}" if scores else "—")

# ============================================================================
# TAB 2 — leadbeheer: status bijwerken, wegfilteren, gefilterd exporteren
# ============================================================================
with tab_beheren:
    st.write("")
    profielen_in_store = store.profielnamen()
    if not profielen_in_store:
        st.info(
            "Nog geen leads opgeslagen. Ga naar '🔍 Nieuwe leads zoeken' om je eerste leadlijst "
            "te genereren — die wordt hier automatisch bewaard."
        )
    else:
        f1, f2 = st.columns([1, 2])
        with f1:
            profiel_filter = st.selectbox("Profiel", ["Alle profielen"] + profielen_in_store)
        with f2:
            toon_statussen = st.multiselect(
                "Toon statussen",
                STATUSSEN,
                default=[s for s in STATUSSEN if s != "niet interessant"],
                help="'Niet interessant' staat standaard uit, zoals afgeschreven leads die je "
                "normaal uit een Excel-lijst zou verwijderen — hier verdwijnen ze gewoon uit "
                "beeld, zonder dat je zelf rijen hoeft te wissen.",
            )

        gekozen_profiel = None if profiel_filter == "Alle profielen" else profiel_filter
        leads = store.haal_leads(profiel_naam=gekozen_profiel, statussen=toon_statussen or None)

        if not leads:
            st.warning("Geen leads binnen deze filters.")
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Zichtbaar", len(leads))
            m2.metric("Interessant", sum(1 for r in leads if r["status"] == "interessant"))
            m3.metric("Contact gelegd", sum(1 for r in leads if r["status"] == "contact gelegd"))
            m4.metric("Klant", sum(1 for r in leads if r["status"] == "klant"))

            df = pd.DataFrame(
                [
                    {
                        "id": r["id"],
                        "Verwijderen": False,
                        "Bedrijf": r["bedrijfsnaam"],
                        "Plaats": r["plaats"],
                        "Score": r["score"],
                        "Status": r["status"],
                        "Contactpersoon": r["contactpersoon"] or "—",
                        "Match-reden": r["match_redenen"] or "",
                        "Profiel": r["profiel_naam"],
                    }
                    for r in leads
                ]
            )

            bewerkt = st.data_editor(
                df,
                use_container_width=True,
                hide_index=True,
                disabled=["id", "Bedrijf", "Plaats", "Score", "Contactpersoon", "Match-reden", "Profiel"],
                column_config={
                    "id": None,
                    "Verwijderen": st.column_config.CheckboxColumn(
                        "🗑", help="Vink aan en klik op 'Verwijderen toepassen' om definitief te wissen"
                    ),
                    "Status": st.column_config.SelectboxColumn("Status", options=STATUSSEN, required=True),
                    "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
                },
                key="leads_editor",
            )

            b1, b2, b3 = st.columns([1, 1, 2])
            with b1:
                if st.button("💾 Statuswijzigingen opslaan", use_container_width=True):
                    gewijzigd = 0
                    for _, rij in bewerkt.iterrows():
                        oorspronkelijk = df.loc[df["id"] == rij["id"], "Status"].iloc[0]
                        if rij["Status"] != oorspronkelijk:
                            store.zet_status(int(rij["id"]), rij["Status"])
                            gewijzigd += 1
                    if gewijzigd:
                        st.success(f"{gewijzigd} status(sen) bijgewerkt.")
                        st.rerun()
                    else:
                        st.info("Geen statuswijzigingen om op te slaan.")
            with b2:
                te_verwijderen = bewerkt.loc[bewerkt["Verwijderen"], "id"].tolist()
                if st.button(
                    f"🗑 Verwijderen toepassen ({len(te_verwijderen)})",
                    use_container_width=True,
                    disabled=not te_verwijderen,
                ):
                    store.verwijder([int(i) for i in te_verwijderen])
                    st.success(f"{len(te_verwijderen)} lead(s) verwijderd.")
                    st.rerun()
            with b3:
                excel_pad = Path("/tmp/leadradar_mijn_leads.xlsx")
                schrijf_excel([row_naar_company(r) for r in leads], excel_pad)
                st.download_button(
                    "⬇ Download Excel (huidige weergave)",
                    data=excel_pad.read_bytes(),
                    file_name="mijn_leads.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
