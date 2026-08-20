"""Prueft die Passpunkte einer Allmaps-Georeferenzierung auf Widersprueche.

Hintergrund: Eine affine Transformation (polynomial, Ordnung 1) mittelt Fehler
weg — ein falsch gesetzter Passpunkt faellt dort kaum auf. Thin Plate Spline
zwingt die Karte dagegen exakt durch jeden Passpunkt; ein widerspruechlicher
Punkt erzeugt dann eine lokale Faltung im Kartenbild (siehe tps_fold.py).

Zwei Tests:

1. Leave-one-out: Fuer jeden Punkt wird aus seinen naechsten Nachbarn eine
   affine Abbildung geschaetzt und der Punkt selbst vorhergesagt. Grosse
   Abweichung = passt nicht zur Nachbarschaft. Achtung: Am Kartenrand sind
   grosse Werte normal, weil die alte Karte dort selbst ungenau ist.
2. Nord/Sued-Widerspruch: Liegt ein Punkt im Scan oberhalb eines Nachbarn,
   muss er auch noerdlicher liegen. Verstoesse sind fast immer echte Fehler
   und der beste Hinweis auf eine Verwechslung.

Aufruf:
    python tools/check_gcps.py [pfad/zur/annotation.json]

Exit-Code 1, wenn Nord/Sued-Widerspruecke gefunden wurden.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

K_NEIGHBOURS = 8      # Nachbarn fuer die lokale Schaetzung
MAX_DX = 400          # nur benachbarte Punkte vergleichen (Bildpixel)
MIN_DY, MAX_DY = 20, 400


def find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "data").is_dir():
            return p
    raise RuntimeError(f"Projekt-Root nicht gefunden ab: {start}")


def to_mercator(lon: float, lat: float) -> tuple[float, float]:
    """Web-Mercator-Meter — die Projektion, in der die Kacheln gerendert werden."""
    x = 6378137.0 * math.radians(lon)
    y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y


def fit_affine(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    A = np.hstack([src, np.ones((len(src), 1))])
    sol, *_ = np.linalg.lstsq(A, dst, rcond=None)
    return sol


def apply_affine(sol: np.ndarray, pts: np.ndarray) -> np.ndarray:
    return np.hstack([pts, np.ones((len(pts), 1))]) @ sol


def main() -> int:
    root = find_project_root(Path(__file__).resolve())
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "data" / "raw" / "georef_map.json"

    anno = json.loads(path.read_text(encoding="utf-8"))
    body = anno["items"][0]["body"]
    img = np.array([f["properties"]["resourceCoords"] for f in body["features"]], float)
    geo = np.array([f["geometry"]["coordinates"] for f in body["features"]], float)
    n = len(img)

    print(f"Annotation:      {path.name}")
    print(f"Transformation:  {body.get('transformation')}")
    print(f"Passpunkte:      {n}\n")

    merc = np.array([to_mercator(lo, la) for lo, la in geo])
    # Mercator dehnt mit 1/cos(lat); damit werden die Abweichungen echte Kilometer
    scale = math.cos(math.radians(float(geo[:, 1].mean()))) / 1000.0

    res_global = np.linalg.norm(apply_affine(fit_affine(img, merc), img) - merc, axis=1) * scale

    res_local = np.zeros(n)
    for i in range(n):
        nearest = np.argsort(np.linalg.norm(img - img[i], axis=1))[1:K_NEIGHBOURS + 1]
        pred = apply_affine(fit_affine(img[nearest], merc[nearest]), img[i:i + 1])[0]
        res_local[i] = np.linalg.norm(pred - merc[i]) * scale

    print(f"Affine Passung (= polynomial):  Median {np.median(res_global):5.1f} km, "
          f"Max {res_global.max():5.1f} km")
    print(f"Lokale Passung (leave-one-out): Median {np.median(res_local):5.1f} km, "
          f"Max {res_local.max():5.1f} km\n")

    print("Auffaelligste Passpunkte (lokale Abweichung zuerst):")
    print(f"{'lokal':>7} {'affin':>7}  {'Bildkoordinate':>15}  {'lon':>9} {'lat':>8}")
    for i in np.argsort(-res_local)[:8]:
        print(f"{res_local[i]:7.1f} {res_global[i]:7.1f}  "
              f"{int(img[i][0]):7d},{int(img[i][1]):6d}  {geo[i][0]:9.4f} {geo[i][1]:8.4f}")

    print("\nNord/Sued-Widersprueche (Bildlage gegen Koordinate):")
    conflicts = 0
    for i in range(n):
        for j in range(i + 1, n):
            dy = img[i][1] - img[j][1]
            if abs(img[i][0] - img[j][0]) > MAX_DX or not (MIN_DY <= abs(dy) <= MAX_DY):
                continue
            # groesseres y = im Scan weiter unten = muss suedlicher liegen
            if (dy > 0) != (geo[i][1] < geo[j][1]):
                conflicts += 1
                km = abs(geo[i][1] - geo[j][1]) * 110.6
                print(f"  ({int(img[i][0])},{int(img[i][1])}) lat {geo[i][1]:.4f}  <->  "
                      f"({int(img[j][0])},{int(img[j][1])}) lat {geo[j][1]:.4f}"
                      f"   Bild dy={dy:+.0f} px, Differenz {km:.0f} km")
    if not conflicts:
        print("  keine gefunden")
        return 0

    print(f"\n{conflicts} Widerspruch/Widersprueche — im Allmaps-Editor pruefen.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
