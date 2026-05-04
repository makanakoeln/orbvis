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
> ersten MKPs. Ziel des Posts: Feedback einsammeln, Mit-Tester finden.
> Entwickelt und getestet primär auf Ubuntu 24.04, unterstützt werden
> sollen aber alle von Checkmk unterstützten Plattformen.
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
> Es gibt vier MKPs — eines pro CMK-Major (2.3, 2.4, 2.5, 2.6):
>
> ```bash
> omd su <site>
> mkp add ~/orbvis-cmk-2.5.mkp     # passend für CMK 2.5
> # oder: ~/orbvis-cmk-2.6.mkp     # CMK 2.6 (beta)
> # oder: ~/orbvis-cmk-2.4.mkp     # CMK 2.4
> # oder: ~/orbvis-cmk-2.3.mkp     # CMK 2.3
> mkp enable orbvis
> orbvis-setup
> ```
>
> Danach erreichbar als **OrbVis**-Eintrag im Checkmk-Hauptmenü
> (zusätzlich auch unter `https://<host>/<site>/orbvis/`).
> Authentifizierung via Checkmk-Session — kein eigenes OrbVis-Passwort.
>
> Detail-Doku: [docs/install.md](https://github.com/makanakoeln/orbvis/blob/main/docs/install.md).
>
> ---
>
> ### Live-Demo
>
> Eine OrbVis-Instanz läuft öffentlich auf
> <https://play.checkmk.com> — kein Login nötig, Boards sind read-only
> einsehbar, Konfiguration ist gesperrt. Reicht zum Reinschauen ohne
> selbst etwas installieren zu müssen.
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
>
> Sicherheits-Reports bitte privat über das GitHub Security-Tab oder
> per E-Mail (siehe SECURITY.md), nicht in öffentlichen Issues.
>
> ---
>
> ### Langfristige Perspektive
>
> Die Entwicklung geht in Richtung built-in Checkmk-Paket — parallel
> zur weiterhin existierenden externen MKP-Linie. Konkrete Termine
> dazu gibt es noch nicht.
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
> *Ronny / @makanakoeln*

---

## Checkliste vor dem Posten

- [ ] Screenshot-Platzhalter `<screenshot-url-1>` / `<screenshot-url-2>`
      durch echte Bild-URLs aus dem Forum-Editor ersetzt (Drag & Drop
      zweier `docs/screenshots/*.png`-Dateien direkt in das Forum-
      Eingabefeld)
- [ ] Alle vier MKPs gebaut und auf das Forum / Releases hochgeladen
      (`make_mkp.sh --cmk-target 2.3`, `--cmk-target 2.4`, `--cmk-target 2.5`,
      `--cmk-target 2.6`)
- [ ] Demo-Site eingerichtet, getestet (read-only, täglicher Reset)
- [ ] 2-3 Bildschirm-Screenshots an Forum-Post angehängt
- [ ] Demo-Video / GIF aufgenommen (60-90 Sekunden Login → Board → Edit → Save)
- [ ] Repo öffentlich geschaltet (von privat → public)
- [ ] GitHub Discussions aktiviert (für Q&A)
- [ ] Erstes "Was läuft schon, was fehlt"-Issue als gepinnte
      Diskussion eröffnet — Sammelpunkt für Community-Feedback
- [ ] Mit Forum-Verantwortlichen abgestimmt: passende Forum-Kategorie,
      Tags, eventuelle Pinning-Bitte
- [ ] CHANGELOG aktualisiert ("0.1.0 — initial release")
- [ ] Release-Tag auf GitHub gesetzt, beide MKPs angehängt, NOTICE
      und SBOMs angehängt
