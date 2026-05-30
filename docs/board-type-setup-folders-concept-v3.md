# Board-Typ: Checkmk SETUP-Ordnerbaum ("Folder Tree" Board) — v3

Status: Konzept (Entscheidungs-Konsolidierung nach Review von v2)
Datum: 2026-05-30
Vorgänger: `…-concept.md` (v1, fachliche Kernidee + UX), `…-concept-v2.md`
(tiefe CMK-Source-Analyse). **v3 ist die maßgebliche Umsetzungsbasis** und legt
die in der Review getroffenen Entscheidungen fest; v1/v2 gelten für Details
(v2 §1 Source-Analyse, v1 §3.3 Renderer-Skizze) unverändert weiter.

> Neu in v3: (a) finalisierte Datenquellen-Entscheidung inkl. **Titel aus
> prettify(Slug)** als Default, (b) **leere Ordner sind Pflicht** — Standalone
> via REST fest eingeplant, (c) ausformulierter **„leer"-Zustand +
> Aggregationsregel**, (d) neuer Abschnitt **§4 Board-Erstellung &
> Konfiguration**.

---

## 1. Datenquellen — finale Entscheidung

Drei Datenebenen, sauber getrennt:

| Ebene | Quelle (beide Modi) | Anmerkung |
|---|---|---|
| **Status** (für Bubbling) | Livestatus-Host-Query mit `host.filename` + `num_services_*` | stabil 2.3–2.6 (`TableHosts.cc:540`); `AuthUser:`-gescoped |
| **Struktur befüllter Ordner** | dieselbe `filename`-Query (Pfadsegmente) | Container-Ordner mit befüllten Unterordnern erscheinen automatisch |
| **Titel (Default)** | `prettify(Slug)` aus `filename` | `_`→Leerzeichen + Title-Case; entspricht CMKs `_fallback_title` |
| **Vollständige Struktur (inkl. leerer Ordner) + echte Titel** | **CMK:** `.wato`-Disk-Walk · **Standalone:** REST `folder_config?recursive` | siehe §2/§3 |

**Kernpunkt:** Livestatus liefert Status + Struktur der befüllten Ordner + Slug.
Das allein ergibt bereits einen funktionierenden Baum. Die **leere-Ordner-/
Echt-Titel-Schicht** wird darübergelegt und gemerged (Key = Ordnerpfad).

### 1.1 Titel: prettify(Slug) als Default, echte Titel als Veredelung
- Default überall: `dc_muc` → „Dc Muc", `rack_01` → „Rack 01".
- **Grenze** (dokumentieren, kein Bug): Slug ist verlustbehaftet (lowercase/
  ASCII → Umlaute/Casing weg) und friert beim Anlegen ein (spätere Titel-
  Änderungen spiegelt der Slug nicht). Echte Titel kommen daher aus der
  Struktur-Schicht (`.wato`/REST), die ohnehin für leere Ordner gebraucht wird
  — d.h. **wer leere Ordner aktiviert, bekommt echte Titel gratis mit**.

---

## 2. Leere Ordner — jetzt Pflicht-Feature

Ein leerer Ordner = WATO-Ordner, unter dem (auch rekursiv) **kein Host** liegt →
in Livestatus unsichtbar. Wird benötigt und **anders dargestellt** (§3).

### 2.1 Quelle pro Modus
- **CMK-Modus:** `.wato`-Disk-Walk über `cmk.utils.paths.check_mk_config_dir/
  "wato"` (listet alle Verzeichnisse host-zahl-unabhängig, liefert Titel). Kein
  GUI-Kontext, keine Creds. **`.wato`-Read via `ast.literal_eval`**, NICHT
  `exec` — die Datei ist ein reines Literal-Dict; OrbVis führt fremde Dateien
  nicht aus. (Review-Flag aus v2.)
