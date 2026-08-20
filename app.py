from __future__ import annotations

from pathlib import Path

import streamlit as st

from leadradar.enrich.kvk import KvkClient
from leadradar.output import schrijf_excel
from leadradar.profile import Profile
from leadradar.scoring import score_bedrijf
from leadradar.sources.csv_source import laad_csv

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
        st.write(f"**Grootte:** {profiel.grootte_min}–{profiel.grootte_max} medewerkers")
        st.write(f"**Regio:** {profiel.regio_omschrijving or '—'}")
        st.write(f"**Signalen:** {', '.join(profiel.signalen) or '—'}")

    st.header("2. KvK-verrijking")
    kvk_aan = st.checkbox(
        "Verrijk met officiële KvK-gegevens",
        value=False,
        help="Vult officiële naam, SBI-code en medewerkersaantal aan. Vereist een KvK API-key. "
        "Uit laten staan werkt ook prima — dan draait de lijst puur op de brongegevens.",
    )
    kvk_key = None
    if kvk_aan:
        kvk_key = st.text_input(
            "KvK API-key",
            type="password",
            help="Leeg laten gebruikt de gedeelde KvK-testomgeving (beperkte testdata, geen echte resultaten).",
        )

st.header("3. Bedrijvenlijst")
st.write(
    "Exporteer een gefilterde lijst vanaf bedrijvenopdekaart.nl (of een vergelijkbare bron) naar CSV, "
    "met kolommen: `bedrijfsnaam, plaats, postcode, sector, grootte_indicatie, "
    "vacature_elektromonteur, geen_eigen_elektrotechnicus, website, bron`."
)
bestand = st.file_uploader("CSV-bestand", type=["csv"])
gebruik_voorbeeld = False
if bestand is None:
    gebruik_voorbeeld = st.checkbox("Ik heb nog geen export — gebruik voorbeelddata om de tool te proberen")

genereer = st.button(
    "Genereer leadlijst",
    type="primary",
    disabled=(bestand is None and not gebruik_voorbeeld),
)

if genereer:
    with st.spinner("Bezig met verwerken..."):
        if bestand is not None:
            tijdelijk_pad = Path("/tmp/leadradar_upload.csv")
            tijdelijk_pad.write_bytes(bestand.getvalue())
            bedrijven = laad_csv(tijdelijk_pad)
        else:
            bedrijven = laad_csv(BASISPAD / "data" / "voorbeeld_export.csv")

        if kvk_aan:
            client = KvkClient(apikey=kvk_key) if kvk_key else KvkClient()
            bedrijven = [client.verrijk(b) for b in bedrijven]

        bedrijven = [score_bedrijf(b, profiel) for b in bedrijven]
        bedrijven.sort(key=lambda b: b.score or 0, reverse=True)

        excel_pad = Path("/tmp/leadradar_output.xlsx")
        schrijf_excel(bedrijven, excel_pad)

    st.success(f"{len(bedrijven)} bedrijven verwerkt — beste match bovenaan.")

    weergave = [
        {
            "Bedrijf": b.bedrijfsnaam,
            "Plaats": b.plaats,
            "Score": b.score,
            "Match-reden": "; ".join(b.match_redenen),
            "KvK-status": b.kvk_status,
        }
        for b in bedrijven
    ]
    st.dataframe(weergave, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇ Download Excel",
        data=excel_pad.read_bytes(),
        file_name="leads.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
