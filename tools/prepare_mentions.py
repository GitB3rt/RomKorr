"""Liest die im Brieftext *erwähnten* Orte aus dem Register der Briefseiten.

Jede Briefseite führt unter „Register" die im Text vorkommenden Orte, Personen
und Werke. Das ist eine andere Geografie als Absende- und Empfangsort: nicht
wohin die Briefe liefen, sondern worüber gesprochen wurde. Die Edition kennt
457 solcher Orte gegenüber 170 Postorten.

Die Angaben stehen als Kommentar im HTML und enthalten je Ort eine ID sowie
GND- und GeoNames-Nummer — damit lassen sich die Koordinaten über dieselbe
Kaskade auflösen wie in Notebook 02, und das Ergebnis landet im selben
Verzeichnis `data/raw/place_coords.csv`.

Gelesen wird aus dem lokalen Seiten-Cache des Scrapers (Notebook 01, Ort per
`ROMKORR_CACHE` steuerbar), es geht also kein zusätzlicher Abruf an die Edition. Nur für Orte, die noch keine Koordinate
haben, werden GeoNames bzw. lobid befragt.

Aufruf:
    python tools/prepare_mentions.py [cache-verzeichnis]
"""
from __future__ import annotations

import csv
import os
import re
import sys
import time
from pathlib import Path

import requests


def cache_vorgabe() -> Path:
    """Derselbe Seiten-Cache wie in Notebook 01 (ROMKORR_CACHE schlaegt alles)."""
    vorgabe = os.environ.get("ROMKORR_CACHE")
    if vorgabe:
        return Path(vorgabe) / "html"
    lokal = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME")
    if lokal:
        return Path(lokal) / "romkorr_scrape_cache" / "html"
    return Path.home() / ".cache" / "romkorr" / "html"


CACHE_VORGABE = cache_vorgabe()
UA = {"User-Agent": "RomKorr/1.0 (research; contact: robert.metzner@posteo.de)"}
PAUSE = 0.4

RE_LI = re.compile(r'<li class="list-group-item">')
RE_ITEM = re.compile(r"<!--itemmArray\s*\((.*?)\)\s*-->", re.DOTALL)
RE_ID = re.compile(r"\[ID\]\s*=>\s*(\d+)")
RE_NAME = re.compile(r"\[content\]\s*=>\s*(.*)")
RE_GND = re.compile(r"\[gnd\]\s*=>\s*([0-9X\-]+)")
RE_GEO = re.compile(r"\[geonames\]\s*=>\s*(\d+)")


def find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "data").is_dir():
            return p
    raise RuntimeError(f"Projekt-Root nicht gefunden ab: {start}")


def orte_der_seite(html: str) -> list[dict]:
    """Erwähnte Orte einer Briefseite aus dem Register-Reiter."""
    i = html.find('id="index-tab-pane"')
    if i < 0:
        return []
    j = html.find(">Orte</h5>", i)
    if j < 0:
        return []
    k = html.find("<h5", j + 10)          # bis zur nächsten Rubrik
    block = html[j:k if k > 0 else len(html)]

    treffer = []
    for teil in RE_LI.split(block)[1:]:
        m = RE_ITEM.search(teil)          # nur der erste Block je Eintrag
        if not m:
            continue
        roh = m.group(1)
        mid, mname = RE_ID.search(roh), RE_NAME.search(roh)
        if not mid or not mname:
            continue
        name = mname.group(1).strip()
        if not name:
            continue
        mgnd, mgeo = RE_GND.search(roh), RE_GEO.search(roh)
        treffer.append({
            "place_id": mid.group(1),
            "place": name,
            "gnd": f"https://d-nb.info/gnd/{mgnd.group(1)}" if mgnd else "",
            "geonames": f"https://www.geonames.org/{mgeo.group(1)}" if mgeo else "",
        })
    return treffer


def coords_geonames(url: str):
    m = re.search(r"geonames\.org/(\d+)", url or "")
    if not m:
        return None
    r = requests.get(f"https://sws.geonames.org/{m.group(1)}/about.rdf", headers=UA, timeout=20)
    r.raise_for_status()
    lat = re.search(r"<wgs84_pos:lat>([-+0-9.]+)</wgs84_pos:lat>", r.text)
    lon = re.search(r"<wgs84_pos:long>([-+0-9.]+)</wgs84_pos:long>", r.text)
    return (float(lat.group(1)), float(lon.group(1))) if lat and lon else None


