# Board-Typ: Checkmk SETUP-Ordnerbaum ("Folder Tree" Board) — v2

Status: Konzept (Überarbeitung von v1 nach tiefer CMK-Source-Analyse)
Autor: Recherche-Agent
Datum: 2026-05-30
Vorgänger: `board-type-setup-folders-concept.md` (v1, unverändert gültig als
fachliche Kernidee; v2 ersetzt v1 bei der **Datenquellen-/Architekturwahl**).

> Diese v2 ergänzt v1 um eine konkrete, an Datei:Zeile belegte Checkmk-Source-
> Analyse und trennt sauber zwischen **CMK-integriertem Modus** und
> **Standalone-Modus**. Die Kernidee (aufklappbarer Statusbaum entlang der
> WATO-Ordnerhierarchie mit Worst-State-Bubbling) bleibt unverändert; v1 §1,
> §3.3–3.6, §4 (UX/Frontend/Workflow) gelten weiter.

---

## 0. Kernaussage vorab (für Eilige)

Die WATO-Folder-**Struktur + Titel** sind in Checkmk in der watolib-Klasse
`FolderTree`/`Folder` gekapselt — diese ist aber **request-context-gebunden**
(`flask.g`, `active_config`, `cmk.gui.logged_in.user`) und zieht beim Import die
gesamte `cmk.gui.*`-Render-Maschinerie nach. Das ist exakt die Klasse von
Abhängigkeit, die OrbVis bei der BI-Integration bewusst vermieden hat (vgl.
`backend/app/integrations/checkmk.py:311-318`). **Direktes Importieren von
`hosts_and_folders.FolderTree` in OrbVis ist daher nicht praktikabel** und
würde dem Memory-Prinzip „nur das nutzen, was ohne GUI-Request lädt"
widersprechen.

Konsequenz für die Mode-Wahl:

- **Live-Status** (für Bubbling) → in **beiden** Modi über Livestatus
  `host.filename` (eine Query, stabil 2.3–2.6).
- **Struktur + Folder-Titel + leere Ordner**:
  - **CMK-Modus**: NICHT über `FolderTree` importieren, sondern die
    **`.wato`-Dateien direkt parsen** (dieselben Dateien, die `Folder.load()`
    liest) — mit OrbVis' bereits vorhandenem `exec_mk_file()`/Object-Store-
    Muster. Pfadauflösung über `cmk.utils.paths` (leichtgewichtig, schon
    importiert). Das gibt Titel + leere Ordner **ohne** GUI-Kontext.
  - **Standalone-Modus**: rein aus `host.filename`-Slugs abgeleitet (keine
    Titel, keine leeren Ordner) — der degradierte, OrbVis-native Pfad.
- **CMK-Frontend-UI** (Tree-Snapin / Vue-Tree): **realistisch nicht nutzbar**
  (Begründung §4). Renderer bleibt eine neue, OrbVis-eigene Vue-Komponente.

---

## 1. Checkmk-Source-Analyse (mit Datei:Zeile, Versionsmatrix)

Quellen: `~/git/checkmk` (master ≈ 2.6), `~/git/2.5.0`, `~/git/2.4.0`,
`~/git/2.3.0`. Ziel-Support 2.3–2.6.

### 1.1 watolib `FolderTree` / `Folder` — Struktur, Titel, Permissions

**Klassen vorhanden in allen vier Versionen:**

| Symbol | master | 2.5.0 | 2.4.0 | 2.3.0 |
|---|---|---|---|---|
| `class FolderTree` | `hosts_and_folders.py:1010` | `:1006` | `:944` | `:942` |
| `class Folder(FolderProtocol)` | `:1228` | `:1224` | `:1141` | `:1126` |
| `def folder_tree()` (Factory) | `:1141` | `:1137` | `:1058` | `:1043` |

**API-Drift `FolderTree.__init__` (HART, brechend):**

- 2.3/2.4: `def __init__(self, root_dir: str | None = None)`
  (`2.3.0/…:945`, `2.4.0/…:947`)
