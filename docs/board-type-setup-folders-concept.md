# Board-Typ: Checkmk SETUP-Ordnerbaum ("Folder Tree" Board)

Status: Konzept (noch nicht implementiert)
Autor: Recherche-Agent
Datum: 2026-05-30

## 1. Kernidee

Ein neuer Board-Typ `foldertree`, der die **Checkmk-SETUP-Ordnerhierarchie**
(Folder → Subfolder → Host → Service) als aufklappbaren Baum darstellt. Jeder
Ordnerknoten trägt einen **abgeleiteten Status** (worst-state-bubbling) aus allen
darunterliegenden Subfolders/Hosts/Services. Ziel: Operator bekommt in einer
einzigen, vertrauten Struktur einen Statusüberblick über die in Checkmk
organisierte Infrastruktur und kann von einem roten Ordner schnell bis zum
auslösenden Service drillen — ohne vorher manuell ein Board zu bauen
(im Gegensatz zu Static).

Abgrenzung in einem Satz: Static/Geo sind kuratierte, positionierte Boards;
Flow/Radar sind topologie- bzw. filtergetrieben; **FolderTree spiegelt die
operative WATO-Organisation 1:1 und braucht keine Pflege**.

---

## 2. Codebase-Exploration (Touchpoints)

### 2.1 Wie Board-Typen heute definiert/registriert sind

Board-Config wird als JSON in `data/maps/` gehalten (kein DB), validiert über
`backend/app/schemas/board.py`. Der Typ steckt im **diskriminierten Union**
`BoardView` (Feld `type`):

- `backend/app/schemas/board.py:199-254`
  `StaticView` / `WorldmapView` / `RadarView` / `FlowView`, zusammengefügt zu
  ```python
  BoardView = Annotated[StaticView | WorldmapView | RadarView | FlowView,
                        Field(discriminator="type")]
  ```
  `BoardConfig.view` defaultet auf `StaticView`.

Ein neuer Typ ist also primär ein neues `*View`-Pydantic-Modell + Aufnahme in
diese Union. Alle weiteren Touchpoints hängen am `view.type`-String:

**Backend**
- `backend/app/services/state_service.py:91` `get_board_states()` →
  `_execute_board_states():126`. Dort wird auf `cfg.view.type == "radar"`
  verzweigt (`_get_radar_states():636`) bzw. `inflate_auto_objects()` für
  Worldmap-Automaps (`:174`). **Hier kommt der neue `foldertree`-Branch hin.**
- `backend/app/api/v1/states.py` — REST `GET /boards/{name}/states` (`:214`),
  SSE `GET /sse/boards/{name}` (`:253`) und der `_broadcast_loop():135`
  (verzweigt bereits auf `cfg.view.type == "flow"` für Topologie-Deltas). Der
  FolderTree nutzt denselben State-Push-Kanal.
- `backend/app/connections/base.py` — ABC mit den Query-Methoden
  (`get_all_hosts_states():260`, `get_services_summary():306`,
  `get_group_member_states():187`, …). **Eine neue Methode
  `get_folder_tree()` wird hier deklariert** und in `livestatus.py`,
  `test.py`, `icinga2.py` implementiert.

**Frontend**
- `frontend/src/types/api.ts:90-109` — TS-Spiegel der Views + `BoardView`-Union.
  Neuer `FolderTreeView` ergänzen.
- `frontend/src/utils/dropdownOptions.ts:51` `boardTypeOptions()` — Liste der im
  Create-Modal angebotenen Typen. Eintrag `foldertree` ergänzen.
- `frontend/src/components/board/CreateBoardModal.vue:126-138` — `desc`-Mapping
  pro Typ; i18n-Key ergänzen.
- `frontend/src/views/BoardView.vue` — zentraler Renderer-Dispatch
  (`:304` Worldmap, `:387` Radar, `:404` Flow, `:478` BoardCanvas/Static).
  `isWorldmap/isFlowmap/isRadar` Computed (`:1270-1272`). **Neuer
  `<FolderTreeBoard>`-Branch + `isFolderTree`-Computed.**
