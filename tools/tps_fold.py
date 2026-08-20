"""Prueft eine Allmaps-Georeferenzierung auf Faltungen der Thin-Plate-Spline.

Thin Plate Spline legt das Kartenblatt exakt durch jeden Passpunkt. Widersprechen
sich benachbarte Passpunkte, kann sich die Flaeche dabei ueberschlagen: Das
Kartenbild erscheint dort verschmiert, gespiegelt oder mit Loechern. Messbar ist
das an der Jacobi-Determinante der Abbildung — wo sie ihr Vorzeichen wechselt,
liegt eine Faltung.

Das Skript rechnet die Transformation selbst nach (unabhaengig vom Tileserver)
und meldet betroffene Bereiche in Bild- und Weltkoordinaten. Welcher Passpunkt
schuld ist, findet danach tools/check_gcps.py.

Aufruf:
    python tools/tps_fold.py [pfad/zur/annotation.json] [--step 40]

Exit-Code 1, wenn Faltungen gefunden wurden.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

DEFAULT_STEP = 40         # Rasterweite in Bildpixeln
FALLBACK_SIZE = (9406, 8127)


def find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "data").is_dir():
            return p
    raise RuntimeError(f"Projekt-Root nicht gefunden ab: {start}")


def mercator(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    x = 6378137.0 * np.radians(lon)
    y = 6378137.0 * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))
    return np.column_stack([x, y])


def inv_mercator(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lon = np.degrees(x / 6378137.0)
    lat = np.degrees(2 * np.arctan(np.exp(y / 6378137.0)) - np.pi / 2)
    return lon, lat


def kernel(r: np.ndarray) -> np.ndarray:
    """Radiale Basisfunktion der Thin Plate Spline: U(r) = r^2 * ln(r)."""
    out = np.zeros_like(r)
    nz = r > 1e-12
    out[nz] = r[nz] ** 2 * np.log(r[nz])
    return out


def solve_tps(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """Loest das TPS-Gleichungssystem; liefert [w (n x 2); a (3 x 2)]."""
    n = len(src)
    d = np.linalg.norm(src[:, None, :] - src[None, :, :], axis=2)
    P = np.hstack([np.ones((n, 1)), src])
    L = np.zeros((n + 3, n + 3))
    L[:n, :n] = kernel(d)
    L[:n, n:] = P
    L[n:, :n] = P.T
    Y = np.zeros((n + 3, 2))
    Y[:n] = dst
    return np.linalg.solve(L, Y)


def apply_tps(sol: np.ndarray, src: np.ndarray, pts: np.ndarray) -> np.ndarray:
    n = len(src)
    w, a = sol[:n], sol[n:]
    r = np.linalg.norm(pts[:, None, :] - src[None, :, :], axis=2)
    return a[0] + pts @ a[1:] + kernel(r) @ w


def jacobian_det(sol: np.ndarray, src: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """dU/dx = (2 ln r + 1) * (x - xi), analog fuer y."""
    n = len(src)
    w, a = sol[:n], sol[n:]
    diff = pts[:, None, :] - src[None, :, :]
    r = np.linalg.norm(diff, axis=2)
    fac = np.zeros_like(r)
    nz = r > 1e-12
    fac[nz] = 2 * np.log(r[nz]) + 1
    dXdx = a[1, 0] + (w[:, 0] * fac * diff[:, :, 0]).sum(axis=1)
    dXdy = a[2, 0] + (w[:, 0] * fac * diff[:, :, 1]).sum(axis=1)
    dYdx = a[1, 1] + (w[:, 1] * fac * diff[:, :, 0]).sum(axis=1)
    dYdy = a[2, 1] + (w[:, 1] * fac * diff[:, :, 1]).sum(axis=1)
    return dXdx * dYdy - dXdy * dYdx


def main() -> int:
    root = find_project_root(Path(__file__).resolve())
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    step = DEFAULT_STEP
    if "--step" in sys.argv:
        step = int(sys.argv[sys.argv.index("--step") + 1])
    path = Path(args[0]) if args else root / "data" / "raw" / "georef_map.json"

    anno = json.loads(path.read_text(encoding="utf-8"))
    item = anno["items"][0]
    body = item["body"]
    img = np.array([f["properties"]["resourceCoords"] for f in body["features"]], float)
    geo = np.array([f["geometry"]["coordinates"] for f in body["features"]], float)

    source = item.get("target", {}).get("source", {})
    width = int(source.get("width") or FALLBACK_SIZE[0])
    height = int(source.get("height") or FALLBACK_SIZE[1])

    print(f"Annotation:      {path.name}")
    print(f"Transformation:  {body.get('transformation')}")
    print(f"Passpunkte:      {len(img)}")
    print(f"Bildgroesse:     {width} x {height} px, Raster {step} px\n")

    sol = solve_tps(img, mercator(geo[:, 0], geo[:, 1]))

    gx, gy = np.meshgrid(np.arange(0, width + 1, step, dtype=float),
                         np.arange(0, height + 1, step, dtype=float))
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    det = jacobian_det(sol, img, pts)

    # Die Abbildung spiegelt global (Bild-y zeigt nach unten, Welt-y nach oben),
    # entscheidend ist daher die Abweichung vom vorherrschenden Vorzeichen.
    folded = det * np.sign(np.median(det)) < 0
    print(f"Rasterpunkte: {len(pts)}, davon gefaltet: {folded.sum()} "
          f"({100 * folded.mean():.2f} %)")

    if not folded.any():
        print("\nKeine Faltung — die Georeferenzierung ist sauber.")
        return 0

    bad = pts[folded]
    world = apply_tps(sol, img, bad)
    lon, lat = inv_mercator(world[:, 0], world[:, 1])
    print(f"\n  Bildbereich:  x {bad[:, 0].min():.0f}..{bad[:, 0].max():.0f}, "
          f"y {bad[:, 1].min():.0f}..{bad[:, 1].max():.0f}")
    print(f"  Weltbereich:  lon {np.nanmin(lon):.2f}..{np.nanmax(lon):.2f}, "
          f"lat {np.nanmin(lat):.2f}..{np.nanmax(lat):.2f}")
    print(f"  Schwerpunkt:  Bild ({bad[:, 0].mean():.0f}, {bad[:, 1].mean():.0f}) "
          f"~ lon {np.nanmean(lon):.2f}, lat {np.nanmean(lat):.2f}")
    print("\nVerursachenden Passpunkt suchen: python tools/check_gcps.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
