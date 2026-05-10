# BI Aggregation Objects — UX Review

Status: review (May 2026), gaps found before first GA shipping of BI support.

## Scope

OrbVis renders Checkmk BI aggregations as a board-object type (`aggregation`).
Three surfaces matter to the operator:

1. **Board canvas** — the icon, badge stack, optional expanded subtree
   (`expand_depth > 0`) — `BoardObject.vue`, `AggregationSubtree.vue`.
2. **Edit panel** — `aggregation_id` autocomplete, expand-depth, labels —
   `EditPanel.vue`, `ObjectPropertiesModal.vue`.
3. **Detail drawer** — what the operator sees when they click the
   aggregation glyph — `DetailDrawer.vue`.

The 6.14 spec in `30-board-objects.spec.ts` is currently `test.skip`'d
("only single-host BIs available"); this review documents what to fix
**before** that skip can be removed and BI is actually testable.

## Designer view (board layout, hover, edit)

### What works

- Custom **tree glyph** root icon (`BoardObject.vue:316`) makes BI
  visually distinct from host/service objects.
- **Expanded subtree** (`AggregationSubtree.vue`) shows children as
  state-coloured circles with downtime/ack badges. Visual language
  matches the canvas elsewhere.
- **Autocomplete** in EditPanel picks aggregation IDs from the configured
  CMK connection (`addAggregationIds`).

### Gaps

1. **No BI-tree preview during configuration.** `expand_depth` is a bare
   numeric input — the designer has no idea whether `2` is enough or
   whether the tree fans out into 200 leaves. *Proposal:* live preview
   pane next to the input that re-computes `tree` and shows a sample
   layout when the value changes.
2. **Branch-pruning is invisible.** `exclude_members` /
   `exclude_member_states` exist as schema fields but the EditPanel
   doesn't expose them. *Proposal:* an "Advanced" disclosure with
   regex-validated text inputs and a count badge ("12 leaves
   suppressed") computed against the live aggregation.
3. **Worst-state vs best-state semantics.** OrbVis bubbles up the worst
   child state (BIStates) — that's correct for "show me problems" but
   the designer can't tell from the UI which aggregation function is in
   use upstream (worst, best, count_ok, …). *Proposal:* read-only chip
   below `aggregation_id` showing the CMK aggregation function so the
   designer doesn't have to crosscheck WATO.
4. **No glyph-density warning.** Auto-expanded subtrees on a worldmap
   board with hundreds of aggregations clutter the canvas. *Proposal:*
   warning banner when the rendered node count > 50, with a link to
   "switch to drawer-only" mode.

## Operator view (hover, drawer, actions)

### What works

- Subtree node hover surfaces the per-node state (color + tooltip).
- Click on a subtree node opens DetailDrawer scoped to that leaf
  (host or service).

### Gaps

1. **No aggregation-level summary in the drawer.** Clicking the
   aggregation root opens an empty-ish drawer because DetailDrawer
   special-cases host/service/group, not `aggregation`. *Proposal:*
   add an "Aggregation summary" pane with: function name, node count
   (OK / WARN / CRIT / UNKNOWN), worst child path, last_state_change
   of the root, and a list of leaf hosts/services with
   click-to-drill-down.
2. **No "what changed" view.** When an aggregation flips from OK →
   CRIT, the operator's first question is "which subtree branch caused
   it?" — currently they need to click each leaf individually.
   *Proposal:* highlight the path from root to the worst leaf in the
   subtree visualisation (bolder line, brief animation on state
   transitions).
3. **Acknowledge/downtime semantics undefined.** The DetailDrawer's
   ack/downtime/force-check buttons act on a *single* host or service.
   For an aggregation the operator usually wants "acknowledge all
   currently-problematic leaves" — there is no such bulk action today.
   *Proposal:* a "Bulk-acknowledge contributing leaves" button that
   walks `tree` and POSTs ack to every node whose state ≥ WARN, with a
   confirmation modal listing the targets.
4. **Stale-data marker missing.** If livestatus to a federated site is
   dead, the aggregation's leaves get stale states but the tree still
   renders as if fresh. *Proposal:* dashed circle (matching the
   Connection-down indicator elsewhere) plus a "Some children
   unreachable — last update Xs ago" line in the drawer.
5. **No drill-through to WATO BI editor.** Operators often need to
   adjust the aggregation rules. *Proposal:* "Open in Checkmk WATO BI
   editor" link in the drawer header (deep-link to
   `wato.py?mode=bi_edit_aggregation&id=<aggregation_id>`).

## Test plan once gaps are filled

The skipped 6.14 spec (`30-board-objects.spec.ts:325`) should be
de-skipped and extended to:

- 6.14a: place an `aggregation` object via the EditPanel using
  autocomplete; assert the live aggregation tree renders with at least
  one leaf.
- 6.14b: change `expand_depth` from 0 to 2 and back; assert the subtree
  appears/disappears.
- 6.14c: click a problematic subtree leaf → drawer opens scoped to
  that leaf with ack/downtime buttons.
- 6.14d: click the aggregation root → drawer shows the new
  "Aggregation summary" pane with the right counts.
- 6.14e: bulk-acknowledge action → all WARN/CRIT leaves return
  `acknowledged=true` via livestatus within 30 s.

Fixtures: a CMK BI aggregation referencing more than one host (the
default sample shipped with `omd create` is single-host only). The
release-test orchestrator can post a multi-host aggregation via the BI
REST API in setup; tracked separately.