- Neue Komponente `frontend/src/components/board/FolderTreeBoard.vue`
  (Renderer, analog zu RadarCanvas/FlowBoard als eigenständiger, nicht
  positionierter Renderer).
- EditPanel/Settings: `BoardSettingsFormSpecModal.vue` (FormSpec-Pfad) und
  `BoardSettingsModalLegacy.vue` (Standalone-Pfad) — beide brauchen die
  FolderTree-Optionen (Root-Folder, Tiefe, Filter). Object-Options
  (`object_options.py` + Pinia `objectOptions`-Store) sind hier **nicht**
  betroffen, weil FolderTree keine pro-Objekt-Typen-Auswahl im EditPanel
  hat (der Baum ist vollständig server-seitig generiert, wie Radar).

> Hinweis: Das `MEMORY.md`-Schema nennt `views/MapView` / `components/map/`.
> Aktueller Stand ist `views/BoardView.vue` + `components/board/`. Diese
> Pfade gelten.

### 2.2 Wie OrbVis an die Ordnerstruktur kommt (belegt)

**Primärquelle — Livestatus-Spalte `host.filename` (eine Query, kein REST):**

Checkmk setzt pro Host die Custom-Variable `FILENAME`; Livestatus exponiert sie
als Spalte `filename` der `hosts`-Tabelle:

- `~/git/checkmk/packages/livestatus/src/TableHosts.cc:540`
  `prefix + "filename", "The value of the custom variable FILENAME", …`

Der Wert wird in `cmk/base/config.py` erzeugt:

- `cmk/base/config.py:3289` `attrs["_FILENAME"] = path`
- `path` = `host_paths[hostname]`, gesetzt über `set_current_path()` →
  `cmk/base/config.py:792-794`:
  ```python
  relative_path = path.relative_to(cmk.utils.paths.check_mk_config_dir)
  current_path = f"/{relative_path}"   # z.B. "/wato/linux/db/hosts.mk"
  ```
  mit `check_mk_config_dir = <omd>/etc/check_mk/conf.d`
  (`cmk/utils/paths.py:40`). WATO schreibt unter `conf.d/wato/…`, daher hat
  `filename` die Form **`/wato/<folder>/<subfolder>/hosts.mk`**.

Ableitung des Ordnerpfads in OrbVis:
```
folder_path = filename
    .removeprefix("/wato/")
    .removesuffix("hosts.mk")
    .strip("/")            # ""  → Root, "linux/db" → verschachtelter Folder
```

Damit liefert **eine einzige** `GET hosts`-Query mit Spalten
`name filename state … num_services_*` (genau die Spalten, die
`get_all_hosts_states()` in `livestatus.py:1045` schon holt — nur `filename`
ergänzen) alle Hosts + ihre Ordnerzuordnung + per-Host-Service-Donut. Das ist
multisite-sicher (jede Zeile self-contained) und respektiert `AuthUser:`-Scoping
(s.u.), weil es eine reguläre Host-Query ist.

**Sekundärquelle / Anreicherung — REST `folder_config` (für Titel & leere
Ordner):**

