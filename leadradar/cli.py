from __future__ import annotations

import argparse

from .pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Leadradar — genereer een gefilterde, gescoorde bedrijvenlijst uit een export."
    )
    parser.add_argument("--profiel", required=True, help="Pad naar het profiel-YAML-bestand")
    parser.add_argument(
        "--input", required=True, help="Pad naar de input-CSV (bijv. export uit bedrijvenopdekaart.nl)"
    )
    parser.add_argument("--output", default="leads.xlsx", help="Pad naar het output .xlsx-bestand")
    parser.add_argument(
        "--geen-kvk-verrijking",
        action="store_true",
        help="Sla KvK-verrijking over (handig zonder netwerktoegang, of om snel te testen)",
    )
    args = parser.parse_args()

    bedrijven = run(
        profiel_pad=args.profiel,
        input_csv=args.input,
        output_pad=args.output,
        verrijken=not args.geen_kvk_verrijking,
    )
    print(f"{len(bedrijven)} bedrijven verwerkt -> {args.output}")


if __name__ == "__main__":
    main()