- **Standalone-Modus:** **REST `folder_config/collections/all?recursive=true`**
  (`folder_config/__init__.py:397`) — **fest eingeplant**. Liefert vollständige
  Hierarchie inkl. leerer Ordner + echte Titel, server-seitig permission-
  gescoped. Über bestehenden `_cmk_rest()` (`livestatus.py:1578`), **TTL-Cache**
  (Struktur/Titel ändern sich selten; nicht pro State-Tick abrufen).
  - **Voraussetzung:** automation-Credentials in der Connection. Fehlen sie →
    ehrlich degradieren: nur befüllte Ordner (aus Livestatus), Hinweis im
    Empty-State/Settings („Leere Ordner brauchen API-Zugang").

### 2.2 Merge
Struktur-Schicht (alle Ordner + Titel) ⨝ Livestatus-Rows (Status/Counts) über
den Ordnerpfad. Ordner ohne zugeordnete Hosts ⇒ als **leer** markiert.

---

## 3. „Leer"-Zustand: Darstellung + Aggregation

### 3.1 Darstellung (distinct, nicht grün/OK)
Ein hostloser Ordner hat **keinen** Status — darf nicht „alles gut"-grün wirken:
- gedämpfte/graue Farbe (NICHT das State-Grün), **gestrichelte/hohle** Ordner-
  Kontur (theme-aware Tokens, light+dark — vgl. `feedback_theme_contrast_cmk_vars`);
- Label/Badge „leer" bzw. „0 Hosts";
- **nicht** in Problem-Zählung/State-Legende einrechnen.

### 3.2 Aggregationsregel (Bubbling)
„Leer" ist ein eigener Rang **außerhalb** `_COMBINED_SEVERITY` und wird bei der
Eltern-Aggregation **übersprungen**:
- leerer Ordner zählt **weder als OK noch als Problem** → aus `max(worst)` der
  Kinder ausgeschlossen;
- Eltern-Ordner mit **ausschließlich** leeren Kindern ⇒ selbst „leer";
- sobald irgendwo darunter ein echter Host liegt ⇒ dessen Worst-State gilt, der
  leere Geschwister-Ordner bleibt nur lokal „leer".

Wiederverwendung: `_COMBINED_SEVERITY` (`state_service.py:36`),
`_aggregate_host_with_services_from_data()` (`:561`); die „leer"-Sonderbehandlung
ist ein dünner Wrapper um den bestehenden Map-Link-Rollup (`:553`).

---

## 4. Board-Erstellung & Konfiguration (neu)

### 4.1 Natur des Board-Typs: dynamisch, settings-only (wie Radar)
Der Baum wird **vollständig aus der Connection generiert** — es gibt **keine
manuell platzierten Objekte**. Daraus folgt (analog Radar/Geo-Automap):
- **Kein Objekt-Editor / kein „Add Object"** und kein Edit-Canvas.
- Konfiguration = **reine View-Settings** (unten), kein Drag&Drop.
- In der Board-Übersicht erscheint die Objekt-Spalte als „dynamic" (wie Radar).

### 4.2 Erstellungs-Flow
1. **Home → „New Board"** (`CreateBoardModal.vue`): neuer Typ **„Folder Tree"**
   in der Typ-Auswahl (neben Static/Flow/Geo/Radar), Name + **Connection**.
2. Anlegen → Board öffnet direkt im gerenderten Zustand (Root = `/` = alle
   Ordner, Default-Tiefe). Sofort nutzbar ohne weitere Schritte.
3. Verfeinern über **Board-Settings** (Zahnrad) — Live-Preview-Editor (0.4.0):
   jede Änderung (Root, Tiefe, Toggles) spiegelt sich sofort im Preview-Pane
   (derselbe Renderer).

### 4.3 Konfigurationsfelder (`FolderTreeView`-Schema)
| Feld | Typ | Default | Zweck |
|---|---|---|---|
| `connection_id` | Connection-Picker (board-level) | — | Monitoring-Quelle |
| `root_folder` | **Folder-Picker** (Autocomplete, Pfad+Titel) | `/` (alle) | Baum auf Teilbaum scopen, z.B. `/rechenzentren/muc` |
| `default_expand_depth` | int (0–n) | `1` | Auto-aufgeklappte Ebenen beim Laden |
| `show_services` | bool | `false` | Hosts zu Services aufklappbar (Dichte/Performance) |
| `show_empty_folders` | bool | `true` | leere Ordner zeigen (Feature an/aus) |
| `problems_only` | bool | `false` | gesunde Teilbäume ausblenden (Triage) |
| `only_hard_states` | bool | `false` | wie andere Boards |
| `sites` | **Site-Multi-Select** | alle | verteiltes Monitoring: Baum auf eine/mehrere Sites scopen (§5) |

(Felder konsolidieren v1 §3.1; neu: `show_empty_folders`, `root_folder` als
echter Folder-Picker.)

### 4.4 Folder-Picker (Root + ggf. Filter)
- Neuer Backend-Endpunkt, z.B. `GET /connections/{id}/folders` → flache Liste
  `{path, title, host_count}` (dieselbe Struktur-Quelle wie der Baum:
  Livestatus-Slugs + `.wato`/REST-Titel). TTL-gecacht.
- Choice-Liste über das **Dropdown-Registry-Muster** (`object_options.py` +
  Endpoint + Pinia-Store), damit FormSpec **und** Legacy-EditPanel dieselbe
  Quelle teilen (vgl. `feedback_dropdown_registry`).
- Default leer ⇒ Root `/`.

### 4.5 FormSpec + Legacy (beide Modi)
- **FormSpec zuerst** (deklarativ, CMK-Modus) in `BoardSettingsFormSpecModal.vue`
  — der Feldsatz ist klein/flach, ideal für FormSpec (vgl.
  `feedback_use_cmk_formspecs`).
- **`BoardSettingsModalLegacy.vue`**: dieselben Felder OrbVis-nativ für
  Standalone (`v-else=capabilities.formSpecs`) — Parität sicherstellen.
- Live-Preview rendert `FolderTreeBoard.vue` mit der Staging-Config.

### 4.6 Leerer/degenerierter Fall
- Non-CMK-Connection (Icinga2) oder keine Ordner ⇒ leerer Baum + erklärender
  Empty-State, kein Crash.
- Standalone ohne automation-Creds ⇒ Baum nur mit befüllten Ordnern + Hinweis
  „Leere Ordner & echte Titel benötigen API-Zugang in der Connection".

---

## 5. Sites / verteiltes Monitoring

In Checkmk-distributed wird die SETUP-Config (Ordner + Host-Definitionen)
**zentral gepflegt und auf Remote-Sites repliziert** → **eine globale
Ordnerhierarchie**, identisch auf allen Sites. **Sites sind ein Attribut der
Hosts (Blätter), nicht der Ordner** — ein Ordner kann Hosts mehrerer Sites
enthalten.

1. **Struktur ist site-übergreifend einheitlich.** Der `.wato`-Walk auf der
   OrbVis-Site (zentrale/replizierte Config) bzw. REST `folder_config` liefert
   die für **alle** Sites gültige Struktur — **eine** Quelle, kein per-Site-
   Struktur-Merge nötig.
2. **Hosts kommen site-getaggt.** Die föderierte Livestatus-Query
   (`_query_with_site`/MultiSiteConnection) liefert Rows mit `site_id` — OrbVis
   macht das bereits. Einsortierung in Ordner per `filename`; der `site_id`
   bleibt am **Blatt** (`ObjectState.site_id`, `schemas/state.py:46`).
3. **Aggregation site-agnostisch.** Folder-Worst-State = schlechtester Zustand
   aller Hosts im Ordner **über alle Sites hinweg** (natürliche „Status von
   allem in diesem Ordner"-Semantik). **Folder-Knoten tragen keinen `site_id`**
   (sie spannen Sites).
4. **Darstellung.** Host-Blatt zeigt eine **Site-Kennung** (kleines Chip/Badge),
   sinnvollerweise nur wenn **>1 Site** vorkommt (Single-Site-Setups bleiben
   clean). Optional im Detail-Drawer eine Per-Site-Aufschlüsselung pro Ordner
   („MUC: 3, davon 1 CRIT · FRA: 2 OK").
5. **Site-Filter** (Config-Feld `sites`, §4.3; optional Runtime-Toggle):
   scopt den Baum via `only_sites` der Multisite-Query. Ein Ordner, dessen Hosts
   alle aus herausgefilterten/nicht sichtbaren Sites stammen, verhält sich wie
   **leer/neutral** (konsistent mit §3) — kein Leak, „leer" ≠ „OK".
6. **Robustheit gegen Config-Drift.** Referenziert ein föderierter Host einen
   `filename`-Ordner, der (unerwartet) nicht in der Struktur-Schicht steht, ist
   der **`filename` autoritativ** für die Platzierung → Ordner aus Slug anlegen.
   `filename`-abgeleitete Struktur = Sicherheitsnetz, `.wato`/REST = Anreicherung.
7. **Deep-Links.** Host-Blatt → CMK-Host-Ansicht der **jeweiligen** Site
   (`site=…`); Folder-Knoten → zentrale WATO-Folder-Ansicht (kein site-Param).

→ Für die Umsetzung heißt das: **keine Sonderarbeit an der Struktur** (kommt
zentral), Sites fallen über die ohnehin föderierte, site-getaggte Host-Query
„gratis" als Blatt-Attribut an; nur Renderer (Badge) + optionaler `sites`-Filter
sind neu.

## 6. Permissions — Sichtbarkeit (User sehen nur, wofür sie berechtigt sind)

**Grundprinzip: jeder angezeigte Ordner muss durch eine Berechtigung gedeckt
sein.** Zwei Fälle:

1. **Befüllte Ordner + Hosts/Services** — bereits korrekt gescoped über
   Livestatus `AuthUser:` (`with_auth_user()`). Der User sieht nur Hosts seiner
   Kontaktgruppen → nur Ordner mit für ihn sichtbaren Hosts (und deren
   Vorfahren-Pfad) erscheinen. **Damit ist deren Titel legitim sichtbar — kein
   Leak** (die v2-Annahme „Titel nicht gescoped" wird **verworfen**, s.u.).
2. **Leere Ordner** — haben keine Hosts → AuthUser greift nicht. Würden aus
   `.wato`/REST **ungefiltert** kommen → **müssen explizit Ordner-permission-
   geprüft** werden, sonst Leak.

### 6.1 Ordner-Leseberechtigung ohne watolib (Port-Muster)
`Folder.may("read")` ist request-/GUI-gebunden (v2 §1.1) → nicht importierbar.
Wir **portieren** die Logik (Muster `checkmk_sites.py:12-22`):
- **Ordner-Kontaktgruppen** aus `.wato`-`attributes.contactgroups`
  (`{groups, recurse_perms, …}`) lesen, inkl. **Vererbung**: Unterordner ohne
  eigene `contactgroups` erbt die des Eltern; `recurse_perms` steuert die
  rekursive Geltung.
- **User-Kontaktgruppen** ermitteln (CMK: userdb/`contacts.mk` — OrbVis liest
  User-Infos bereits via SSO/`checkmk.py`).
- **Admin-Override:** `wato.see_all_folders`/Admin → alle Ordner (is_admin kommt
  aus dem CMK-Rollen-Sync, den OrbVis schon hat).
- **Regel:** leerer Ordner sichtbar ⟺ Admin ODER (User-CGs ∩ effektive
  Ordner-CGs ≠ ∅).

### 6.2 Pro Modus
- **CMK-Modus:** exakter Check über `.wato`-`contactgroups` + User-CGs. (Das
  rechtfertigt den `.wato`-Walk nun **doppelt**: echte Titel **und** Permission-
  Attribute.)
- **Standalone:** REST läuft mit **automation-Creds (= sieht alles)**, nicht als
  End-User, und ein OrbVis-Standalone-User hat nicht zwingend CMK-Kontaktgruppen
  → **kein** verlässlicher End-User-Scope für leere Ordner. → **Fail-closed:**
  leere Ordner nur für Admins; Nicht-Admins sehen ausschließlich die befüllten,
  AuthUser-gescopten Ordner. (Optionaler Ausbau: User→CG-Mapping via REST
  `objects/user_config/{user}`.)

### 6.3 Konsequenz
Es wird **kein** Ordner angezeigt, der nicht durch (1) oder (2) gedeckt ist;
bei Unsicherheit **fail-closed** (verbergen). Damit erfüllt das Board „User
sehen nur, wofür sie berechtigt sind" — Struktur **und** Titel.

### 6.4 Teil-berechtigte Ordner — CMK-Befund: NICHT maskieren (verworfen)
**Geklärt per CMK-Source** (`docs/folder-permission-cmk-behavior.md`): Checkmk
maskiert Folder-Titel **nie**. Der Folder-Painter in Monitoring-Views löst den
vollen echten Titel **ohne** `Folder.may("read")`-Check auf
(`cmk/gui/wato/views.py:46-77` → `Folder.title()`); das `wato_foldertree`-Snapin
baut den Baum aus einer **AuthUser-gescopten** `GET hosts … Columns: filename`-
Query und zeigt für jeden Ordner mit sichtbarem Host den echten Titel. WATO-
Folder-Permission und Monitoring-Kontaktgruppen sind **zwei getrennte Achsen**;
ein „Host zeigen, Titel maskieren" existiert in CMK nicht.
→ **Die Maskieren-Idee wird verworfen.** 1:1-CMK = **befüllte Ordner immer mit
echtem Titel** (Monitoring-Achse/AuthUser entscheidet, kein WATO-Check — genau
das tut der livestatus-abgeleitete Baum bereits); **leere Ordner** über den
Folder-CG-Check (§6.1–6.3) gaten und im Zweifel **ganz verbergen**, nie
maskieren. Verhalten über 2.3–2.6 identisch.

#### (historische Notiz) ursprüngliche Maskieren-Idee
Sonderfall: User darf einen **Host** sehen (Monitoring-Kontaktgruppe), aber hat
**keine WATO-Folder-Leseberechtigung**. Monitoring-Sichtbarkeit (Kontaktgruppen)
und WATO-Folder-Permission sind in CMK **getrennte Achsen**. Idee (Nutzer):
**Host darstellen, aber den Folder-NAMEN maskieren**.
- **Muss 1:1 Checkmk entsprechen** → die exakte Regel (maskiert CMK den
  Folder-Titel in Monitoring-Views/Snapin, wenn die WATO-Folder-Permission
  fehlt, der Host aber via Kontaktgruppe sichtbar ist? Oder zeigt CMK den Titel
  ohnehin?) ist **per CMK-Source zu klären, nicht zu raten** (Research-Agent
  beauftragt).
- **Datenmodell unterstützt es bereits:** Folder-Knoten haben `title` getrennt
  von Host-Kindern → „Titel maskieren, Hosts behalten" ist ein reiner
  Title-Override (z.B. `title="(eingeschränkt)"`, `folder_id`/Pfad anonymisiert),
  ohne die AuthUser-basierte Host-Aggregation zu ändern.
- **Status:** offen bis CMK-Source-Befund; bis dahin gilt §6.1–6.3 (Ordner ohne
  Berechtigung ganz verbergen). Befund entscheidet zwischen „verbergen" und
  „maskieren + Hosts zeigen".

## 7. Ordner umbenennen / verschieben

- **Titel-Umbenennung** (Slug/Pfad bleibt): unkritisch — Live-Baum zeigt beim
  nächsten Struktur-Refresh (TTL) den neuen Titel; ein per Pfad gepinntes Board
  bleibt gültig.
- **Verschieben / Slug-Änderung** (Pfad ändert sich): alle Host-`filename`
  ändern sich → der **Live-Baum heilt sich selbst** (nächste Livestatus-Query
  sortiert Hosts unter den neuen Pfad). Problematisch ist nur das
  **`root_folder`-Pin** eines Boards, falls per Pfad gespeichert → Pfad weg →
  leerer Baum.

### 7.1 `root_folder` stabil referenzieren
- **Bevorzugt: stabile Folder-`__id`** (UUID, in `.wato`/REST vorhanden) statt
  Pfad als `root_folder`-Wert speichern → übersteht Umbenennen/Verschieben;
  aktueller Pfad wird zur Laufzeit aufgelöst.
- **Fallback** (Standalone ohne REST, nur Pfade): Pfad speichern; bei „nicht
  auflösbar" **klarer UI-Zustand** „Konfigurierter Wurzelordner existiert nicht
  mehr (umbenannt/verschoben?) — bitte neu wählen" statt stillem Leer-Baum.
- Der Folder-Picker (§4.4) liefert daher `{id, path, title}`; gespeichert wird
  `id` (wenn vorhanden), Resolve/Anzeige über `path`.

## 8. Live-Update / SSE
- Status fließt über den bestehenden SSE-Kanal. Der **Baum muss in den
  Broadcast-Diff-Hash einfließen** (sonst frieren Folder-Badges ein) — sauberer:
  **eigenes SSE-Event** `folder_tree_update` statt Einbettung in `MapStates`
  (vgl. v1 §4.5). Struktur (Ordner/Titel) ändert sich selten → getrennt vom
  Status-Tick, TTL-gecacht; nur der Status-Layer tickt im Refresh-Intervall.

## 9. Abgrenzung CMK-Reuse (aus v2, bestätigt)
- **Nicht** nutzbar: `watolib.FolderTree`/`Folder` (request-/`g`-gebunden,
  brechende `__init__`-API ab 2.5), Sidebar-Snapin (`_snapins.py:349`,
  server-HTML), cmk-frontend-vue (keine Tree-Komponente).
- **Genutzt:** Livestatus `host.filename`; `cmk.utils.paths` + `.wato`-Read
  (CMK); REST `folder_config` (Standalone, jetzt Pflicht); OrbVis-Helfer
  `_COMBINED_SEVERITY`/`_aggregate_host_with_services_from_data`/`with_auth_user`/
  `_cmk_rest`. Renderer ist OrbVis-eigen.

---

## 10. Implementierungsplan (Delta zu v2)

### Phase 0 — Schema & Typ-Registrierung (modusagnostisch)
- `schemas/board.py`: `FolderTreeView` (Felder §4.3) + `BoardView`-Union.
- `schemas/state.py`: `FolderTreeNode` (+ `is_empty`-Flag, `host_count`).
- `frontend/src/types/api.ts`, `utils/dropdownOptions.ts`, `CreateBoardModal.vue`
  (neuer Typ), i18n.

### Phase 1 — Livestatus-Baum (MVP, beide Modi identisch)
- `connections/base.py`: ABC `get_folder_tree()` + `FolderTreeData`.
- `connections/livestatus.py`: Host-Query um `filename`+`num_services_*`
  (FolderTree-**eigene** Spaltenliste, nicht global `_HOST_EXTRA_COLS`
  verteuern); Slug-Ableitung + **prettify(Slug)**-Titel; `_query_with_site`
  (multisite/`site_id`).
- `connections/test.py` (Fake-Baum inkl. eines leeren Ordners),
  `connections/icinga2.py` (leer/flach).

### Phase 2 — Aggregation & State-Branch (modusagnostisch)
- `state_service.py`: `_get_folder_tree_states()` + Branch in
  `_execute_board_states()` (`:126`/`:133`); Bubbling + **„leer"-Sonderrang**
  (§3.2); `problems_only`-Pruning.
- `api/v1/states.py`: eigenes `folder_tree_update`-SSE-Event + Diff.

### Phase 3 — Vollständige Struktur + Titel (leere Ordner)
- **CMK:** `integrations/checkmk_folders.py` (analog `checkmk_sites.py`):
  `read_wato_folder_tree(root)` — Walk `conf.d/wato/`, `.wato` via
  `ast.literal_eval`, Titel + `__id` + `attributes.contactgroups`/leere Ordner;
  guarded `available` + try/except. **Ordner-Permission-Filter (§6):**
  leere Ordner gegen User-CGs (userdb) + Vererbung + Admin-Override prüfen.
- **Standalone:** `livestatus.py` REST-Variante `folder_config?recursive`
  (TTL-Cache), Merge mit Livestatus-Rows; ohne Creds → degradieren. Leere
  Ordner **fail-closed** außer für Admins (§6.2).
- Kopf-Kommentar „nicht `FolderTree` importieren" (Muster `checkmk_sites.py:12-22`).

### Phase 4 — Renderer (OrbVis-eigen)
- `components/board/FolderTreeBoard.vue` (neu): `<ul role="tree">`,
  Expand/Collapse, Virtual-Scroll, State-Badges (`stateColors`, theme-aware),
  **„leer"-Styling** (§3.1), Worst-Path-Auto-Expand, „Probleme"-Toggle,
  **Site-Chip am Host-Blatt** (nur bei >1 Site, §5).
- `views/BoardView.vue`: Dispatch + `isFolderTree`; Drawer/ContextMenu/
  BoardSearch wiederverwenden (`:1715-1736`). Kein Edit-Canvas (settings-only).

### Phase 5 — Erstellung & Settings
- `CreateBoardModal.vue`: Typ „Folder Tree".
- Folder-Picker-Endpunkt `GET /connections/{id}/folders` → `{id, path, title,
  host_count}`, **permission-gefiltert** (§6); gespeichert wird `id` (§7.1).
  Dropdown-Registry (`object_options.py` + Store).
- `BoardSettingsFormSpecModal.vue` (FormSpec) + `BoardSettingsModalLegacy.vue`
  (Parität): Felder §4.3 inkl. `sites`-Multi-Select (Quelle: Connection-Sites,
  Dropdown-Registry), Live-Preview.

### Tests
- Backend: Slug-Ableitung + prettify, Bubbling inkl. „leer"-Sonderrang,
  `problems_only`; CMK `.wato`-Parsing gegen Fixture-`conf.d/wato` (kein OMD);
  Standalone REST gegen gemockte `_cmk_rest`-Antwort.
- Frontend: Tree-Render/Expand + „leer"-Darstellung (analog `BoardCanvas.test.ts`).
- Playwright: Create → Settings (Root/Tiefe/Toggles, `show_empty_folders`) →
  Expand → Drilldown → Drawer; CMK- und Standalone-Modus separat.

---

## 11. Offene/bestätigte Entscheidungen
- ✅ Leere Ordner Pflicht; Standalone via REST (Creds nötig, sonst degradieren).
- ✅ Titel = prettify(Slug) Default, echte Titel via `.wato`/REST-Schicht.
- ✅ `.wato` via `ast.literal_eval` (kein `exec`).
- ✅ Eigenes SSE-Event statt Diff-Hash-Einbettung.
- ✅ Settings-only/dynamisches Board (kein Objekt-Editor).
- ✅ Sites = Blatt-Attribut, Struktur global/zentral, Aggregation site-agnostisch,
  optionaler `sites`-Filter (§5).
- ✅ **Permissions (§6):** kein Ordner ohne Berechtigung sichtbar; befüllte via
  AuthUser, leere via portiertem Ordner-CG-Check (CMK), Standalone fail-closed
  (leere Ordner nur Admin). v2-„Titel nicht gescoped"-Trade-off verworfen.
- ✅ **Rename/Move (§7):** `root_folder` per stabiler `__id` (wo verfügbar),
  Pfad-Fallback + „nicht auflösbar"-UI; Live-Baum heilt sich via `filename`.
- ⚠️ Zu bestätigen bei Umsetzung: Default `expand_depth=1`; Site-Badge erst ab
  >1 Site; CG-Vererbungs-Semantik (`recurse_perms`) gegen echte CMK-Folder
  gegentesten.