- `cmk/gui/openapi/endpoints/folder_config/__init__.py:367` `list_folders`
  → `GET domain-types/folder_config/collections/all?recursive=true&show_hosts=true`
  liefert die **autoritative Hierarchie inkl. Folder-Titel** (Display-Namen wie
  „Linux Server", nicht nur Slugs) und auch **leere Ordner**, die in der
  `filename`-Ableitung fehlen würden.

OrbVis hat den REST-Pfad bereits (Bearer-Auth über
`automation_user`/`automation_secret`, `_cmk_rest()` in
`livestatus.py:1585`), nutzt ihn aber bisher nur für BI/Metriken. Folder-Titel
sind ein optionales Upgrade; **MVP kommt mit `filename` allein aus** (Slug als
Anzeigename).

### 2.3 Vorhandene Status-Aggregation / worst-state-bubbling (wiederverwenden)

- **Combined-severity-Skala** `_COMBINED_SEVERITY`
  (`state_service.py:36-45`): einheitlicher Rang über Host- UND Service-States
  (`PENDING:-1 … CRITICAL:4`). **Genau die Skala für das Folder-Bubbling
  verwenden** — kein eigener Vergleich.
- **Host+Services-Rollup** `_aggregate_host_with_services_from_data()`
  (`state_service.py:561-575`): nimmt einen Host-State + dessen Service-States
  und gibt den schlechtesten zurück. Vorlage für die Host-Ebene des Baums.
- **Map-Link-Rollup** (`state_service.py:519-554`): bündelt heterogene
  Kindzustände eines Map-Objekts zum Worst-State via `_COMBINED_SEVERITY`.
  Direkte Vorlage für die Folder-Ebene (Folder = „Container" wie eine
  verlinkte Map).
- **Gruppen-Rollup** `get_hostgroup_states()` / `get_servicegroup_states()`
  (`livestatus.py:867-900`) — Muster, wie ein Container-Status aus
  `Columns: state` einer gefilterten Query entsteht (hier aber pro Folder
  client-/service-seitig aggregiert, nicht per Livestatus-Stats).
- **Frontend BI-State-Mapping** `BI_STATE_FULL_LABEL` +
  `stateColor()` (`utils/stateColors.ts:25`, `STATE_COLORS:6`) — für die
  Status-Badges am Baum.

Der Folder-Aggregator wird also als kleine rekursive Funktion über das schon
gebaute (host→services)-Datenmaterial gelegt und nutzt durchweg
`_COMBINED_SEVERITY`.

### 2.4 Vorhandene Tree-/Expand-Collapse-Bausteine

- `frontend/src/components/board/AggregationSubtree.vue` — d3-`hierarchy()` +
  `d3.tree()` Layout mit **worst-path-Highlight** (Pfad Wurzel→schlimmstes
  Blatt), Downtime/Ack-Badges, State-Farben. Das ist ein **grafischer** Baum
  (SVG, fester Layout) — nützliche Vorlage für Badge-/Farb-/Worst-Path-Logik,
  aber für hunderte Hosts ungeeignet (kein Collapse, kein Virtualisieren).
- `state.py:130-146` `AggregationNode` — rekursives Tree-Schema
  (`children: list[AggregationNode]`, `node_type`, `state`, `in_downtime`,
  `acknowledged`). **Direkte Vorlage für ein `FolderTreeNode`-Schema.**
- `DetailDrawer.vue` (Tabs, Drill-Down) und `ContextMenu.vue` — bestehende
  Detail-/Aktions-Surfaces, die der FolderTree für Blätter (Host/Service)
  wiederverwendet (gleicher `node-enter`/Klick→Drawer-Pfad wie Radar/Flow,
  vgl. `BoardView.vue:1715-1736`).

Einen klassischen **aufklappbaren List-Tree** (HTML `<ul>` mit
Expand/Collapse + Virtual-Scroll) gibt es noch nicht — der ist neu zu bauen,
aber State-/Aggregations-/Drawer-Logik wird wiederverwendet.

---

## 3. Konzept

### 3.1 Datenmodell

**Board-Config (`schemas/board.py`):**
```python
class FolderTreeView(BaseModel):
    type: Literal["foldertree"] = "foldertree"
    # WATO-Ordnerpfad relativ zur Site-Root ("" = gesamter Baum,
    # "linux/db" = nur dieser Teilbaum). Slash-getrennt, ohne /wato/-Prefix.
    root_folder: str = ""
    # Wie viele Folder-Ebenen unter root standardmäßig aufgeklappt sind
    # (0 = nur Root-Ebene). UI darf tiefer expandieren; das ist nur der
    # Initialzustand.
    default_expand_depth: int = Field(default=1, ge=0, le=10)
    # Nur Hosts/Services mit Problem-State einblenden (Operator-Default-Toggle).
    problems_only: bool = False
    # Service-Blätter überhaupt laden? Aus Performancegründen abschaltbar;
    # dann endet der Baum auf Host-Ebene.
    show_services: bool = True
    # Harte States bevorzugen (wie only_hard_states bei dyngroup).
    only_hard_states: bool = False
```
Aufnahme in die `BoardView`-Union (`board.py:251`) und in `types/api.ts:109`.

**Tree-Response-Schema (`schemas/state.py`, analog `AggregationNode`):**
```python
class FolderTreeNode(BaseModel):
    id: str                       # stabiler Pfad-Key, z.B. "folder:linux/db"
    node_type: Literal["folder", "host", "service"]
    title: str                    # Anzeigename (Folder-Slug oder REST-Titel,
                                  # Host-Alias, Service-Description)
    name: str                     # technischer Name (folder path / host / svc)
    state: str                    # aggregierter/realer State-String
    host_name: str | None = None  # für host/service-Blätter (Drawer/Deep-Link)
    service_description: str | None = None
    in_downtime: bool = False
    acknowledged: bool = False
    stale: bool = False
    # Worst-Aggregat-Zähler je Folder (für Badge "3 CRIT / 2 WARN").
    counts: ServicesSummary | None = None
    host_count: int = 0           # nur folder: # Hosts im Teilbaum
    children: list[FolderTreeNode] = Field(default_factory=list)
```
`MapStates` bekommt ein optionales Feld `folder_tree: FolderTreeNode | None`
(neben `states`), sodass der bestehende SSE-/MapStates-Container ohne neuen
Endpunkt genügt. Alternativ ein eigenes Top-Level-Feld, damit der Diff-Hash im
Broadcast-Loop sauber bleibt — siehe Risiken.

### 3.2 Backend-Endpunkt & Aggregation

**Connection-Methode** (`base.py` ABC + `livestatus.py`):
```python
async def get_folder_tree(self, root: str, *, only_hard: bool) -> list[HostFolderRow]
```
- Eine `GET hosts`-Query mit `Columns: name alias filename state acknowledged
  scheduled_downtime_depth num_services_ok num_services_warn num_services_crit
  num_services_unknown num_services_pending` (Erweiterung der bereits in
  `livestatus.py:1045` existierenden Query um `filename`/`alias`).
- Optional `Filter: host_filename ~ ^/wato/<root>/` für Teilbaum-Scoping.
- `with_auth_user()`-Kontext (`livestatus.py:712`) wird vom aufrufenden
  `get_board_states()` bereits gesetzt → Folder-Sichtbarkeit folgt automatisch
  den Contact-Groups des Users (Hosts außerhalb seiner Berechtigung fehlen, der
  Ordner erscheint dann ggf. gar nicht oder mit reduzierter Aggregation).
- Services werden **lazy** pro Host nur geladen, wenn ein Host im UI expandiert
  wird (eigener Endpunkt, s.u.) bzw. bei `show_services` initial nur als
  Donut-Counts aus den `num_services_*`-Spalten (kein Service-Roundtrip nötig
  für die Folder-Aggregation).

**State-Service-Branch** (`state_service.py:_execute_board_states`):
```python
if cfg.view.type == "foldertree":
    return await _get_folder_tree_states(cfg, connection)
```
`_get_folder_tree_states()`:
1. `rows = await connection.get_folder_tree(root, only_hard=...)`.
2. Pfad-Split jeder Zeile (`filename` → Folderpfad, s. 2.2) und Aufbau der
   Folder-Hierarchie als `dict[path, FolderTreeNode]`, fehlende
   Zwischenordner implizit anlegen.
3. Host-Knoten anhängen; Host-State via
   `_aggregate_host_with_services_from_data()`-Logik (Host-State vs.
   Service-Donut-Schwere) auf Wunsch verschmelzen.
4. **Folder-Bubbling**: rekursiv von den Blättern hoch, je Folder
   `worst = max(child_states, key=_COMBINED_SEVERITY.get)` — identische Skala
   wie Map-Link-Rollup (`state_service.py:553`).
5. `counts`/`host_count` je Folder mitsummieren (für Badge & Empty-State).
6. Optional `problems_only`: Teilbäume ohne Problem-Blatt entfernen
   (Folder bleibt nur, wenn er ein WARN+/DOWN/CRIT-Blatt enthält).

**Lazy Service-Endpunkt** (Frontend ruft beim Host-Expand):
- Wiederverwendung von `GET /connections/{id}/hosts/{host}/services` bzw.
  `get_host_services()` (`base.py:216`) — **kein neuer** Endpunkt nötig,
  derselbe Pfad, den DetailDrawer schon nutzt.

**Live-Update:** Der `_broadcast_loop()` (`states.py:135`) ruft pro Tick
`get_board_states(cfg)`; für `foldertree` gibt das den frisch aggregierten
Baum zurück, der über den **bestehenden SSE-Kanal** als `MapStates`-Payload
(mit `folder_tree`) gepusht wird. Kein neuer Transport.

### 3.3 Frontend-Renderer (`FolderTreeBoard.vue`)

- **Aufklappbarer List-Tree** (HTML, nicht SVG): `<ul role="tree">`,
  Zeilen mit Disclosure-Triangle, Einrückung pro Tiefe, Status-Punkt links
  (Farbe via `stateColor()`/`STATE_COLORS`), Titel, rechts ein
  Counts-Badge (`3 ✕ CRIT · 2 ✕ WARN`) für Folder bzw. Service-Donut für
  Hosts.
- **Theme-aware**: ausschließlich vorhandene CSS-Tokens/`stateColors`
  (light+dark schon abgedeckt); für Icon-/Badge-Kontrast auf Board-Untergrund
  das etablierte `--icon-halo`-Muster, nicht `.dark`-Invert (vgl.
  Memory-Lesson „Board-Icon-Lesbarkeit via Kontrast-Halo").
- **Expand/Collapse**: Folder-Ebenen kommen komplett im Tree-Payload (billig,
  da nur Counts). **Service-Blätter werden lazy** beim Host-Expand über
  `get_host_services()` nachgeladen und gecacht; spart Roundtrips bei großen
  Sites.
- **Virtualisierung**: bei vielen sichtbaren Zeilen (>~200) Windowing
  (nur sichtbarer Ausschnitt im DOM), damit hunderte Hosts flüssig bleiben.
- **Worst-Path-Highlight**: optionaler „zum Problem springen"-Affordance —
  Logik aus `AggregationSubtree.vue:253` (Pfad Wurzel→schlimmstes Blatt)
  wiederverwenden, hier als Auto-Expand bis zum schlimmsten Blatt.
- **Suche/Filter**: bestehende `BoardSearch.vue` integrieren (filtert Knoten,
  klappt Treffer-Pfade auf). „Nur Probleme"-Toggle spiegelt
  `view.problems_only`, kann clientseitig live umgeschaltet werden.
- **Empty-States**: (a) keine Connection → bestehende Connection-Down-Banner;
  (b) Root-Folder leer / kein Host sichtbar (Permission!) → klare Meldung
  „Keine sichtbaren Ordner/Hosts in diesem Bereich".
- **Drawer/Context**: Klick auf Host/Service öffnet **bestehenden
  `DetailDrawer`** (gleicher `detailDrawerObject`-Pfad wie Static/Radar,
  `BoardView.vue:1715-1736`); Rechtsklick → bestehendes `ContextMenu.vue`
  (Ack/Downtime/Comment). Folder-Knoten haben keinen Drawer, aber ein
  Kontextmenü „Alle Hosts im Folder bestätigen" wäre ein Folgeschritt.

### 3.4 Operator-Workflow

1. Operator öffnet das FolderTree-Board → sieht oberste WATO-Ordner mit
   Status-Punkt + Problem-Counts.
2. **„Nur Probleme"** ist (optional) Default an → nur Äste mit
   WARN/CRIT/DOWN bleiben; alles Grüne ist zugeklappt/weg.
3. Roter Ordner → aufklappen → roter Subfolder → roter Host → roter Service.
4. Service-Klick → DetailDrawer (Output, Graphen, Acks/Downtimes).
5. **Deep-Link nach Checkmk**: `buildCheckmkUrl()`/`openUrl()`
   (`utils/boardNavigation.ts`, von AggregationSubtree `:208-211` genutzt)
   für Host/Service. Für Folder optional Deep-Link in WATO/Monitoring-View
   (`view=host&wato_folder=<path>`), analog zum CMK-`link_from_filename`
   (`cmk/gui/painter/v0/painters.py:1606`).

### 3.5 UX-Details

- **Skalierung (hunderte Hosts)**: Folder-Aggregation ist O(1) pro Host (nur
  `num_services_*`, kein Service-Roundtrip); Services lazy. Virtual-Scroll im
  Tree. „Probleme"-Filter reduziert sichtbare Knoten drastisch.
- **Performance Backend**: eine Host-Query je Tick (≙ bestehende
  `get_all_hosts_states`-Kosten + `filename`-Spalte). Service-Detail nur
  on-demand.
- **A11y/Tastatur**: ARIA `tree`/`treeitem`/`group`, `aria-expanded`,
  Pfeiltasten (←/→ collapse/expand, ↑/↓ navigieren, Enter = Drawer).
- **Visuelle Hierarchie**: Einrückung + Disclosure-Triangle + Status-Punkt;
  Folder fett, Host normal, Service gedimmt. Counts rechtsbündig.
- **NagVis-Classic-Mode**: **N/A** — `render_mode: nagvis_classic`
  (`board.py:384`) betrifft nur positionierte Static-Boards
  (Top-Left-Anchoring); ein FolderTree hat keine Koordinaten. Der Typ ignoriert
  `render_mode`.

### 3.6 Mehrwert / Abgrenzung

| Typ | Quelle | Layout | Pflege | Lücke, die FolderTree füllt |
|-----|--------|--------|--------|------------------------------|
| Static | kuratiert | Koordinaten | hoch | spiegelt keine WATO-Struktur |
| Geo/Worldmap | Geo-Labels | Karte | mittel | nur georeferenzierte Hosts |
| Flow | Parent/Child-Topologie | Force-Graph | keine | technische Abhängigkeit, nicht Org-Struktur |
| Radar | 1 Gruppe/Filter | radiale Chips | keine | flach, 1 Ebene, keine Hierarchie |
| **FolderTree** | **WATO `filename`** | **Tree** | **keine** | **operative Org-Hierarchie + Bubbling** |

FolderTree ist der einzige Typ, der die in Checkmk gepflegte
**Verwaltungsstruktur** ohne Doppelpflege als Statusbaum zeigt.

---

## 4. Risiken / offene Fragen

1. **`filename`-Verfügbarkeit**: Spalte existiert in CMK-Livestatus
   (`TableHosts.cc:540`), aber ist leer, wenn `host_paths`/`_FILENAME` nicht
   gesetzt ist (z.B. Hosts aus DCD/Programmatik ohne WATO-Datei, Nagios-Core
   ohne Checkmk). → **Fallback-Ordner „(ungeordnet)"** für Hosts ohne
   `filename`; Icinga2-Connection liefert i.d.R. keinen WATO-Pfad → dort Baum
   leer/flach. `test.py`-Backend muss `get_folder_tree()` deterministisch
   stubben.
2. **Folder-Titel vs. Slug**: `filename` liefert nur den Slug (Verzeichnis),
   nicht den WATO-Titel. Schöne Titel nur via REST `folder_config`
   (Bearer-Auth nötig). MVP: Slug; Upgrade: REST-Anreicherung mit Cache.
3. **Multisite/distributed**: `filename` ist pro Site unabhängig; gleicher
   Ordnerpfad auf zwei Sites muss verschmolzen werden (Key = Pfad, `site_id`
   am Blatt führen — `ObjectState.site_id` existiert, `state.py:46`). Pfade
   können site-spezifisch divergieren → Konflikte dokumentieren.
4. **Permissions/Contact-Group-Scoping**: `AuthUser:` filtert Hosts; ein
   Ordner, dessen Hosts der User nicht sehen darf, verschwindet oder zeigt
   unvollständige Aggregation. Das ist gewollt (kein Daten-Leak), aber Operator
   muss verstehen, dass „grün" ≠ „nichts da". Empty-State entsprechend texten.
5. **Diff-Hash im Broadcast-Loop**: Bisher difft der Loop `MapStates.states`.
   Ein eingebetteter `folder_tree` muss in den Vergleich/Hash einbezogen werden,
   sonst frieren Folder-Badges ein. Sauberere Option: eigenes SSE-Event
   `folder_tree` (analog zum Topology-Delta-Pfad `states.py:176-194`).
6. **REST-Rate/Latenz**: Falls Folder-Titel-Anreicherung pro Tick liefe, würde
   das die Site belasten → Titel separat & gecacht (TTL), nicht im State-Tick.

---

## 5. Implementierungsplan (phasenweise, mit Dateien)

### Phase 0 — Schema & Typ-Registrierung
- `backend/app/schemas/board.py`: `FolderTreeView` + Aufnahme in `BoardView`-Union.
- `backend/app/schemas/state.py`: `FolderTreeNode`; `folder_tree`-Feld an
  `MapStates` (oder eigenes SSE-Event vorbereiten).
- `frontend/src/types/api.ts`: `FolderTreeView`, `FolderTreeNode`, Union erweitern.
- `frontend/src/utils/dropdownOptions.ts:51` + `CreateBoardModal.vue:126` +
  i18n-Keys (`board.boardTypeFolderTree*`).

### Phase 1 — Datenzugriff (Livestatus, MVP via `filename`)
- `backend/app/connections/base.py`: ABC-Methode `get_folder_tree()` + `HostFolderRow`-Typ.
- `backend/app/connections/livestatus.py`: Implementierung
  (`filename`-Spalte in die bestehende Host-Query bei `:1045` aufnehmen,
  Pfad-Ableitung `removeprefix("/wato/")…`).
- `backend/app/connections/test.py`: deterministischer Fake-Folderbaum.
- `backend/app/connections/icinga2.py`: leere/flache Implementierung
  (kein WATO).

### Phase 2 — Aggregation & State-Service-Branch
- `backend/app/services/state_service.py`: `_get_folder_tree_states()`
  + Branch in `_execute_board_states()`; Bubbling über `_COMBINED_SEVERITY`,
  Host-Rollup via `_aggregate_host_with_services_from_data()`.
- `backend/app/api/v1/states.py`: sicherstellen, dass `_broadcast_loop` den
  Baum mitschickt/diffed (Hash-Anpassung oder eigenes Event).

### Phase 3 — Frontend-Renderer
- `frontend/src/components/board/FolderTreeBoard.vue` (neu): Tree-View,
  Expand/Collapse, Virtual-Scroll, Status-Badges, Worst-Path-Auto-Expand,
  „Probleme"-Toggle.
- `frontend/src/views/BoardView.vue`: Dispatch-Branch + `isFolderTree`-Computed
  + Drawer/Context-Verdrahtung (vorhandene Pfade wiederverwenden).
- `frontend/src/components/board/BoardSearch.vue`: Integration (Treffer-Pfade
  aufklappen).

### Phase 4 — Settings/Edit & i18n
- `BoardSettingsFormSpecModal.vue` + `BoardSettingsModalLegacy.vue`:
  Felder Root-Folder, `default_expand_depth`, `problems_only`, `show_services`,
  `only_hard_states` (FormSpec-Pfad zuerst deklarativ).
- i18n-Strings (de/en) für Typ, Beschreibung, Empty-States, Settings-Labels.

### Phase 5 — Veredelung (optional)
- Folder-Titel über REST `folder_config/collections/all?recursive=true`
  (`_cmk_rest()`-Pfad) mit Cache/TTL.
- Folder-Kontextmenü (Bulk-Ack/Downtime über alle Hosts im Teilbaum).
- Folder-Deep-Link in CMK-Monitoring-View (`wato_folder=<path>`).

### Tests
- Backend: Aggregations-/Pfad-Ableitungs-Unit-Tests gegen `test.py`-Backend
  (Bubbling, `problems_only`, `filename`-Edgecases inkl. leerer Wert).
- Frontend: Tree-Render-/Expand-Tests analog `BoardCanvas.test.ts`.
- Playwright: Board anlegen → Folder expandieren → Problem-Drilldown → Drawer.
