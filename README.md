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
- Vereinheitlichung von Personen- und Datumsangaben
- Erfassung von Quell-URLs

**Ergebnis**
- Rohdaten (CSV) in `data/raw/`
- Noch keine Geokoordinaten

Dieses Notebook muss nur neu ausgeführt werden, wenn sich die Quelldaten ändern.

---

## 2. Datenaufbereitung und Geokodierung  
### `02_RomKorr_DataPrep.ipynb`

**Zweck**
- Bereinigung und Normalisierung der Rohdaten
- Geokodierung von Absende- und Empfangsorten
- Vereinheitlichung von Ortsnamen
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
  - filterabhängiger Heatmap
  - Hotspots
  - Zeit-Animation (Jahres-Slider mit Play-Button, Einzeljahr oder kumulativ)
  - Netzwerk-Ansicht (wer schrieb wem, d3-force; Klick auf Person filtert die Karte)
  - Ergebnisliste mit Pagination
- CSV-Export der gefilterten Briefe (Excel-kompatibel, UTF-8-BOM)
- Permalink: Filterzustand steht in der URL und ist als Link teilbar

**Ergebnis**
- Statische HTML-Datei:

outputs/romkorr_map.html


Diese Datei kann direkt lokal geöffnet oder auf einer Website veröffentlicht werden.

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

- stabilen, reproduzierbaren Workflow (inkl. Harmonisierung fehlerhafter Geokodierungen)
- kombinierbare Filter: Person (Suchfeld), Ort, Jahr, Route, nur datierte Briefe
- Routen-Bündelung, filterabhängige Heatmap, Zeit-Animation
- Netzwerk-Ansicht der Korrespondenzen
- Permalinks und CSV-Export

Ideen für Erweiterungen:

- visuelle Kodierung der Korrespondenzrichtung (Pfeile oder Farbverlauf)
- gebogene Linien (trennt Hin- und Rückrichtung optisch)
- Statistik-Panel (Briefe pro Jahr zum aktuellen Filter)
- Personen-Profile (Steckbrief mit Top-Partnern und -Orten)
- Auslagerung der Briefdaten in eine separate JSON-Datei (schnelleres Laden)