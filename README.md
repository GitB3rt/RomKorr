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
│ └── 03_RomKorr_MapBuilder_v9.ipynb
│
├── outputs/
│ ├── romkorr_map.html # Aktuelle finale Karten-HTML
│ └── alt/ # Frühere Karten-Versionen
│
├── notebooks/ # Optionaler Arbeitsbereich
│
├── alt/ # Historische Entwicklungsstände (Archiv)
│ └── Stand24/
│
└── .ipynb_checkpoints/ # Automatisch erzeugt (nicht versionieren)

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
### `03_RomKorr_MapBuilder_v9.ipynb`

**Zweck**
- Erzeugung der interaktiven Karte mit **Folium und JavaScript**
- Aufbau der Benutzeroberfläche (Sidebar)
- Filter nach:
  - Person
  - Ort
  - Jahr (von / bis)
- Darstellung von:
  - Korrespondenz-Linien
  - Heatmap
  - Hotspots
  - Ergebnisliste mit Pagination
- CSV-Export der gefilterten Briefe

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

Empfohlene Einrichtung:

```bash
conda create -n romkorr python=3.11
conda activate romkorr
pip install numpy pandas folium branca


Veröffentlichung und Nutzung

Die erzeugte HTML ist statisch (kein Server notwendig)

Es werden keine personenbezogenen Daten verarbeitet

Externe Inhalte:

OpenStreetMap / Leaflet

Verlinkungen auf öffentlich zugängliche Briefquellen

Bei Veröffentlichung auf einer Website sollte in der Datenschutzerklärung auf
externe Kartendienste und ausgehende Links hingewiesen werden.

Status und Weiterentwicklung

Der aktuelle Stand bietet:

stabilen, reproduzierbaren Workflow

leistungsfähige Filter

kombinierte Karten- und Listenansicht

Geplante, noch nicht implementierte Erweiterungen:

filterabhängige Heatmap

visuelle Kodierung der Korrespondenzrichtung

zeitliche Animationen

Netzwerk-Ansichten