# RomKorr – Interaktive Karte der Korrespondenzen der Frühromantik

**RomKorr** ist ein Python-basiertes Projekt zur Aufbereitung, Analyse und Visualisierung
von Brief-Korrespondenzen der Frühromantik. Es kann ebenso für andere Korrespondenzen genutzt und angepasst werden.

Zentrales Ergebnis ist eine **interaktive Webkarte (HTML)**, die räumliche
Korrespondenzbeziehungen sichtbar macht und über Filter explorierbar ist.

Die Karte eignet sich für **Exploration der Briefe**, **Forschung**, **Lehre** und **öffentliche Präsentation** (z. B. Einbindung auf einer Website).

---

## Projektidee

Das Projekt verfolgt drei Hauptziele:

1. **Datenintegration**  
   Sammlung und Vereinheitlichung von Briefmetadaten (Sender, Empfänger, Datum, Ort). Optional: Web-Scraping, um Daten zu erhalten.

2. **Räumliche Modellierung**  
   Geokodierung von Absende- und Empfangsorten sowie Ableitung räumlicher Beziehungen.

3. **Explorative Visualisierung**  
   Darstellung der Korrespondenzen als:
   - Linien (Absendeort → Empfangsort)
   - Heatmap und Hotspots
   - filterbare Ergebnisliste mit CSV-Export

---

## Ordnerstruktur

│
├── data/
│ ├── raw/ # Rohdaten (externe Quellen, unverändert)
│ └── processed/ # Aufbereitete Daten (zentrale Arbeitsbasis)
│ ├── letters_master.csv
│ ├── letters_master.parquet
│ └── places_agg.parquet
│
├── src/
│ └── romkorr/
│ ├── 01_RomKorr_Scraper_clean.ipynb
│ ├── 02_RomKorr_DataPrep.ipynb
│ └── 03_RomKorr_MapBuilder.ipynb
│
├── outputs/
│ ├── romkorr_map.html # Aktuelle finale Karten-HTML
│ └── alt/ # Frühere Karten-Versionen (nicht versioniert)
│
├── tools/ # Prüfwerkzeuge für die Georeferenzierung
│ ├── check_gcps.py
│ └── tps_fold.py
│
├── backup/ # Manuelle Sicherungen (nicht versioniert)
│
└── requirements.txt # Python-Abhängigkeiten

---

## Empfohlener Workflow

Die **aktuelle und aktive Pipeline** befindet sich vollständig unter:

src/romkorr/

Die Notebooks sind nummeriert und werden **in dieser Reihenfolge** ausgeführt.

---

## 1. Scraping und Rohdaten  
### `01_RomKorr_Scraper_clean.ipynb`

**Zweck**
- Sammlung bzw. Import von Briefmetadaten
- Die zu prüfenden IDs kommen aus der **`sitemap.xml`** der Edition (statt einen
  ID-Bereich zu raten); ergänzt um die IDs des letzten Laufs, weil die Sitemap
  vereinzelt Briefe auslässt
- Erfassung von Quell-URLs sowie der **Normdaten-Links je Ort** (GeoNames **und** GND),
  wie sie die Briefseiten selbst verlinken
- Zusätzlich wird die **TEI-Fassung** jedes Briefes geladen
  (`/letters/xml/<id>`): Sie enthält das Datum maschinenlesbar als `@when` —
  auch bei unscharfen Angaben wie „[vor dem 22.04.1790]" oder „Sommer 1793".
  Gelesen wird gezielt `<correspAction type="sent">`, denn der TEI-Header trägt
  unter `<publicationStmt>` ein zweites Datum (das der Veröffentlichung)
- Die Metadaten-Labels der Website werden **deutsch und englisch** erkannt; die
  Edition liefert beide Sprachfassungen gemischt aus

**Ergebnis**
- Rohdaten (CSV) in `data/raw/`, gefiltert in `data/processed/rom_korr_full_website.csv`
- Noch keine Geokoordinaten (die entstehen in 02 aus den Normdaten-Links)

Dieses Notebook muss nur neu ausgeführt werden, wenn sich die Quelldaten ändern.

---

## 2. Datenaufbereitung und Geokodierung  
### `02_RomKorr_DataPrep.ipynb`

**Zweck**
- Bereinigung und Normalisierung der Rohdaten
- Koordinaten primär aus **Normdaten** (Kaskade: GeoNames-Link → GND via lobid.org);
  Namens-Geocoding nur als dokumentierter Fallback — unaufgelöste Fälle werden geloggt.
  Ergebnisse gecacht in `data/raw/normdata_fixes.csv` (dort sind auch manuelle
  Korrekturen möglich: `lat`/`lon` eintragen, Quelle vermerken, 02 neu ausführen)