- **2.5/2.6: `def __init__(self, root_dir=None, *, config: HostsAndFoldersConfig)`**
  (`2.5.0/…:1009`, `checkmk/…:1013`) — **neuer, pflicht-keyword-only Parameter
  `config`**. Wer `FolderTree()` direkt baut, muss ab 2.5
  `HostsAndFoldersConfig.from_config(active_config)` mitgeben
  (`checkmk/…:1143`). Das wiederum braucht `active_config` (Request-Kontext).

**Request-Kontext-Bindung (der eigentliche Show-Stopper):**

- `FolderTree.all_folders()` liest/füllt `flask.g`:
  `checkmk/…:1025-1028` (`if "wato_folders" not in g: g.wato_folders = …`),
  identisch `2.3.0/…:948-951`. Ohne `flask.g` (= ohne aktiven Request) wirft
  das bzw. liefert nichts Brauchbares.
- Die Disk-Walk-Variante `_get_fully_loaded_wato_folders()`
  (`checkmk/…:732-737`) ruft `Folder.load(tree=…, name="", parent_folder=None)`
  rekursiv — das wäre an sich datei-getrieben, aber `Folder.load()` ruft
  `edition(cmk.utils.paths.omd_root)` und `folder_validators_registry[…]`
  (`checkmk/…:1273`), und das **Modul** `hosts_and_folders.py` importiert am
  Kopf die volle GUI-Schicht:
  `cmk.gui.config.active_config` (`:47`), `cmk.gui.ctx_stack.g` (`:48`),
  `cmk.gui.htmllib.html` (`:53`), `cmk.gui.http.request` (`:54`),
  `cmk.gui.logged_in.user` (`:57`), `cmk.gui.page_menu` (`:58`),
  `cmk.gui.session_context` (`:60`) u.v.m.
  → Schon der **Import** des Moduls aktiviert die GUI-Render-Maschinerie;
  genau das, wovor `checkmk.py:311-318` (BI-Kommentar) warnt.
- Permissions/Scoping sind ebenfalls request-gebunden:
  `Folder.permitted_groups()` (`checkmk/…:203`), `Folder.may("read"/"write")`
  (`:236`), `Folder.folder_should_be_shown()` (`:1924`) lesen alle
  `active_config.*` und `cmk.gui.logged_in.user`. Außerhalb eines GUI-Requests
  gibt es keinen `user` → kein verlässliches Folder-Permission-Scoping über
  watolib.

**Was watolib trotzdem verrät (nützlich als Spezifikation, nicht als Import):**

- Titel-Quelle: `Folder.load()` liest den Titel direkt aus der `.wato`-Datei:
  `title=serialized.get("title", _fallback_title(folder_path))`
  (`checkmk/…:1277`). Fallback-Titel = Basename des Pfads (`:2925-2928`).
- Die `.wato`-Datei liegt unter `<folder>/.wato`
  (`_folder_wato_info_path`, `checkmk/…:2931-2932`) und ist ein
  Python-Literal-Dict (`StandardWATOInfoStorage.read` →
  `store.load_object_from_file`, `checkmk/…:748-750`) mit u.a.
  `title`, `attributes`, `__id`, `num_hosts`.
