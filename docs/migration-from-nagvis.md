# Migrating from NagVis to OrbVis

OrbVis is a separate application — it does not share a database, user store,
or configuration with NagVis. The only crossover is the map definitions: the
home screen has an **Import Board** button that accepts NagVis `.cfg` files
directly and converts them on the fly. For bulk migrations there is also a
CLI helper (`tools/cfg_importer.py`) that produces OrbVis v2 board JSON from
the same `.cfg` input. Users, roles, backend connections and custom assets do
not transfer; OrbVis sets these up freshly via its own admin UI (or, in OMD
mode, via Checkmk).

## What gets converted

| NagVis concept                | OrbVis equivalent                                  |
| ----------------------------- | -------------------------------------------------- |
| `define global { … }`         | Board-level metadata (label, defaults)             |
| `define host { … }`           | Host object on the board                           |
| `define service { … }`        | Service object                                     |
| `define hostgroup { … }`      | Hostgroup object                                   |
| `define servicegroup { … }`   | Servicegroup object                                |
| `define line { … }`           | Line object (visual variant via `line_style`)      |
| `define textbox { … }`        | Textbox object                                     |
| `define shape { … }`          | Image object                                       |
| `define map { … }`            | Board-link object                                  |
| `iconset` (e.g. `std_medium`) | `icon_size` (24 px, etc.) — see `ICONSET_SIZE` map |
| `line_type` integer           | `line_style` shape + `line_perfdata_label` + `line_weather_color` |
| `line_label_in` / `line_label_out` | `weathermap_metric` / `weathermap_metric_out` |
| `line_width` integer          | `line_width` integer (default 3 in upstream)       |
| `gadget_url` (stock)          | `gadget_type` (gauge, bar) — known gadgets only    |

The `line_type` integer decomposes into three orthogonal OrbVis attributes:

| `line_type` | `line_style`    | `line_perfdata_label` | `line_weather_color` |
| ----------- | --------------- | --------------------- | -------------------- |
| `10`        | `arrow_inward`  | `none`                | `false`              |
| `11`        | `arrow_end`     | `none`                | `false`              |
| `12`        | `plain`         | `none`                | `false`              |
| `13`        | `arrow_inward`  | `percent`             | `true`               |
| `14`        | `arrow_inward`  | `both`                | `true`               |
| `15`        | `arrow_inward`  | `bandwidth`           | `true`               |

## What does **not** carry over automatically

- **Custom `gadget_url` values** that don't match a known stock gadget fall
  back to icon mode with a warning. Re-implementing custom gadgets is a
  manual job.
- **Backend connection definitions** — NagVis' `[backend_*]` sections are
  not converted. Configure backends in OrbVis via *Admin → Backends*
  (or `backends.json`).
- **Custom CSS / templates** — OrbVis uses Vue components, not PHP
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

### 2. Import via the OrbVis home screen (recommended)

1. Open OrbVis and sign in with an account that has board-create rights.
2. On the home screen, click **Import Board**.
3. Pick a `.cfg` file. OrbVis converts it server-side, validates the
   result, and the new board shows up on the home screen immediately.
4. If a board with the same name already exists, OrbVis asks before
   overwriting.

This is the only step needed for most maps — repeat it per file, or use
the CLI below for batch jobs.

### 3. Bulk convert via CLI (optional)

For dozens or hundreds of maps in one go:

```bash
python tools/cfg_importer.py --batch \
    /opt/omd/sites/<site>/etc/nagvis/maps/ \
    ./out/
```

Each `.cfg` becomes a `.json` with the same basename. Drop the resulting
files into the boards directory:

- **OMD MKP:** `$OMD_ROOT/var/orbvis/boards/`
- **Standalone:** `<install-dir>/boards/`
- **Dev:** `backend/boards/`

OrbVis hot-reloads board JSON, so the boards appear without a restart.
A single map can also be converted with
`python tools/cfg_importer.py path/to/map.cfg ./out/`.

### 4. Copy backgrounds (optional)

NagVis stores map backgrounds under `etc/nagvis/maps/...` or
`share/nagvis/htdocs/userfiles/images/maps/`. Copy the ones you need to:

- **OMD MKP install:** `$OMD_ROOT/var/orbvis/boards/backgrounds/`
- **Standalone install:** `<install-dir>/boards/backgrounds/`

The board JSON references them by filename only.

### 5. Review and tidy

Open each board in OrbVis edit mode and check:

- Object positions (NagVis uses pixel coordinates from a different
  canvas system; positions usually carry over but verify edge cases)
- Hover / context-menu templates (NagVis defaults vs. OrbVis defaults
  may differ for non-standard fields)
- URL fields and click actions
- Lines that used custom `line_weather_colors` thresholds — OrbVis applies
  its default utilization-gradient colours instead

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
