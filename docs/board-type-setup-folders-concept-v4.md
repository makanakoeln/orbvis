# Folder-Board v4 — Interaktive „Folder Map" (Zoomable Circle Packing)

Status: Konzept + Implementierung (Branch `feat/foldertree-board`).
Vorgänger: `…-concept-v3.md` (Datenmodell, Aggregation, Sites, Erstellung) bleibt
maßgeblich für Backend/Schema. Dieses Dokument ergänzt **nur die Darstellung**.

## Problem

Der v1–v3-Renderer (`FolderTreeRow`/`FolderTreeBoard`) ist eine eingerückte
Baumliste — präzise, aber **statisch**: sie liest sich wie eine Konfigurationsdatei,
nicht wie ein operativer Überblick. Ein Operator vor einer Wand-Anzeige will auf
einen Blick *sehen*, wo sich Probleme ballen, ohne jede Zeile zu lesen. Feedback:
„Aktuell ist mir das zu statisch. Vielleicht so ähnlich wie bei den Flow boards."

Das Flow-Board verwandelt Topologie in einen lebendigen, zoombaren d3-Graphen.
Das Folder-Board soll dasselbe Prinzip auf die **SETUP-Hierarchie** anwenden.

## Gewählte Darstellung: Zoomable Circle Packing (d3.pack)

Verschachtelte Kreise: Ordner enthalten Ordner enthalten Hosts.

| Encoding | Bedeutung |
|---|---|
| Kreis-Größe | Anzahl Hosts darunter (`host_count` über `sum`) |
| Füll-/Ring-Farbe | gebubbleter Worst-State (`stateColor`) |
| Verschachtelung | SETUP-Ordnerhierarchie 1:1 |
| dünner gestrichelter Ring, keine Füllung | **leerer Ordner** (eigener Rang, sticht ab) |
| solider Punkt | Host-Blatt, Farbe = kombinierter Host-Status |

### Warum Circle Packing (vs. Alternativen)

- **Container-Metapher 1:1**: „Ordner enthält Dinge" wird *räumlich* abgebildet —
  ein roter Ordner-Ring zeigt sofort, dass ein Problem darin steckt.
- **Drill-down = Zoom**: Klick auf einen Ordner zoomt ihn füllend heran (kanonische
  Bostock-Interaktion) → wirkt dynamisch, keine separate Navigation nötig.
- **Leere Ordner** lassen sich als kleine umrissene Kreise natürlich darstellen
  (Pflichtanforderung aus v3: müssen sichtbar *und anders* sein).
- **Skaliert ruhiger als ein Force-Graph**: deterministisches Layout, kein
  Physik-Zittern — angenehmer für eine Dauer-Anzeige.

Verworfen: **Sunburst** (radiale Segmentwinkel für tiefe/leere Ordner unleserlich,
„enthält" nur implizit); **Treemap** (Rechtecke verlieren die Tiefen-Cue, leere
Null-Größe-Ordner verschwinden); **Force-Graph wie Flow** (Bäume per Physik
„wandern", instabil) — Circle Packing liefert dasselbe lebendige, zoombare,
knotenbasierte Gefühl bei stabiler Struktur.

## Interaktion

- **Klick Ordner** → hineinzoomen (wird Fokus). **Klick Hintergrund/Breadcrumb** → heraus.
- **Klick Host** → Detail-Drawer (bestehende `select-host`-Verdrahtung wiederverwendet).
- **Hover** → Tooltip: Titel, Status, Host-/Problem-Zähler.
- **Breadcrumb** (root / dc / muc) oben, spiegelt den Fokus; Klick springt.
- **Toolbar**: View-Umschalter **Map | List** (List = bestehender Baum, bleibt
  erhalten), „Problems only"-Filter, Summary.
- **Live**: reiner State-Wechsel → Kreise neu einfärben mit kurzer Transition
  (kein Relayout). Strukturänderung → Relayout mit Transition. Die Entscheidung
  fällt über den Pfad-Set-Vergleich (analog zur Backend-`folder_tree_changed`-Signatur).

## Granularität

Die Map packt **Ordner + Hosts**. Services bleiben dem **List-Modus** und dem
**Drawer** vorbehalten (`show_services`), damit die Map ruhig bleibt. Host-Blätter
sind in der Map Endknoten.

## Theme

`stateColor()` + CMK-CSS-Vars (`--text`, `--text-muted`, `--border`, `--bg-*`).
Leerer Ordner: `--text-muted` gestrichelt, transparente Füllung. Muss in
Dark **und** Light lesbar sein (Verifikation in beiden Themes Pflicht).

## Default

Map ist der neue Default-Renderer; „List" für die präzise Auflistung bleibt einen
Klick entfernt. Umschaltung session-lokal, kein Persist nötig.
