# Checkmk-Verhalten: Folder-Titel-Sichtbarkeit bei fehlender WATO-Folder-Permission

Status: Research-Befund (CMK-Source 1:1, alles Datei:Zeile-belegt)
Datum: 2026-05-30
Auftrag: Klärung von §6.4 des Folder-Tree-Board-Konzepts (v3) — „Host sichtbar,
Folder-Titel maskieren?" — gegen die echte Checkmk-Quelle.

Untersuchte Stände: `~/git/checkmk` (master = 2.6), `~/git/2.5.0`, `~/git/2.4.0`,
`~/git/2.3.0`. Verhalten ist über alle vier Stände **identisch** (nur kosmetische
API-Änderungen, s.u. „Versionsunterschiede").

---

## Kernbefund (TL;DR)

**Checkmk maskiert Folder-Titel NICHT.** In Monitoring-Views und im
WATO-Foldertree-Snapin wird der echte Folder-Titel jedes Ordners angezeigt, in
dem ein für den User (via Monitoring-Kontaktgruppe) **sichtbarer Host** liegt —
**ohne** jegliche Prüfung der WATO-Folder-Leseberechtigung (`Folder.may("read")`).

Es existiert in CMK **kein Konzept „Folder-Titel maskieren, Host aber zeigen".**
WATO-Folder-Permission und Monitoring-Sichtbarkeit sind zwei getrennte Achsen;
die Folder-Permission steuert **WATO/Setup** (Bearbeiten/Sehen von
Ordnerstrukturen im Setup, Foldertree-Reduktion), **nicht** die Anzeige des
Titels in Monitoring-Kontexten.

→ **Die vom OrbVis-Nutzer vorgeschlagene Variante „Titel maskieren" ist ein
Fremdkörper, nicht Checkmk-konform.** „1:1 Checkmk" bedeutet hier: **Titel des
befüllten Ordners zeigen** (der Host ist sichtbar ⇒ sein Ordner-Titel ist es auch).

---

## Frage 1 — Monitoring-Views / „Folder"-Painter

Der Folder-Painter sitzt in `cmk/gui/wato/views.py`:
- `PainterWatoFolderAbs` / `…Rel` / `…Plain` (`views.py:84/107/130`) und der
  Sortierer rufen alle `get_wato_folder()` (`views.py:46`).
- `get_wato_folder()` nimmt die Livestatus-Spalte `host_filename` (z.B.
  `/wato/muc/north/hosts.mk`), schneidet sie auf den WATO-Pfad zu (`views.py:47-50`)
  und löst Titel auf via:
  - `get_folder_title_path_with_links(wato_path)` (`views.py:53`) bzw.
  - `get_folder_title_path(wato_path)` (`views.py:55`).
- **Kein `may("read")`, kein `folder_should_be_shown`, keine CG-Prüfung** im
  gesamten Painter. Der einzige Fallback ist `MKGeneralException` → roher Pfad
  (`views.py:57-62`), und der greift nur bei *nicht auflösbaren* Pfaden (fremde
  Site mit abweichender Hierarchie), nicht bei fehlender Permission.

Die Auflösung selbst (`cmk/gui/watolib/hosts_and_folders.py`):
- `get_folder_title_path()` → `folder_tree().folder(path).title_path()`
  (`hosts_and_folders.py:3922-3925`) — `@request_memoize`, **kein Permission-Check**.
- `get_folder_title_path_with_links()` → `…title_path_with_links()`
  (`:3928-3930`).
- `Folder.title_path()` = `[folder.title() for folder in parent_chain + [self]]`
  (`:2012-2013`) — iteriert die **komplette Elternkette** und ruft jeweils
  `title()`.
- `Folder.title()` = `return self._title` (`:1693-1694`) — gibt schlicht den
  gespeicherten Titel zurück, **unabhängig von jeder Berechtigung**.

⇒ Sobald der Host in einer Monitoring-View auftaucht (was AuthUser-gescoped ist,
s. Frage 3), zeigt der Folder-Painter den **echten, vollständigen Titelpfad** —
auch wenn der User die zugehörigen WATO-Ordner nicht lesen darf.

## Frage 2 — WATO-Foldertree-Snapin (`wato_foldertree`)

`cmk/gui/wato/_snapins.py`:
- `SidebarSnapinWATOFoldertree.show()` (`:366`) ruft `compute_foldertree()` (`:372`).
- `compute_foldertree()` (`:243`) baut den Baum **aus einer Livestatus-Query**:
  `"GET hosts\nStats: state >= 0\nColumns: filename"` (`:245`) über `sites.live()`.
  D.h. die Ordnermenge ist exakt „alle Ordner, in denen sichtbare Hosts liegen"
  (+ deren Eltern-Pfad, `:271-281`).
- Pro Ordner: `get_folder()` → `"title": folder.title() or path.rsplit(...)`
  (`:251-253`) — **echter `title()`**, kein `may("read")`-Filter.
- `render_tree_folder()` (`:316`) rendert `"%s (%d)" % (folder["title"], num_hosts)`
  (`:326-327`) — Titel + Host-Zahl, ohne Permission-Gate.
- `reduce_tree()` (`:303-312`) entfernt nur **leere** Top-Level-Zwischenebenen
  (`len(.folders)==1 and .num_hosts==0`) — eine reine Aufräum-Heuristik, **kein**
  Permission-Filter.

**Antwort auf die Teilfrage „Ordner ohne Permission, aber mit sichtbarem Host
darunter":** Genau dieser Fall wird im Snapin gezeigt — der Ordner erscheint mit
echtem Titel, weil sein Host via Livestatus sichtbar ist. Der Snapin fragt
`Folder.may("read")` an **keiner** Stelle. (Der WATO-Foldertree-Snapin ist damit
das nächste CMK-Pendant zum OrbVis-Board und beweist: CMK gated Titel rein über
Monitoring-Sichtbarkeit, nicht über Folder-Permission.)

Hinweis: Das ist **nicht** dasselbe wie die *Setup*-Folder-Liste (Modus
`mode=folder` in `wato.py`), die sehr wohl `subfolders(only_visible=True)` /
`folder_should_be_shown("read")` benutzt (s. Frage 3). Der Snapin und die
Monitoring-Views sind die relevanten Vergleichsobjekte für ein Board.

## Frage 3 — Zwei getrennte Achsen (WATO-Folder vs. Monitoring-CG)

Ja, es sind nachweisbar **zwei getrennte Achsen**:

**Achse A — Monitoring-Sichtbarkeit (Livestatus AuthUser):**
- `cmk/gui/sites.py:507-511` `_set_livestatus_auth()` setzt auf jeder
  GUI-Livestatus-Verbindung `g.live.set_auth_user("read", user_id)`. Jede
  `GET hosts`-Query (Views, Snapin) ist damit auf die **Monitoring-Kontaktgruppen**
  des Users gescoped (`host_contact_groups` ∩ User-CGs). Dies bestimmt, **ob ein
  Host (und damit sein Ordnereintrag) überhaupt auftaucht**.

**Achse B — WATO-Folder-Permission (rein GUI/watolib, kein Livestatus):**
- `Folder.permissions.may("read")` → `PermissionChecker.may`
  (`hosts_and_folders.py:236-241`) → `_user_needs_permission("read")` (`:2100`).
- Erlaubt bei: `wato.see_all_folders` (`:2104-2105`), oder `is_contact(user)`
  (`:2107-2108`): User-CG ∩ `permitted_groups` des Ordners ≠ ∅.
- `groups()` (`:2041-2087`) liest `attributes.contactgroups` aus den
  **effektiven Folder-Attributen** inkl. Vererbung (`recurse_perms`, `:2075-2076`).
- `folder_should_be_shown("read")` (`:1924-1934`): liefert `True` wenn
  `wato_hide_folders_without_read_permissions` aus ist **(Default: `False`,
  `cmk/gui/general_config.py:627`)** — d.h. **standardmäßig werden ALLE Ordner im
  Setup gezeigt**. Selbst wenn aktiviert, genügt Permission auf **irgendeinen
  Unterordner** (`:1929-1932`), um den Ordner zu zeigen.

Diese Achse B steuert das **Setup/WATO-UI** (Folder-Editor, Move-Choices
`:1936-1967`, `subfolders(only_visible=True)` `:1821-1837`) — **nicht** die
Titelanzeige in Monitoring-Views/Snapin.

**Können die Achsen auseinanderfallen?** Ja, beidseitig:
- Host im Monitoring sichtbar (Monitoring-CG), WATO-Ordner nicht lesbar
  (keine `attributes.contactgroups`-Übereinstimmung) → Host + **echter
  Folder-Titel** erscheinen trotzdem (Painter/Snapin, s.o.).
- WATO-Ordner lesbar, aber kein sichtbarer Host (z.B. host-CG ≠ folder-CG, oder
  `use_for_services`/`recurse_use`-Konstellationen) → Ordner im Setup sichtbar,
  aber in Monitoring-Views leer.

Die CGs der beiden Achsen *können* übereinstimmen (typische Konfig: Folder-CG
mit `use=True` schreibt dieselbe CG als Host-Contactgroup), **müssen** es aber
nicht — `permitted_groups` (Achse B) und `host_contact_groups` (in den
Monitoring-Daten, Achse A) sind in `groups()` getrennte Rückgabewerte
(`:2083-2087`), gesteuert über separate Flags `use` / `recurse_perms` /
`recurse_use`.

## Frage 4 — Gibt es „Titel maskieren, Host zeigen" in CMK?

**Nein.** CMK kennt nur zwei Verhaltensweisen:
1. **Monitoring-Kontext** (Views, `wato_foldertree`-Snapin): Host sichtbar ⇒
   **voller echter Folder-Titel sichtbar**, ohne Folder-Permission-Check.
2. **Setup/WATO-Kontext** (`mode=folder`-Liste, Move-Dialoge): Ordner wird
   **ganz weggelassen**, wenn (und nur wenn) `wato_hide_folders_without_read_permissions`
   aktiv ist und weder der Ordner noch ein Unterordner lesbar ist —
   ganzer-Ordner-verbergen, **nie** „Titel maskieren".

Ein Zwischenzustand „Host darstellen, aber Folder-Namen durch Platzhalter
ersetzen" existiert in der CMK-Source an keiner Stelle. Die `title()`-Methode
hat keinen Permission-Parameter, und kein Aufrufer im Monitoring-Pfad gated sie.

---

## Versionsunterschiede 2.3 → 2.6

**Verhaltensgleich über alle vier Stände.** Belege:
- `get_wato_folder()` / Titelauflösung: identische Logik in
  `2.3.0|2.4.0|2.5.0|checkmk` `cmk/gui/wato/views.py`. Einziger Diff: 2.3 nutzt
  `HTML(" / ")`, ab 2.4 `HTML.without_escaping(" / ")` (reine API-Umbenennung,
  kein Verhaltensunterschied); 2.3 nimmt `request` global, ab 2.4 als Parameter.
- `compute_foldertree()` / `wato_foldertree`-Snapin: gleiche Livestatus-Query
  `GET hosts … Columns: filename` und gleiche `folder.title()`-Nutzung in allen
  Ständen (`_snapins.py`, Zeilen variieren: 2.3 `:240/242/249`, 2.4 `:247/249/257`,
  2.5 `:221/223/231`, 2.6 `:243/245/253`). Kein `may("read")` in irgendeiner Version.
- `wato_hide_folders_without_read_permissions`-Default `= False` unverändert.

Für die im Konzept (§9) erwähnte brechende `FolderTree.__init__`-API ab 2.5 gilt:
betrifft nur die **Instanziierung** der watolib-Objekte, **nicht** die hier
relevante Sichtbarkeits-/Titel-Semantik. OrbVis instanziiert `FolderTree`
ohnehin nicht (liest `.wato`/REST), daher irrelevant für diesen Befund.

---

## Empfehlung für die OrbVis-Umsetzung

**Verwerfe §6.4-Idee „Titel maskieren + Host zeigen". Sie ist NICHT
Checkmk-konform.** Das exakte 1:1-Checkmk-Verhalten lautet:

1. **Befüllte Ordner (Host via Monitoring-CG / AuthUser sichtbar):**
   **echten Titel zeigen — immer, ohne WATO-Folder-Permission-Check.**
   Das deckt sich exakt mit dem schon in §6.1 Fall (1) beschriebenen Verhalten
   und mit dem `wato_foldertree`-Snapin. Die in v2 verworfene Sorge „Titel
   leakt" ist hier **bewusst genau das Checkmk-Verhalten** — kein Leak im
   CMK-Sinn, weil der Host (und damit die Existenz + Lage des Ordners) für den
   User ohnehin sichtbar ist. **§6.4 ist damit aufzulösen zu: voller Titel.**

2. **Leere Ordner (kein sichtbarer Host):** Hier greift AuthUser nicht. CMKs
   Monitoring-Pfad zeigt sie gar nicht erst (sie tauchen in `GET hosts` nicht
   auf). OrbVis legt sie aus `.wato`/REST darüber → **hier ist der
   Folder-Permission-Check (§6.1–6.3) korrekt und nötig**: leeren Ordner nur
   zeigen, wenn Admin ODER User-CG ∩ effektive Folder-CG ≠ ∅; sonst
   **ganz verbergen** (nicht maskieren). Das spiegelt CMKs einzigen echten
   Folder-Verbergmechanismus (`folder_should_be_shown`/`only_visible`, Setup-Pfad).

3. **Niemals Titel-Platzhalter („(eingeschränkt)") einführen** — CMK tut das
   nirgends; es wäre ein Fremdkörper und würde Operatoren verwirren, die
   1:1-Parität erwarten.

Damit ist die Regel sauber und CMK-deckungsgleich:
**befüllt ⇒ Titel zeigen (Monitoring-Achse entscheidet) · leer ⇒
Folder-Permission-Achse entscheidet, im Zweifel verbergen.** Das Datenmodell
(Titel getrennt von Host-Kindern) bleibt, aber der `title`-Override entfällt.