- WATO-Root-Verzeichnis: `wato_root_dir() = cmk.utils.paths.check_mk_config_dir
  / "wato"` (`cmk/gui/watolib/utils.py:22-23`). `check_mk_config_dir` =
  `<omd>/etc/check_mk/conf.d` (vgl. v1 §2.2). **`cmk.utils.paths` ist
  leichtgewichtig und in OrbVis bereits der Standard** (Memory:
  „always use settings.checkmk_omd_root / cmk.utils.paths").

→ **Empfehlung CMK-Modus**: Struktur + Titel + leere Ordner aus den
`.wato`-Dateien selbst lesen (Walk über `conf.d/wato/`), NICHT via
`FolderTree`. Das ist exakt das Muster, das OrbVis schon hat
(`exec_mk_file`/Object-Store-Read) und das ohne Request-Kontext läuft.

### 1.2 Folder-Status-Aggregation — gibt es die in Checkmk fertig?

**Nein, nicht außerhalb der GUI/Redis.** Befunde:

- Keine Livestatus-`folder`-Tabelle und keine Livestatus-Spalte, die einen
  aggregierten Folder-Status liefert. Die einzige Folder-Verknüpfung auf der
  Monitoring-Seite ist `host.filename` (Custom-Var `FILENAME`):
  `packages/livestatus/src/TableHosts.cc:540` (master), stabil identisch
  `2.5.0:541`, `2.4.0:539`, `2.3.0:538`.
- `Folder.num_hosts_recursively()` (`checkmk/…:1793-1802`) zählt nur Hosts und
  greift im Normalfall auf **Redis-Folder-Metadaten** zu
  (`self.tree.redis_client.folder_metadata(...)`) — also wieder
  request-/redis-gebunden, und es ist ohnehin nur ein Host-Count, kein Status.
- Die GUI gruppiert Monitoring-Views per `host_filename`-Painter
  (`cmk/gui/painter/v0/painters.py`, „link_from_filename"), aber das ist
  reine Anzeige, keine wiederverwendbare Aggregations-API.

→ **Folder-Status muss OrbVis selbst bubbeln** (wie in v1 §2.3), aus den
Live-Host/Service-Daten. Keine CMK-Funktion vorhanden, die das abnimmt.

### 1.3 GUI-Tree-Rendering / Snapins / cmk-frontend-vue

- Sidebar-Snapin „WATO Foldertree": `cmk/gui/wato/_snapins.py`
  (`SidebarSnapinWATOFoldertree`, `:349`; Renderer `render_tree_folder`,
  `:316-346`). Nutzt `folder_tree()` (`:266`) und rendert **server-seitig
  HTML** über `html.open_ul()/html.li()` (`:322-346`) — vollständig an den
  GUI-Request + `html`-Writer gebunden. **Nicht wiederverwendbar** in OrbVis.
- `cmk-frontend-vue`: **keine** generische Tree-Komponente. Suche nach
  `*tree*`-Dateien unter `packages/cmk-frontend-vue/src` → 0 Treffer; Suche
  nach `role="tree"`/`treeitem`/`aria-expanded` findet nur Dropdown/Accordion-
  Trigger (`components/CmkDropdown/…`, `components/CmkAccordion/…`), keinen
  Folder-/Hierarchie-Tree. Zudem ist cmk-frontend-vue eine private SPA, kein
  Library-Export (Memory: „cmk-frontend-vue ist private SPA … Vendoring +
  Drift-Check ist der gangbare Weg").

→ **CMK-UI realistisch nutzbar: nichts Tree-Spezifisches.** Bestenfalls
allgemeine Tokens/Buttons (`CmkButton`, State-Farben) im FormSpec-fähigen
Modus, wie OrbVis es ohnehin tut. Der Tree-Renderer ist neu zu bauen
(OrbVis-eigene Vue-Komponente, siehe v1 §3.3 — unverändert gültig).

### 1.4 REST-API `folder_config`

- Endpoint `list_folders` vorhanden:
  `cmk/gui/openapi/endpoints/folder_config/__init__.py:397`
  (`GET domain-types/folder_config/collections/all`), Query-Params
  `recursive` (`:378`) und `show_hosts` (`:383`); rekursiv via
  `parent.subfolders_recursively()` (`:402`), serialisiert in
  `_folders_collection(...)` (`:409-418`, Hosts als Sub-Collection bei
  `show_hosts`). Liefert **autoritative Hierarchie inkl. Titel und leerer
  Ordner**, und respektiert serverseitig die Permissions des
  automation/REST-Users (`need_recursive_permission("read")`, `:401`).
- REST ist die **einzige** Struktur-/Titel-Quelle, die auch **standalone**
  (ohne `cmk.*`) funktioniert — vorausgesetzt automation-Credentials liegen
  vor. OrbVis hat den REST-Pfad bereits: `_cmk_rest()` /
  `_cmk_rest_base()` in `connections/livestatus.py:1578` / `:1569`.
- Nachteil REST: zusätzlicher HTTP-Roundtrip + Latenz; Titel/Struktur ändern
  sich selten → **mit TTL cachen, nicht pro State-Tick** (vgl. v1 §4.6).

### 1.5 Wie OrbVis cmk-Module heute sicher über 2.3–2.6 importiert

- Bootstrapping: `integrations/checkmk.py:setup()` (`:26-57`) hängt
  `lib/python3` + `lib/python3.*/site-packages` an `sys.path`, smoke-testet
  `import cmk.utils.paths` und setzt `available`. Alles Weitere ist
  best-effort.
- Muster „try-import, sonst Fallback": überall, z.B.
  `from cmk.gui.userdb.store import load_user` mit `except` → File-Fallback
  (`checkmk.py:52-57`, `:113-125`), `from cmk.utils.paths import
  livestatus_unix_socket` mit `except ImportError` (`checkmk_sites.py:139-142`).
- **Ports statt Import**, wenn das cmk-Symbol request-gebunden ist:
  `checkmk_sites.py:12-22` portiert `cmk.gui.site_config.enabled_sites` /
  `is_single_local_site`, **weil** `cmk.gui.sites` flask/g/active_config am
  Modulkopf importiert „and cannot be imported outside a GUI request context"
  und sich die API zwischen Versionen ändert. **Genau dieselbe Begründung
  trifft 1:1 auf `hosts_and_folders.FolderTree` zu** → Port/Reimplementierung
  (hier: `.wato`-Walk) ist das etablierte, vom Projekt gesegnete Vorgehen.
- BI als Präzedenzfall für „nur das compute-Subpaket nutzen, nicht die GUI":
  `checkmk.py:306-352` importiert ausschließlich `cmk.bi.*` (pure compute),
  explizit **nicht** `cmk.gui.bi.*` „which would require … flask, WSGI, or
  edition-feature-registry shenanigans".

**Versions-Inkompatibilitäten watolib 2.3→2.6 (relevant):**

1. `FolderTree.__init__` keyword-only `config` ab 2.5 (s. 1.1) — brechend für
   direkten Konstruktoraufruf.
2. `recursive_subfolder_choices(pretty=…)` existiert 2.3 (`2.3.0:955`) und
   master (`checkmk:1032`), aber das ist GUI-intern; irrelevant beim
   `.wato`-Walk.
3. `.wato`-Dateiformat (`title`, `attributes`, `__id`, `num_hosts`) ist über
   2.3–2.6 **stabil** (gleiche `serialized.get("title", …)`-Logik). Robust:
   `title` mit `_fallback_title`=Basename defaulten, fehlende Keys tolerieren.
4. `host.filename`-Spalte: über 2.3–2.6 **unverändert** (s. 1.2) — die
   sicherste Quelle, der einzige modusübergreifende gemeinsame Nenner.

---

## 2. Architektur: Mode-Split mit gemeinsamer Abstraktion

### 2.1 Gemeinsames Interface (Frontend-Renderer identisch)

Ein Backend-Interface, zwei Struktur-Implementierungen, **eine** Bubbling-/
Renderer-Schicht:

```python
# connections/base.py (ABC)
class ConnectionBase(ABC):
    async def get_folder_tree(self, root: str, *, only_hard: bool) -> FolderTreeData: ...
```

`FolderTreeData` bündelt: (a) flache Folder-Struktur (Pfad → {title, parent,
is_empty}), (b) Host-Rows mit `filename`/State/Service-Counts/`site_id`. Die
**Aggregation** (`_get_folder_tree_states()` im state_service) ist modusagnostisch
und arbeitet nur auf `FolderTreeData` — egal woher Struktur/Titel kamen.

### 2.2 CMK-integrierter Modus

Datenquellen:

- **Struktur + Titel + leere Ordner**: Walk über
  `cmk.utils.paths.check_mk_config_dir / "wato"`; pro Verzeichnis die
  `.wato`-Datei via OrbVis-`exec_mk_file()`-Muster (bzw. analog
  `store.load_object_from_file`) lesen → `title`. Fehlt die Datei/`title`:
  Basename als Slug (`_fallback_title`-Verhalten nachbilden). Leere Ordner
  erscheinen, weil sie als Verzeichnis existieren.
  - Versions-Guard: nur `cmk.utils.paths` (stabil) wird importiert; **kein**
    `cmk.gui.*`. Wrappen in `if integrations.checkmk.available: …` mit
    `try/except` → bei Importfehler automatisch Fallback auf Standalone-Pfad.
- **Live-Status**: Livestatus-Host-Query mit `filename`-Spalte (s. 2.4),
  multisite- + permission-sicher über den bestehenden `with_auth_user()`-Kontext.
- **Permissions**: NICHT über `Folder.may()` (request-gebunden), sondern
  implizit über Livestatus `AuthUser:` — Hosts, die der User nicht sehen darf,
  fehlen in den Rows. `.wato`-Walk liefert zwar alle Verzeichnisnamen, aber
  ein Ordner ohne sichtbare Hosts wird (bei `problems_only`/leeren Filtern)
  ausgeblendet bzw. als „leer/keine Sicht" markiert. **Trade-off:** Folder-
  *Titel* selbst sind nicht permission-gescoped (Titel ist kein Geheimnis;
  Host-/Service-Daten bleiben gescoped). Im Risiko-Abschnitt dokumentieren.

Nicht verwenden (mit Begründung im Code-Kommentar, analog `checkmk_sites.py`):
`cmk.gui.watolib.hosts_and_folders.FolderTree`, `cmk/gui/wato/_snapins.py`.

### 2.3 Standalone-Modus

Datenquellen:

- **Struktur**: ausschließlich aus `host.filename`-Slugs abgeleitet
  (`removeprefix("/wato/").removesuffix("/hosts.mk").strip("/")`, vgl. v1 §2.2).
  Zwischenordner implizit aus den Pfadsegmenten anlegen.
- **Titel**: = letztes Pfadsegment (Slug). **Optionale** Anreicherung über
  REST `folder_config?recursive=true` *falls* automation-Credentials
  konfiguriert sind (mit TTL-Cache); sonst Slug.
- **Live-Status**: identische Livestatus-Query wie CMK-Modus.
- **Permissions**: über Livestatus `AuthUser:` (wie immer in OrbVis standalone).

Was **nicht** geht (bewusste Degradierung, im Empty-State/Tooltip kommunizieren):

1. **Echte Folder-Titel** ohne REST → nur Slugs.
2. **Leere Ordner** (ohne Hosts) sind unsichtbar (kein `filename` referenziert
   sie). Nur via REST sichtbar.
3. **Folder-Permission-Scoping** existiert nicht über Slugs hinaus; was nicht
   in den (AuthUser-gefilterten) Host-Rows ist, taucht nicht auf — das ist
   sicher (kein Leak), aber „grün/leer" ≠ „nichts da".
4. **Nicht-Checkmk-Backends** (Icinga2): kein `filename` → flacher/leerer Baum;
   `test.py` stubbt deterministisch.

### 2.4 Gemeinsame Livestatus-Query (beide Modi)

Erweiterung der bestehenden `get_all_hosts_states()`
(`connections/livestatus.py:1820-1827`) bzw. eine Schwester-Methode:

- Heute: `Columns: name {state} plugin_output perf_data acknowledged
  scheduled_downtime_depth {_HOST_EXTRA_COLS}` über `_query_with_site(...)`
  (site-getaggte Rows → multisite-sicher; `site_id` ans Blatt, `ObjectState.
  site_id` existiert: `schemas/state.py:46`).
- Für FolderTree zusätzlich: **`filename`** (Ordnerzuordnung) sowie
  `num_services_ok/warn/crit/unknown/pending` (Folder-Donut ohne Service-
  Roundtrip). `_HOST_EXTRA_COLS` (`livestatus.py:449-452`) enthält aktuell
  `address alias …`, aber **keine** `num_services_*`/`filename` → diese ergänzen
  (entweder in `_HOST_EXTRA_COLS` global oder in einer FolderTree-eigenen
  Spaltenliste, um andere Pfade nicht zu verteuern).
- `with_auth_user()` (`livestatus.py:712`) wird vom aufrufenden
  `get_board_states()` bereits gesetzt → Permission-Scoping gratis.

---

## 3. Status-Bubbling (unverändert aus v1 — bestehende Helfer wiederverwenden)

- Skala: `_COMBINED_SEVERITY` (`services/state_service.py:36`) — einheitlicher
  Rang Host+Service.
- Host-Rollup: `_aggregate_host_with_services_from_data()`
  (`state_service.py:561-568`) — Host-State vs. Service-Schwere verschmelzen.
- Folder-Rollup: rekursiv `worst = max(child_states, key=_COMBINED_SEVERITY.get)`
  — identisches Muster wie der Map-Link-Rollup (`state_service.py:553`).
- Branch-Anker: `_execute_board_states()` (`state_service.py:126`) verzweigt
  heute auf `cfg.view.type == "radar"` (`:133`); neuer `foldertree`-Branch
  parallel dazu → `_get_folder_tree_states()`.
- Response-Schema `FolderTreeNode` wie v1 §3.1 (Vorlage `AggregationNode`,
  `schemas/state.py`). In `MapStates` (`schemas/state.py:115`) optional
  einbetten **oder** eigenes SSE-Event (Diff-Hash-Risiko, v1 §4.5).

---

## 4. CMK-UI: realistische Einschätzung

| CMK-Asset | Wiederverwendbar? | Begründung |
|---|---|---|
| `hosts_and_folders.FolderTree` (Struktur) | **Nein** (Import) / **ja als Spec** | request-/`g`-gebunden, brechende `__init__`-API ab 2.5, zieht volle `cmk.gui.*` |
| `.wato`-Dateien (Titel/Struktur) | **Ja** (CMK-Modus) | reine Disk-Daten, Format 2.3–2.6 stabil, OrbVis hat `exec_mk_file` |
| REST `folder_config` | **Ja** (beide Modi, opt.) | HTTP, kein `cmk.*`-Import nötig; cachen |
| Sidebar-Snapin `_snapins.py` | **Nein** | server-HTML via `html.*`, GUI-gebunden |
| cmk-frontend-vue Tree | **Nein** | existiert nicht; SPA nicht als Library exportiert |
| `CmkButton`/State-Farben (FormSpec-Modus) | **Ja** (allgemein) | wie OrbVis es bereits tut |

Fazit: Der **Renderer bleibt OrbVis-eigen** (neue
`components/board/FolderTreeBoard.vue`, v1 §3.3). Aus CMK kommt im CMK-Modus
nur **Daten** (Titel via `.wato`), keine UI.

---

## 5. Risiken / Versions-Matrix

| Risiko | Modus | Schwere | Mitigation |
|---|---|---|---|
| `FolderTree.__init__`-API-Drift (config ab 2.5) | CMK | hoch | gar nicht importieren; `.wato`-Walk |
| `cmk.gui.*`-Import zieht GUI-Maschinerie | CMK | hoch | nur `cmk.utils.paths`; try/except → Standalone-Fallback |
| `.wato`-Format ändert sich | CMK | niedrig | `dict.get(..., default)`, Basename-Fallback |
| `filename` leer (DCD/Programm-Hosts, Nicht-WATO) | beide | mittel | Fallback-Ordner „(ungeordnet)" |
| Folder-Permission nur über AuthUser, nicht über Titel | beide | mittel | dokumentieren; Host-/Svc-Daten bleiben gescoped, kein Leak |
| Standalone: keine Titel/leeren Ordner | standalone | niedrig | Slug-Titel; optional REST mit TTL |
| Diff-Hash friert `folder_tree` ein | beide | mittel | eigenes SSE-Event oder Hash erweitern (v1 §4.5) |
| Große Bäume (1000e Hosts) | beide | mittel | eine Host-Query/Tick, Services lazy, Frontend-Virtual-Scroll |
| REST-Last bei Titel-Anreicherung | beide | niedrig | TTL-Cache, nicht pro Tick |
| Distributed: gleicher Pfad auf mehreren Sites | beide | mittel | Key = Pfad, `site_id` am Blatt führen (v1 §4.3) |

Versions-Matrix der genutzten Symbole:

| Symbol/Quelle | 2.3 | 2.4 | 2.5 | 2.6 | OrbVis-Nutzung |
|---|---|---|---|---|---|
| Livestatus `host.filename` | ✓ | ✓ | ✓ | ✓ | **beide Modi** (primär) |
| `cmk.utils.paths.check_mk_config_dir` | ✓ | ✓ | ✓ | ✓ | CMK-Modus (`.wato`-Walk) |
| `.wato`-Datei `title` | ✓ | ✓ | ✓ | ✓ | CMK-Modus |
| REST `folder_config?recursive` | ✓ | ✓ | ✓ | ✓ | optional, beide Modi |
| `FolderTree`/`Folder` Direktimport | ✗ vermeiden | ✗ | ✗ (config!) | ✗ | **nicht nutzen** |

---

## 6. Implementierungsplan (phasenweise, Datei-Touchpoints, nach Modus getrennt)

### Phase 0 — Schema & Typ-Registrierung (modusagnostisch)
- `backend/app/schemas/board.py`: `FolderTreeView` + Aufnahme in
  `BoardView`-Union (Felder wie v1 §3.1: `root_folder`,
  `default_expand_depth`, `problems_only`, `show_services`, `only_hard_states`).
- `backend/app/schemas/state.py`: `FolderTreeNode`; Einbettung in `MapStates`
  (`:115`) oder eigenes Event.
- `frontend/src/types/api.ts`: `FolderTreeView`, `FolderTreeNode`, Union.
- `frontend/src/utils/dropdownOptions.ts` + `CreateBoardModal.vue` + i18n.

### Phase 1 — Gemeinsame Abstraktion + Standalone-Pfad (MVP)
- `backend/app/connections/base.py`: ABC `get_folder_tree()` + `FolderTreeData`.
- `backend/app/connections/livestatus.py`: Standalone-Implementierung —
  `filename`+`num_services_*` an die Host-Query (`:1820` / `_HOST_EXTRA_COLS`
  `:449`), Pfad-Slug-Ableitung; `_query_with_site` für multisite/`site_id`.
- `backend/app/connections/test.py`: deterministischer Fake-Baum.
- `backend/app/connections/icinga2.py`: leerer/flacher Baum.

### Phase 2 — Aggregation & State-Service-Branch (modusagnostisch)
- `backend/app/services/state_service.py`: `_get_folder_tree_states()` +
  Branch in `_execute_board_states()` (`:126`/`:133`); Bubbling via
  `_COMBINED_SEVERITY` (`:36`), Host-Rollup `_aggregate_host_with_services_
  from_data()` (`:561`); `problems_only`-Pruning.
- `backend/app/api/v1/states.py`: `_broadcast_loop` schickt/difft den Baum.

### Phase 3 — CMK-Modus-Anreicherung (Struktur + Titel + leere Ordner)
- `backend/app/integrations/checkmk.py` (oder neues
  `integrations/checkmk_folders.py` analog `checkmk_sites.py`): Funktion
  `read_wato_folder_tree(root)` — Walk `cmk.utils.paths.check_mk_config_dir/
  "wato"`, `.wato`-Read via `exec_mk_file`/Object-Store, Titel/leere Ordner;
  guarded by `available`, try/except → None.
- `livestatus.py`: CMK-Modus-Variante von `get_folder_tree()` merged
  `read_wato_folder_tree()`-Struktur mit den Live-Host-Rows.
- Kopf-Kommentar mit der „nicht FolderTree importieren"-Begründung (Muster
  `checkmk_sites.py:12-22`).

### Phase 4 — Frontend-Renderer (modusagnostisch, OrbVis-eigen)
- `frontend/src/components/board/FolderTreeBoard.vue` (neu) — v1 §3.3:
  aufklappbarer `<ul role="tree">`, Virtual-Scroll, State-Badges via
  `stateColors`, Worst-Path-Auto-Expand, „Probleme"-Toggle, `--icon-halo`.
- `frontend/src/views/BoardView.vue`: Dispatch + `isFolderTree`, Drawer/Context
  wiederverwenden (`:1715-1736`).
- `BoardSearch.vue`-Integration; DetailDrawer/ContextMenu für Blätter.

### Phase 5 — Settings/Edit & Veredelung
- `BoardSettingsFormSpecModal.vue` + `BoardSettingsModalLegacy.vue`:
  Felder (Root-Folder, Tiefe, Toggles), FormSpec zuerst deklarativ.
- Optionale REST-Titel-Anreicherung (`_cmk_rest` `:1578`) mit TTL-Cache
  (auch für Standalone-Titel/leere Ordner).
- Folder-Bulk-Aktionen, Folder-Deep-Link in CMK-Monitoring (`wato_folder=`).

### Tests
- Backend: Pfad-Ableitung + Bubbling + `problems_only` gegen `test.py`;
  CMK-Modus `.wato`-Parsing gegen ein Fixture-`conf.d/wato`-Verzeichnis (kein
  laufendes OMD nötig).
- Frontend: Tree-Render/Expand analog `BoardCanvas.test.ts`.
- Playwright: anlegen → expandieren → Drilldown → Drawer; CMK- und
  Standalone-Modus separat.

---

## 7. Zusammenfassung (kompakt)

- **Wiederverwendbare CMK-Module (Datei:Zeile):** Livestatus `host.filename`
  (`packages/livestatus/src/TableHosts.cc:540`, stabil 2.3–2.6) als primäre
  Folder-Quelle in BEIDEN Modi; `cmk.utils.paths.check_mk_config_dir` +
  `.wato`-Dateien (`cmk/gui/watolib/utils.py:22`, Titel-Logik
  `hosts_and_folders.py:1277`/`:2925`) für CMK-Modus-Titel; REST
  `folder_config` (`cmk/gui/openapi/endpoints/folder_config/__init__.py:397`)
  optional in beiden Modi. OrbVis-Reuse: `_COMBINED_SEVERITY`
  (`state_service.py:36`), `_aggregate_host_with_services_from_data()` (`:561`),
  `with_auth_user()` (`livestatus.py:712`), `_cmk_rest()` (`:1578`).
- **NICHT nutzbar:** `watolib.FolderTree`/`Folder` (request-/`g`-gebunden,
  brechende `__init__`-API ab 2.5: `checkmk:1013` vs `2.3.0:945`; zieht volle
  `cmk.gui.*`), Sidebar-Snapin `_snapins.py:349` (server-HTML), cmk-frontend-vue
  (keine Tree-Komponente vorhanden, private SPA).
- **CMK-Modus Datenquelle:** Live-Status via Livestatus+`filename`; Struktur/
  Titel/leere Ordner via direktem `.wato`-Walk (kein GUI-Kontext).
- **Standalone Datenquelle:** alles aus `host.filename`-Slugs; Titel=Slug,
  keine leeren Ordner, optional REST mit TTL-Cache. Permission über AuthUser.
- **CMK-UI realistisch nutzbar:** nichts Tree-Spezifisches — Renderer bleibt
  OrbVis-eigen; aus CMK kommt nur Daten.
- **Versions-Risiken 2.3–2.6:** `FolderTree.__init__`-Drift (config ab 2.5)
  und der GUI-Import-Chain sind die Hauptgründe, watolib zu meiden;
  `filename` + `.wato`-Format + `cmk.utils.paths` sind über alle vier
  Versionen stabil; Import-Guards via `integrations.checkmk.available` +
  try/except → automatischer Standalone-Fallback.
- **Top-Implementierungsschritte:** (1) `FolderTreeView`/`FolderTreeNode`-
  Schemas + Union; (2) Livestatus-Host-Query um `filename`+`num_services_*`
  erweitern (Standalone-MVP); (3) `_get_folder_tree_states()`-Branch mit
  bestehendem Bubbling; (4) CMK-Modus `.wato`-Walk für Titel/leere Ordner
  (guarded); (5) `FolderTreeBoard.vue`-Renderer + Settings.