- „Unbekannt" als Ortsname erhält keine Koordinaten
- Vereinheitlichung von Ortsnamen und Harmonisierung abweichender Koordinaten
- Erzeugung einer konsistenten Master-Datei

**Ergebnis**
- `data/processed/letters_master.csv`
- `data/processed/letters_master.parquet`
- optionale Aggregationen (z. B. `places_agg.parquet`)

Diese Dateien bilden die **Grundlage aller weiteren Analysen und Visualisierungen**.

---

## 3. Karten- und Website-Generierung  
### `03_RomKorr_MapBuilder.ipynb`

**Zweck**
- Erzeugung der interaktiven Karte mit **Folium und JavaScript**
- Aufbau der Benutzeroberfläche (Sidebar)
- Filter nach:
  - Person (Suchfeld über alle Personen, findet auch Teilnamen wie „Schlegel")
  - Ort (Dropdown passt sich den übrigen Filtern dynamisch an)
  - Jahr (von / bis), optional nur datierte Briefe
- Darstellung von:
  - Korrespondenz-Routen (gebündelt; Liniendicke/Deckkraft = Briefanzahl, Klick zeigt Richtungs-Statistik)
  - filterabhängiger Heatmap (sequentielle Ein-Farbton-Rampe)
  - Hotspots als Proportionalkreise (Kreisfläche und Zahl = Briefanzahl im aktiven
    Filter — Kreise wachsen, schrumpfen und verschwinden mit Person-/Ort-/Jahresfilter
    und Zeit-Animation; benachbarte Orte verschmelzen beim Herauszoomen und teilen
    sich per Klick). Auch die Orts-Popups (Anzahl, Beispiele, Listen-Button) werden
    beim Öffnen aus dem aktiven Filter gebaut
  - Briefe mit nur einem bekannten Ort (Gegenstelle „Unbekannt") zählen am bekannten
    Endpunkt mit und erscheinen in Liste, CSV und Popups — nur ohne Linie
  - Zeit-Animation (Jahres-Slider mit Play-Button, Einzeljahr oder kumulativ)
  - Netzwerk-Ansicht (wer schrieb wem, d3-force; Klick auf Person filtert die Karte)
  - Ergebnisliste mit Pagination
- Historische Karten-Ebene: F. L. Güssefeld, „Charte das Deutsche Reich" (Nürnberg 1789,
  Homännische Erben) als zuschaltbares Overlay über der modernen Karte — Punkte, Linien
  und Heatmap bleiben darüber sichtbar, die Deckkraft ist per Regler einstellbar.
  Die Karten-Referenz stammt aus `data/raw/georef_map.json` (Allmaps-Georeferenzierungs-Annotation);
  die Kacheln liefert der Allmaps-Tileserver live aus dem IIIF-Digitalisat der
  Princeton University Library — im Repo liegen keine Kartenbilder.
  Entzerrt wird per **Thin Plate Spline** (`HIST_TRANSFORMATION`), damit das Blatt
  exakt durch die Passpunkte läuft; die affine Alternative `polynomial` weicht am
  Kartenrand um mehrere Dutzend Kilometer ab. Die Kachel-URL adressiert die
  **versionierte** Map-Referenz (`<id>@<version>`), weil der Tileserver Kacheln pro
  Map-ID 30 Tage cacht: Ohne Version kämen nach einer Korrektur im Allmaps-Editor
  weiterhin veraltete Kacheln. Umgekehrt heißt das: Nach einer Editor-Änderung muss
  `georef_map.json` neu geladen und die Karte neu gebaut werden.
- CSV-Export der gefilterten Briefe (Excel-kompatibel, UTF-8-BOM)
- Permalink: Filterzustand steht in der URL und ist als Link teilbar

**Ergebnis**
- Statische HTML-Datei:

outputs/romkorr_map.html


Diese Datei kann direkt lokal geöffnet oder auf einer Website veröffentlicht werden.

---

## Prüfwerkzeuge für die Georeferenzierung (`tools/`)

Zwei eigenständige Skripte prüfen die Allmaps-Annotation, bevor sie in die Karte geht.
Ohne Argument nehmen sie `data/raw/georef_map.json`; beide melden Funde per Exit-Code 1.

```bash
python tools/tps_fold.py     # Faltungen der Thin Plate Spline finden
python tools/check_gcps.py   # widersprüchliche Passpunkte finden
```

`tps_fold.py` rechnet die Transformation unabhängig vom Tileserver nach und sucht über
die Jacobi-Determinante nach Stellen, an denen sich das Kartenblatt überschlägt — dort
erscheint der Kartenstich verschmiert oder mit Löchern. Gemeldet wird der betroffene
Bereich in Bild- und Weltkoordinaten.

`check_gcps.py` sucht den Verursacher. Der aussagekräftigste Test ist der
Nord/Süd-Vergleich: Liegt ein Passpunkt im Scan oberhalb seines Nachbarn, muss er
auch nördlicher liegen — Verstöße sind fast immer Eingabefehler. Zusätzlich wird je
Punkt eine Leave-one-out-Abweichung gegen die Nachbarschaft berechnet. Am Kartenrand
sind große Werte dort normal, weil die Karte von 1789 selbst ungenau ist (Längengrade
waren damals fehleranfällig, Randstaaten weniger sorgfältig konstruiert).

Nützlich sind die Skripte besonders beim Wechsel auf Thin Plate Spline: Die affine
Transformation mittelt einen falschen Passpunkt weg, TPS zwingt sich exakt durch ihn
hindurch und faltet dabei die Umgebung.

---

## Hinweise zu historischen Dateien (`alt/`)

Der Ordner `alt/` enthält:
- frühere Entwicklungsstände
- Experimente
- ältere Datenformate
- ältere Karten-Versionen

Diese Dateien sind **nicht Teil der aktuellen Pipeline** und dienen ausschließlich
der Dokumentation der Projektentwicklung.

---

## Abhängigkeiten

Getestet mit Python 3.11 (Conda):

- numpy  
- pandas  
- folium  
- branca  
- requests, beautifulsoup4 (nur für das Scraping-Notebook)  
- pyarrow (Parquet-Dateien)  

Empfohlene Einrichtung:

```bash
conda create -n romkorr python=3.11
conda activate romkorr
pip install -r requirements.txt
```

---

## Veröffentlichung und Nutzung

- Die erzeugte HTML ist **statisch** (kein Server notwendig) — die eine Datei
  `outputs/romkorr_map.html` kann direkt auf einen Webspace hochgeladen werden.
- Es werden keine personenbezogenen Daten von Besuchern verarbeitet.
- Externe Inhalte (werden beim Öffnen aus dem Internet geladen):
  - OpenStreetMap-Kacheln / Leaflet (Standard-Basiskarte)
  - CARTO (alternative helle Basiskarte, im LayerControl wählbar)
  - Allmaps-Tileserver (`allmaps.xyz`) — Kacheln der historischen Karte
    (Güssefeld 1789; Digitalisat: Princeton University Library, per IIIF)
  - d3.js via jsDelivr-CDN (nur für die Netzwerk-Ansicht)
  - Verlinkungen auf öffentlich zugängliche Briefquellen (briefe-der-romantik.de)
- **Hinweis lokales Öffnen:** Beim Öffnen per Doppelklick (`file://`) blockieren
  die OSM-Server die Kacheln teilweise (fehlender Referer) — dann im LayerControl
  auf „CartoDB Positron" umschalten. Auf einer gehosteten Website tritt das
  Problem nicht auf.
- Bei Veröffentlichung sollte die Datenschutzerklärung auf externe Kartendienste,
  CDN-Einbindung und ausgehende Links hinweisen.

---

## Status und Weiterentwicklung

Der aktuelle Stand bietet:

- stabilen, reproduzierbaren Workflow (Koordinaten aus Normdaten GeoNames/GND
  statt blindem Geocoding; inkl. Harmonisierung fehlerhafter Geokodierungen)
- kombinierbare Filter: Person (Suchfeld), Ort, Jahr, Route, nur datierte Briefe
- Routen-Bündelung, filterabhängige Heatmap, Zeit-Animation
- Netzwerk-Ansicht der Korrespondenzen
- historische Karten-Ebene (Güssefeld 1789, georeferenziert mit Allmaps)
- einheitliches, validiertes Farbschema „Tinte & Preußischblau" (lesbar auf
  moderner wie historischer Karte, farbfehlsichtigkeits-geprüft)
- Permalinks und CSV-Export

Ideen für Erweiterungen:

- visuelle Kodierung der Korrespondenzrichtung (Pfeile oder Farbverlauf)
- gebogene Linien (trennt Hin- und Rückrichtung optisch)
- Statistik-Panel (Briefe pro Jahr zum aktuellen Filter)
- Personen-Profile (Steckbrief mit Top-Partnern und -Orten)
- Auslagerung der Briefdaten in eine separate JSON-Datei (schnelleres Laden)