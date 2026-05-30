# Folder-Board v4 — Darstellung (Tree-Default + Datadog-Style Treemap-Map)

Status: Konzept + Implementierung (Branch `feat/foldertree-board`).
Vorgänger: `…-concept-v3.md` (Datenmodell, Aggregation, Sites, Erstellung) bleibt
maßgeblich für Backend/Schema. Dieses Dokument ergänzt **nur die Darstellung**.

## Problem

Der v1–v3-Renderer ist eine eingerückte Baumliste — präzise, aber als alleinige
Ansicht „zu statisch" (User-Feedback): ein Operator vor einer Wand-Anzeige will auf
einen Blick *sehen*, wo sich Probleme ballen. Ziel war eine zweite, visuelle Ansicht
„ähnlich wie bei den Flow boards".

## Designschleife (wichtig)

**Erster Versuch: Zoomable Circle Packing (verworfen).** Optisch ansprechend, aber im
CMK-Modus an echten Daten (Folder 10, 54 Hosts) **für Operatoren unbrauchbar**:
unbeschriftete Punkte (man sieht nicht *welcher* Host), der einzelne Ordner-Ring trägt
keine Information, Root-Hosts „spillen" sichtbar aus dem Ring. Hierarchie war kaum
ablesbar — genau das, was der Operator erwartet, fehlte.

**Wettbewerbs-Abgleich:** Checkmk selbst (Ordnerbaum + Problem-Listen), PRTG
(hierarchischer Device-Tree als Primäransicht), Icinga/Thruk/Zabbix (Hostgroup-Listen)
setzen alle auf **Hierarchie**; eine visuelle „Map" bei Skalierung macht **Datadog** als
**Treemap/Host-Map** (beschriftete, größenproportionale, farbcodierte Kacheln).

## Entscheidung

1. **Hierarchischer Baum (List) ist der Default** — das mentale Modell eines
   CMK-Operators. `FolderTreeRow`/`FolderTreeBoard`, `mode='list'`.
2. **Visuelle „Map" = Datadog-Style Nested Treemap** (`FolderTreeMap.vue`, d3.treemap
   squarified), umschaltbar per Map/List-Toggle.

## Treemap-Darstellung

| Encoding | Bedeutung |
|---|---|
| Kachel-/Box-Größe | Anzahl Hosts darunter (`host_count` über `sum`) |
| Host-Kachel-Farbe | kombinierter Host-Status (`stateColor`) |
| Ordner-Box mit Kopfzeile | `Titel · host_count`, Rahmen farbig bei Problem |
| verschachtelte Boxen + Header | SETUP-Hierarchie **explizit** (jede Ebene eine Box) |
| gestrichelte Box, „· empty" | **leerer Ordner** (sticht ab, Pflicht aus v3) |

**Warum Treemap statt Circle Packing:** Kacheln tragen **Labels** (Host + Ordner
sichtbar ohne Hover), Größenverhältnis ist exakt ablesbar, Probleme sind solide
Farbblöcke, leere Ordner bekommen eine echte (gestrichelte) Box, kein „Spill". Das
ist das etablierte Ops-„Heatmap"-Muster.

## Interaktion

- **Klick Ordner(-box/-header)** → Drill-down (Treemap re-layoutet auf den Ordner,
  animiert). **Klick leere Canvas / Breadcrumb** → eine Ebene zurück.
- **Klick Host-Kachel** → Detail-Drawer (bestehende `select-host`-Verdrahtung).
- **Hover** → Tooltip (Titel, Status, Host-/Problem-Zähler).
- **Breadcrumb** (Main › Datacenters › …), Klick springt.
- **Toolbar** (geteilt mit List): Map/List-Toggle, „Problems only", Summary.
- **Live**: reiner State-Wechsel → Kacheln neu einfärben (Transition, kein Relayout);
  Strukturänderung → Relayout. Entscheidung via Pfad-Set-Vergleich.
- **ResizeObserver** → Treemap füllt den Container 1:1 (keine Verzerrung).

## „Problems only" / Semantik-Hinweis

Filtert Äste ohne Problem (`prune`). Offener Punkt: ein Host zählt schon als „Problem",
wenn nur ein *Service* WARNING ist (kombinierter State) — auf einer Default-CMK-Site
ist fast jeder Host betroffen, dann blendet der Filter sichtbar nichts aus. Ggf. später
Schweregrad-Schwelle (nur CRIT/DOWN) und Leerzustand-Feedback.

## Theme

`stateColor()` + CMK-CSS-Vars; leere Ordner `--text-muted` gestrichelt; Labels mit
`--bg-glass`-Halo. In Dark **und** Light verifiziert (standalone + CMK/ZWEIFUENF).
