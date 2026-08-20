from __future__ import annotations

from typing import List, Optional, Union
from pathlib import Path

from .enrich.kvk import KvkClient
from .models import Company
from .output import schrijf_excel
from .profile import Profile
from .scoring import score_bedrijf
from .sources.csv_source import laad_csv


def run(
    profiel_pad: Union[str, Path],
    input_csv: Union[str, Path],
    output_pad: Union[str, Path],
    kvk_client: Optional[KvkClient] = None,
    verrijken: bool = True,
) -> List[Company]:
    profiel = Profile.from_yaml(profiel_pad)
    bedrijven = laad_csv(input_csv)

    if verrijken:
        client = kvk_client or KvkClient()
        bedrijven = [client.verrijk(b) for b in bedrijven]

    bedrijven = [score_bedrijf(b, profiel) for b in bedrijven]
    schrijf_excel(bedrijven, output_pad)
    return bedrijven
