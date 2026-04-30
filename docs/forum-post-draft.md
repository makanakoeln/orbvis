# Forum-Post-Entwurf — OrbVis Community-Ankündigung

Entwurf für den Checkmk-Forum-Beitrag, in dem OrbVis als potentieller
NagVis-Nachfolger zum Community-Test vorgestellt wird. Vor dem
Veröffentlichen die `<…>`-Platzhalter ausfüllen und mit den
Forum-Verantwortlichen abstimmen.

Dieser Entwurf ist intentional ehrlich (Beta-Status, fehlende Features
explizit benannt) — Erwartungs-Management spart später Konflikte.

---

## Titel

> **OrbVis — ein moderner NagVis-Nachfolger für Checkmk (Community-Beta)**

Alternativ-Titel:

- *OrbVis: Live-Visualisierung für Checkmk, Community-Preview*
- *Vorstellung: OrbVis (NagVis-Reimplementierung, GPL-2.0)*

## Body

> *Hi zusammen,*
>
> nach längerer Eigenarbeit möchte ich der Community **OrbVis**
> vorstellen — eine neu gebaute Visualisierungs-Oberfläche für
> Checkmk, die NagVis als Nachfolger ablösen kann, sobald sie reif
> genug dafür ist. Heute öffne ich das Repo und veröffentliche die
> erste MKP. Ziel des Posts: Feedback einsammeln, Mit-Tester finden.
>
> ---
>
> ### Was OrbVis ist
>
> - Frontend: Vue 3 + TypeScript, kein PHP, kein jQuery.
> - Backend: Python 3.12, FastAPI, SQLAlchemy 2.0 async.
> - States kommen per **WebSocket** in Echtzeit ins Frontend — kein
>   Polling mehr.
> - Vier Board-Typen: **Static** (klassischer NagVis-Ersatz),
>   **Flow** (force-directed Topologie), **Radar** (Severity-Grid),
>   **Geo** (Leaflet-Karte mit Lat/Lng-Objekten und -Linien).
> - Native Checkmk-Integration: Sidebar-Snapin, Menü-Eintrag,
>   SSO via Checkmk-Cookie, htpasswd-Fallback.
> - GPL-2.0-only, gleiche Lizenz wie NagVis und Checkmk Raw.
>
> ![OrbVis board view](<screenshot-url-1>)
> ![Edit mode](<screenshot-url-2>)
>
> ---
>
> ### Was bereits funktioniert
>
> Die wichtigsten NagVis-Konzepte sind da: Hosts, Services, Hostgroups,
> Servicegroups, Lines (inkl. Weathermap mit Bandbreiten-Farben),
> Textboxen, Bilder, Map-Links, Hover-Menüs, Kontextmenüs,
> Acknowledged/Downtime-Indikatoren, `only_hard_states`,
> `recognize_services`, Kiosk-Mode mit Rotation.
>
> Eine Vergleichs-Matrix mit allen Punkten ist im Repo:
> [docs/comparison.md](https://github.com/makanakoeln/orbvis/blob/main/docs/comparison.md).
>
> ---
>
> ### Was (noch) fehlt
>
> Damit niemand mit falschen Erwartungen reinrennt:
>
> - **LDAP** (für Standalone): noch nicht. Checkmk-SSO funktioniert.
> - **Audit-Log**: noch nicht.
> - **Plugin-API** für eigene Gadgets: noch nicht.
> - **Custom NagVis-Gadgets**: nur die Standard-Gadgets (gauge, bar)
>   importiert der Konverter automatisch — Custom-PHP-Gadgets
>   landen als Icons und müssen manuell nachgebaut werden.
> - **Mobile-Editor**: Boards rendern auf Mobile, der Editor ist
>   Desktop-first.
>
> Eine vollständige Roadmap mit Quartalszielen liegt in
> [ROADMAP.md](https://github.com/makanakoeln/orbvis/blob/main/ROADMAP.md).
>
> ---
>
> ### NagVis-Migration
>
> Das Repo enthält `tools/cfg_importer.py`, das `.cfg`-Maps direkt in
> OrbVis-JSON konvertiert. Schritt-für-Schritt-Anleitung mit
> Erklärung was übernommen wird und was nicht:
> [docs/migration-from-nagvis.md](https://github.com/makanakoeln/orbvis/blob/main/docs/migration-from-nagvis.md).
>
> Empfehlung: ein, zwei Boards probemigrieren, OrbVis ein bis zwei
> Wochen parallel laufen lassen, dann erst NagVis abschalten.
>
> ---
>
> ### Installation auf einer Checkmk-Site
>
> Es gibt zwei MKPs — eines für Checkmk 2.3 / 2.4, eines für 2.5+:
>
> ```bash
> omd su <site>
> mkp add ~/orbvis-X.Y.Z-cmk2.3.mkp     # CMK 2.3 / 2.4
> # oder: ~/orbvis-X.Y.Z-cmk2.5.mkp     # CMK 2.5+
> mkp enable orbvis
> orbvis-setup
> ```
>
> Danach: `https://<host>/<site>/orbvis/` öffnen, das initiale
> Admin-Passwort steht einmalig in `$OMD_ROOT/var/log/orbvis.log`.
>
> Detail-Doku: [docs/install.md](https://github.com/makanakoeln/orbvis/blob/main/docs/install.md).
>
> ---
>
> ### Live-Demo
>
> *<Demo-URL einfügen — derzeit noch kein öffentlicher Endpoint
> bereitgestellt; wenn Demo-Site online ist, hier verlinken>*
>
> Login: `<demo-user>` / `<demo-passwort>` (read-only, täglicher Reset).
>
> ---
>
> ### Was OrbVis (heute) **nicht** ist
>
> - Kein offizielles Checkmk-Produkt. Community-getriebenes
>   GPL-2.0-Projekt.
> - Kein Drop-in-Ersatz, wenn ihr LDAP, Audit-Logs oder Custom-PHP-
>   Gadgets braucht (siehe oben).
> - Kein Wegwerf-Skript: das Codebase ist getestet (~1500 Backend-
>   Tests, Pre-Commit mit Ruff/Mypy strict, CI mit pip-audit /
>   bandit / gitleaks). Aber die Versionsnummer ist `0.1.0` aus gutem
>   Grund — ich erwarte Feedback, das die ersten Iterationen
>   reichlich verändert.
>
> ---
>
> ### Wie ihr helfen könnt
>
> 1. **Probiert es auf einer Test-Site aus** und meldet, was nicht
>    funktioniert. Issues im Repo sind willkommen — Bug-Template
>    ist da.
> 2. **Migriert ein, zwei alte NagVis-Maps** und schreibt, was am
>    Importer hakt.
> 3. **Lest die [Roadmap](https://github.com/makanakoeln/orbvis/blob/main/ROADMAP.md)**
>    und kommentiert, ob die Prioritäten passen.
>
> Sicherheits-Reports bitte privat über das GitHub Security-Tab oder
> per E-Mail (siehe SECURITY.md), nicht in öffentlichen Issues.
>
> ---
>
> ### Langfristige Perspektive
>
> Mit Checkmk GmbH ist im Gespräch, OrbVis ab Checkmk 2.6 als
> **built-in Paket** auszuliefern — parallel zur weiterhin
> existierenden externen MKP-Linie. Dieser Schritt ist von
> CLA-/Code-Style-/Bazel-Klärungen abhängig und ist *nicht* Bestandteil
> dieses Beta-Releases. Wenn er kommt, behält die externe Variante
> ihre Daseinsberechtigung für CMK 2.3/2.4/2.5-Sites.
>
> ---
>
> Repo: <https://github.com/makanakoeln/orbvis>
> Issues / Feature-Requests: <https://github.com/makanakoeln/orbvis/issues>
> Lizenz: GPL-2.0-only
>
> Danke fürs Lesen — und besonders denen, die direkt mal eine MKP
> draufpacken und Bugs einreichen.
>
> *<Name / Handle>*

---

## Checkliste vor dem Posten

- [ ] Alle `<…>`-Platzhalter ersetzt (Demo-URL, Demo-Credentials, Name)
- [ ] Beide MKPs gebaut und auf das Forum / Releases hochgeladen
      (`make_mkp.sh --cmk-target 2.3` und `--cmk-target 2.5`)
- [ ] Demo-Site eingerichtet, getestet (read-only, täglicher Reset)
- [ ] 2-3 Bildschirm-Screenshots an Forum-Post angehängt
- [ ] Demo-Video / GIF aufgenommen (60-90 Sekunden Login → Board → Edit → Save)
- [ ] Repo öffentlich geschaltet (von privat → public)
- [ ] GitHub Discussions aktiviert (für Q&A)
- [ ] Erstes "Was läuft schon, was fehlt"-Issue als gepinnte
      Diskussion eröffnet — Sammelpunkt für Community-Feedback
- [ ] Mit Forum-Verantwortlichen abgestimmt: passende Forum-Kategorie,
      Tags, eventuelle Pinning-Bitte
- [ ] CHANGELOG aktualisiert ("0.1.0 — Public beta release")
- [ ] Release-Tag auf GitHub gesetzt, beide MKPs angehängt, NOTICE
      und SBOMs angehängt
