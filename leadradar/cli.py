from __future__ import annotations

import argparse

from .pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Leadradar — genereer een gefilterde, gescoorde bedrijvenlijst."
    )
    parser.add_argument("--profiel", required=True, help="Pad naar het profiel-YAML-bestand")
    parser.add_argument("--output", default="leads.xlsx", help="Pad naar het output .xlsx-bestand")

    bron = parser.add_mutually_exclusive_group(required=True)
    bron.add_argument(
        "--openkvk-key",
        help="OpenKvK/overheid.io API-key — zoekt automatisch op sector/SBI x plaats uit het "
        "profiel, exacte match op officiële SBI-code.",
    )
    bron.add_argument(
        "--google-places-key",
        help="Google Places API-key — zoekt automatisch op vrije tekst x plaats, sterker voor "
        "lokaal vindbare bedrijven (winkels, installateurs, dienstverleners).",
    )
    bron.add_argument(
        "--input",
        help="Pad naar een handmatige CSV-export (bijv. van bedrijvenopdekaart.nl) i.p.v. "
        "automatisch zoeken.",
    )

    parser.add_argument(
        "--kvk-verrijking",
        action="store_true",
        help="Verrijk elk resultaat extra met de officiële KvK Basisprofiel-API (medewerkersaantal, "
        "officiële naam). Vereist een geldige KvK-key voor echte resultaten.",
    )
    parser.add_argument(
        "--website-verrijking",
        action="store_true",
        help="Bezoek de eigen website van elk bedrijf om een vacature-elektromonteur-signaal en een "
        "best-effort contactpersoon te vinden. Alleen mogelijk als er al een website-URL bekend is "
        "(Google Places vult die altijd; OpenKvK niet gegarandeerd).",
    )
    parser.add_argument(
        "--outreach",
        action="store_true",
        help="Genereer per bedrijf een concept eerste bericht (nog geen 'Gilberts stijl' — "
        "generiek sjabloon, altijd checken voor verzenden).",
    )
    args = parser.parse_args()

    bedrijven = run(
        profiel_pad=args.profiel,
        output_pad=args.output,
        input_csv=args.input,
        openkvk_apikey=args.openkvk_key,
        google_places_apikey=args.google_places_key,
        verrijken_kvk=args.kvk_verrijking,
        verrijken_website=args.website_verrijking,
        genereer_outreach=args.outreach,
    )
    print(f"{len(bedrijven)} bedrijven verwerkt -> {args.output}")


if __name__ == "__main__":
    main()
