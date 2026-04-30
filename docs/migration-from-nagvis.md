# Migrating from NagVis to OrbVis

OrbVis ships a converter (`tools/cfg_importer.py`) that reads legacy NagVis
`.cfg` map files and writes OrbVis v2 board JSON.

## What gets converted

| NagVis concept                | OrbVis equivalent                                  |
| ----------------------------- | -------------------------------------------------- |
| `define global { … }`         | Board-level metadata (label, defaults)             |
| `define host { … }`           | Host object on the board                           |
| `define service { … }`        | Service object                                     |
| `define hostgroup { … }`      | Hostgroup object                                   |
| `define servicegroup { … }`   | Servicegroup object                                |
| `define line { … }`           | Line / weathermap line                             |
| `define textbox { … }`        | Textbox object                                     |
| `define shape { … }`          | Image object                                       |
| `define map { … }`            | Board-link object                                  |
| `iconset` (e.g. `std_medium`) | `icon_size` (24 px, etc.) — see `ICONSET_SIZE` map |
| `line_type` integer           | `line_style` string (plain, arrow_end, weathermap) |
| `gadget_url` (stock)          | `gadget_type` (gauge, bar) — known gadgets only    |

## What does **not** carry over automatically

- **Custom `gadget_url` values** that don't match a known stock gadget fall
  back to icon mode with a warning. Re-implementing custom gadgets is a
  manual job.
- **Backend connection definitions** — NagVis' `[backend_*]` sections are
  not converted. Configure backends in OrbVis via *Admin → Backends*
  (or `backends.json`).
- **User accounts / permissions** — re-create users and roles in OrbVis;
  the NagVis `auth.db` SQLite file is not imported.
- **Custom CSS / templates** — OrbVis uses Vue + Tailwind, not PHP
  templates. Visual customisation goes through board settings and the
  hover/context menu template fields.

## Step-by-step

### 1. Locate your NagVis maps

On a Checkmk site running NagVis:

```bash
ls $OMD_ROOT/etc/nagvis/maps/
# → demo.cfg, datacenter.cfg, network.cfg, …
```

Standalone NagVis: typically `/usr/local/nagvis/etc/maps/`.

### 2. Convert a single map

```bash
cd /path/to/orbvis
python tools/cfg_importer.py \
    /opt/omd/sites/<site>/etc/nagvis/maps/datacenter.cfg \
    ./out/
```

Output: `./out/datacenter.json` plus a console summary of the objects
created and any warnings (unknown gadget URLs, unmapped iconsets, etc.).

### 3. Batch-convert a whole maps directory

```bash
python tools/cfg_importer.py --batch \
    /opt/omd/sites/<site>/etc/nagvis/maps/ \
    ./out/
```

Each `.cfg` becomes a `.json` with the same basename.

### 4. Copy backgrounds (optional)

NagVis stores map backgrounds under `etc/nagvis/maps/...` or
`share/nagvis/htdocs/userfiles/images/maps/`. Copy the ones you need to:

- **OMD MKP install:** `$OMD_ROOT/local/share/orbvis/boards/backgrounds/`
- **Standalone install:** `<install-dir>/boards/backgrounds/`

The board JSON references them by filename only.

### 5. Drop the JSON into the OrbVis boards directory

- **OMD MKP:** `$OMD_ROOT/local/share/orbvis/boards/datacenter.json`
- **Standalone:** `<install-dir>/boards/datacenter.json`
- **Dev:** `backend/boards/datacenter.json`

Reload OrbVis (`omd restart orbvis` / `systemctl restart orbvis`) — the
new boards appear on the home screen immediately.

### 6. Review and tidy

Open each board in OrbVis edit mode and check:

- Object positions (NagVis uses pixel coordinates from a different
  canvas system; positions usually carry over but verify edge cases)
- Hover / context-menu templates (NagVis defaults vs. OrbVis defaults
  may differ for non-standard fields)
- URL fields and click actions
- Lines that used custom weathermap thresholds

## Recommended migration order

1. Start with one or two boards to validate the workflow on your data.
2. Convert the rest in batch.
3. Run OrbVis side-by-side with NagVis for a week or two so you can spot
   any state-display discrepancies before retiring NagVis.
4. Remove NagVis only after you're satisfied OrbVis covers every active
   board.

## Reporting issues

If you find a NagVis feature that the importer misses, please open a
[GitHub issue](https://github.com/makanakoeln/orbvis/issues) with:

- The smallest possible `.cfg` snippet that triggers the problem
- The actual JSON the importer produced
- What you expected to see in OrbVis

NagVis-feature parity is one of OrbVis' top priorities — concrete
examples help us close gaps quickly.
