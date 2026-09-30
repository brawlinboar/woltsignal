"""Kraków neighborhood lookup. The MSIP download is the source; the parquet is its cache."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ADRESY_PARQUET = Path(__file__).resolve().parents[1] / "data" / "adresy_msip.parquet"
MSIP_WFS = (
    "https://msip3.um.krakow.pl/server/services/Pobieranie/Adresy/MapServer/WFSServer"
)


def format_postal_series(series):
    """Write a 5-digit postcode as ##-###. 30127 and 30-127 become 30-127."""
    text = series.astype("string").str.strip()
    digits = text.str.replace(r"\D", "", regex=True)
    formatted = digits.str.slice(0, 2) + "-" + digits.str.slice(2)
    return formatted.where(digits.str.len().eq(5), text)


def download_address_points(dest=ADRESY_PARQUET, page_size=1000):
    """Download Kraków address points from the MSIP WFS for dataset 1492.

    Layer Adresy:Punkty_adresowe. Same columns as the xlsx export.
    """
    frames = []
    start = 0
    while True:
        query = urllib.parse.urlencode(
            {
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeNames": "Adresy:Punkty_adresowe",
                "outputFormat": "GEOJSON",
                "count": page_size,
                "startIndex": start,
            }
        )
        request = urllib.request.Request(
            f"{MSIP_WFS}?{query}",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.load(response)
        features = payload.get("features") or []
        if not features:
            break
        frames.append(pd.DataFrame(feature["properties"] for feature in features))
        start += len(features)
        if len(features) < page_size:
            break
    points = pd.concat(frames, ignore_index=True)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    points.to_parquet(dest, index=False)
    return dest


def neighborhood_by_postal(path=ADRESY_PARQUET):
    """##-### postcode -> neighborhood with strictly more houses.

    Address points come from the MSIP WFS. A postcode maps to the dzielnica
    that contains more of its houses. An equal count stays unmapped.
    """
    addr = pd.read_parquet(path, columns=["kod_pocztowy", "nazwa_dzielnicy"])
    addr["postal"] = format_postal_series(addr["kod_pocztowy"])
    addr["nazwa_dzielnicy"] = addr["nazwa_dzielnicy"].astype("string").str.strip().str.upper()
    counts = (
        addr.groupby(["postal", "nazwa_dzielnicy"], dropna=False)
        .size()
        .reset_index(name="n_houses")
    )
    counts["rank"] = counts.groupby("postal")["n_houses"].rank(method="min", ascending=False)
    winners = counts.loc[counts["rank"].eq(1)]
    tied = winners["postal"].duplicated(keep=False)
    winners = winners.loc[~tied]
    return winners.set_index("postal")["nazwa_dzielnicy"]


def krakow_postal_codes(path=ADRESY_PARQUET):
    """Every ##-### postcode in the Kraków address file, including ties."""
    addr = pd.read_parquet(path, columns=["kod_pocztowy"])
    return set(format_postal_series(addr["kod_pocztowy"]).dropna())


def ensure_address_points(path=ADRESY_PARQUET):
    """Download from MSIP when the cache is absent, then return the path."""
    if not Path(path).exists():
        download_address_points(path)
    return Path(path)