def coords_gnd(url: str):
    m = re.search(r"d-nb\.info/gnd/([0-9X\-]+)", url or "")
    if not m:
        return None
    r = requests.get(f"https://lobid.org/gnd/{m.group(1)}.json", headers=UA, timeout=20)
    r.raise_for_status()
    geo = r.json().get("hasGeometry")
    if isinstance(geo, list):
        geo = geo[0] if geo else None
    for wkt in (geo or {}).get("asWKT") or []:
        pm = re.search(r"Point\s*\(\s*([-+0-9.]+)\s+([-+0-9.]+)\s*\)", wkt)
        if pm:
            return float(pm.group(2)), float(pm.group(1))
    return None


def schluessel(place: str, geonames: str, gnd: str) -> list[str]:
    """Wie in Notebook 02: GeoNames-URL, sonst GND-URL, sonst Name."""
    keys = [u for u in (geonames, gnd) if u]
    if place:
        keys.append(f"name:{place}")
    return keys


def main() -> int:
    root = find_project_root(Path(__file__).resolve())
    cache = Path(sys.argv[1]) if len(sys.argv) > 1 else CACHE_VORGABE
    if not cache.is_dir():
        print(f"Cache nicht gefunden: {cache}")
        return 1

    ziel = root / "data" / "raw" / "mentions.csv"
    verzeichnis = root / "data" / "raw" / "place_coords.csv"

    dateien = sorted(cache.glob("*.html"), key=lambda p: int(p.stem) if p.stem.isdigit() else 0)
    print(f"Lese {len(dateien)} Seiten aus {cache} ...")

    zeilen, orte = [], {}
    ohne_register = 0
    for f in dateien:
        html = f.read_text(encoding="utf-8", errors="ignore")
        if 'id="metadata-tab-pane"' not in html:
            continue
        treffer = orte_der_seite(html)
        if not treffer:
            ohne_register += 1
            continue
        for t in treffer:
            zeilen.append({"letter_id": f.stem, **t})
            orte.setdefault(t["place_id"], t)

    print(f"  {len(zeilen)} Erwähnungen in {len({z['letter_id'] for z in zeilen})} Briefen")
    print(f"  {len(orte)} verschiedene Orte; {ohne_register} Briefe ohne Ortsnennung")

    # Koordinaten: was im Verzeichnis steht, wird nicht erneut geholt
    spalten = ["key", "place", "geonames_url", "gnd_url", "lat", "lon", "source"]
    bestand = list(csv.DictReader(verzeichnis.open(encoding="utf-8"))) if verzeichnis.exists() else []
    bekannt = {r["key"]: r for r in bestand if r.get("lat") and r.get("lon")}
    print(f"  im Ortsverzeichnis bereits bekannt: {len(bekannt)} Schlüssel")

    neu, offen = [], 0
    for t in orte.values():
        keys = schluessel(t["place"], t["geonames"], t["gnd"])
        if any(k in bekannt for k in keys):
            continue
        lat = lon = None
        quelle = "none"
        try:
            if t["geonames"]:
                got = coords_geonames(t["geonames"])
                if got:
                    lat, lon, quelle = got[0], got[1], "geonames"
            if lat is None and t["gnd"]:
                got = coords_gnd(t["gnd"])
                if got:
                    lat, lon, quelle = got[0], got[1], "gnd"
        except Exception as e:
            print(f"    [WARN] {t['place']}: {e}")
        if lat is None:
            offen += 1
        else:
            bekannt[keys[0]] = {"lat": lat, "lon": lon}
        neu.append({"key": keys[0], "place": t["place"], "geonames_url": t["geonames"],
                    "gnd_url": t["gnd"], "lat": lat if lat is not None else "",
                    "lon": lon if lon is not None else "", "source": quelle})
        time.sleep(PAUSE)

    if neu:
        alle = bestand + neu
        gesehen, sauber = set(), []
        for r in alle:                       # letzter Eintrag je Schlüssel gewinnt
            sauber = [x for x in sauber if x["key"] != r["key"]]
            sauber.append(r)
        sauber.sort(key=lambda r: (r["place"], r["key"]))
        with verzeichnis.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=spalten)
            w.writeheader()
            w.writerows(sauber)
        print(f"  {len(neu)} Ort(e) ergänzt, davon {offen} ohne Koordinate "
              f"-> {verzeichnis.name}")

    with ziel.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["letter_id", "place_id", "place", "gnd", "geonames"])
        w.writeheader()
        w.writerows(zeilen)
    print(f"Geschrieben: {ziel.name} — {len(zeilen)} Zeilen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
