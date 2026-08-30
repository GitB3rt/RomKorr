"""Bereitet die historischen Territorialgrenzen für die Karte auf.

Quelle: https://github.com/aourednik/historical-basemaps (GPL-3.0), Datei
`world_1800.geojson`. Von den verfügbaren Stützjahren (1783, 1800, 1815) passt
1800 am besten: Der Briefbestand hat seinen Median 1798, 77 % der Briefe
stammen aus 1795 oder später. Polen fehlt dort zu Recht — es war 1795 geteilt
worden; die Batavische und die Helvetische Republik entsprechen dem Stand, den
die späteren Briefe vorfanden.

Das Skript lädt die Weltdatei, schneidet sie auf den Briefraum zu, rundet die
Koordinaten und schreibt `data/raw/borders_1800.geojson`. Der Zuschnitt spart
den größten Teil der 1,8 MB; gerechnet wird mit Sutherland-Hodgman, damit keine
Geometrie-Bibliothek nötig ist.

Aufruf:
    python tools/prepare_borders.py
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

QUELLE = ("https://raw.githubusercontent.com/aourednik/historical-basemaps/"
          "master/geojson/world_1800.geojson")

# Briefraum mit Rand: die Orte liegen (ohne Madras) zwischen -2,7 und 26 Grad
# Länge sowie 40,8 und 58 Grad Breite.
AUSSCHNITT = (-12.0, 36.0, 32.0, 61.0)   # xmin, ymin, xmax, ymax
STELLEN = 4                               # Nachkommastellen (~11 m)
MIN_PUNKTE = 4                            # kleinere Ringe sind Rauschen


def find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "data").is_dir():
            return p
    raise RuntimeError(f"Projekt-Root nicht gefunden ab: {start}")


def clip_ring(ring: list, rect: tuple) -> list:
    """Schneidet einen Polygonring am Rechteck zu (Sutherland-Hodgman)."""
    xmin, ymin, xmax, ymax = rect

    def drin(p, kante):
        x, y = p
        return (x >= xmin, x <= xmax, y >= ymin, y <= ymax)[kante]

    def schnitt(p, q, kante):
        (x1, y1), (x2, y2) = p, q
        if kante in (0, 1):
            xe = xmin if kante == 0 else xmax
            t = (xe - x1) / (x2 - x1)
            return [xe, y1 + t * (y2 - y1)]
        ye = ymin if kante == 2 else ymax
        t = (ye - y1) / (y2 - y1)
        return [x1 + t * (x2 - x1), ye]

    aus = [list(p[:2]) for p in ring]
    for kante in range(4):
        if not aus:
            return []
        ein, aus = aus, []
        for i in range(len(ein)):
            akt, vor = ein[i], ein[i - 1]
            a_drin, v_drin = drin(akt, kante), drin(vor, kante)
            if a_drin:
                if not v_drin:
                    aus.append(schnitt(vor, akt, kante))
                aus.append(akt)
            elif v_drin:
                aus.append(schnitt(vor, akt, kante))
    return aus


def flaeche(ring: list) -> float:
    s = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i - 1][:2]
        x2, y2 = ring[i][:2]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def schwerpunkt(ring: list) -> list:
    """Flächenschwerpunkt - Ankerpunkt für die Beschriftung."""
    cx = cy = a = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i - 1][:2]
        x2, y2 = ring[i][:2]
        f = x1 * y2 - x2 * y1
        a += f
        cx += (x1 + x2) * f
        cy += (y1 + y2) * f
    if a == 0:
        return list(ring[0][:2])
    a *= 0.5
    return [round(cx / (6 * a), STELLEN), round(cy / (6 * a), STELLEN)]


def polygone(geom: dict) -> list:
    """Vereinheitlicht Polygon und MultiPolygon zu einer Liste von Polygonen."""
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return list(geom["coordinates"])
    return []


def main() -> None:
    root = find_project_root(Path(__file__).resolve())
    ziel = root / "data" / "raw" / "borders_1800.geojson"

    print(f"Lade {QUELLE.rsplit('/', 1)[-1]} ...")
    with urllib.request.urlopen(QUELLE, timeout=60) as r:
        welt = json.loads(r.read().decode("utf-8"))
    print(f"  {len(welt['features'])} Gebiete weltweit")

    # Gleichnamige Gebiete zusammenfassen: Preußen, Anhalt und Braunschweig
    # liegen in der Quelle als mehrere Flächen vor (sie waren zersplittert).
    # Als ein Gebiet mit mehreren Flächen bekommen sie auch nur eine Beschriftung.
    gesammelt: dict[str, list] = {}
    for f in welt["features"]:
        name = f["properties"].get("NAME")
        if not name or name in ("None", None):
            continue

        neue_polys = []
        for poly in polygone(f.get("geometry") or {}):
            ringe = []
            for ring in poly:
                geschnitten = clip_ring(ring, AUSSCHNITT)
                if len(geschnitten) >= MIN_PUNKTE:
                    ringe.append([[round(x, STELLEN), round(y, STELLEN)]
                                  for x, y in geschnitten])
            if ringe:
                neue_polys.append(ringe)

        if not neue_polys:
            continue
        gesammelt.setdefault(str(name), []).extend(neue_polys)

    ausgabe = []
    for name, polys in sorted(gesammelt.items()):
        groesster = max((r[0] for r in polys), key=flaeche)
        a = flaeche(groesster)
        # Ab welcher Zoomstufe die Beschriftung erscheint: grosse Gebiete frueh,
        # Kleinstaaten wie Waldeck oder Lippe erst, wenn Platz dafuer da ist.
        minzoom = next(z for grenze, z in ((20, 4), (5, 5), (1, 6), (0.2, 7))
                       if a > grenze) if a > 0.2 else 8
        ausgabe.append({
            "type": "Feature",
            "properties": {"name": name, "label": schwerpunkt(groesster),
                           "flaechen": len(polys), "minzoom": minzoom},
            "geometry": {"type": "MultiPolygon", "coordinates": polys},
        })
    ziel.write_text(
        json.dumps({"type": "FeatureCollection", "features": ausgabe},
                   ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")

    kb = ziel.stat().st_size / 1024
    print(f"Geschrieben: {ziel.name} — {len(ausgabe)} Gebiete, {kb:.0f} KB")
    print("Gebiete:", ", ".join(f["properties"]["name"] for f in ausgabe[:12]), "...")


if __name__ == "__main__":
    main()
