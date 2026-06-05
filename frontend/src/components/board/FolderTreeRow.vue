<template>
  <div
    class="ft-row"
    :class="{
      'ft-row--folder': node.kind === 'folder',
      'ft-row--clickable': node.kind !== 'folder'
    }"
    role="treeitem"
    :aria-level="depth + 1"
    :aria-expanded="isExpandable ? isOpen : undefined"
    :title="node.output || undefined"
    @click="onRowClick"
    @contextmenu="onCtx"
    @mousemove="onHover"
    @mouseleave="$emit('hover-clear')"
  >
    <!-- One vertical guide per ancestor level so the nesting depth (e.g.
             a host directly under Main vs. inside a subfolder) is unambiguous. -->
    <span v-for="i in depth" :key="i" class="ft-guide" />
    <!-- Any expandable node (folder, or host when services are shown) gets a
             chevron so the drill-down is discoverable; leaves get a spacer. -->
    <button
      v-if="isExpandable"
      type="button"
      class="ft-chevron"
      :aria-label="isOpen ? t('board.ftCollapse') : t('board.ftExpand')"
      @click.stop="onChevron"
    >
      {{ isOpen ? '▾' : '▸' }}
    </button>
    <span v-else class="ft-chevron ft-chevron--spacer" />

    <!-- Theme-aware folder glyph (Tabler-style) instead of an OS-dependent emoji. -->
    <svg
      v-if="node.kind === 'folder'"
      class="ft-icon"
      :class="{ 'ft-icon--empty': isEmpty }"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path
        v-if="isOpen"
        d="M5 19l2.757-7.351A1 1 0 0 1 8.694 11H21l-2.757 7.351A1 1 0 0 1 17.306 19zM3 19V6a1 1 0 0 1 1-1h5l3 3h6a1 1 0 0 1 1 1v2"
      />
      <path v-else d="M3 6a1 1 0 0 1 1-1h5l3 3h8a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" />
    </svg>
    <!-- Host glyph; also acts as an expand toggle when drillable (the chevron
             is the primary affordance). -->
    <svg
      v-else-if="node.kind === 'host'"
      class="ft-icon ft-host-icon"
      :class="{
        'ft-host-icon--toggle': isExpandable,
        'ft-host-icon--open': isExpandable && isOpen
      }"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      :role="isExpandable ? 'button' : undefined"
      :aria-label="
        isExpandable ? (isOpen ? t('board.ftCollapse') : t('board.ftExpand')) : undefined
      "
      @click="onHostIconClick"
    >
      <rect x="3" y="4" width="18" height="13" rx="1" />
      <path d="M7 21h10M9 17v4M15 17v4" />
    </svg>
    <span
      v-if="!isEmpty && !(node.kind === 'folder' && pills.length)"
      class="ft-dot"
      :style="{ background: stateColorVar(node.state) }"
      :title="node.state"
    />

    <span
      class="ft-title"
      :class="{ 'ft-title--empty': isEmpty, 'ft-title--svc': node.kind === 'service' }"
      >{{ node.title }}</span
    >

    <!-- Stays next to the name; a right-aligned count drifts away on wide screens. -->
    <span v-if="isEmpty" class="ft-badge ft-badge--empty">{{ t('board.ftEmptyHosts') }}</span>
    <span v-else-if="node.kind === 'folder'" class="ft-meta"
      >{{ node.host_count }} {{ t('board.ftHosts')
      }}<template v-if="pills.length && folderOk > 0"> · {{ folderOk }} OK</template></span
    >
    <span v-if="node.kind === 'folder' && pills.length" class="ft-pills">
      <span
        v-for="p in pills"
        :key="p.state"
        class="ft-pill"
        :style="{ background: p.bg, color: p.fg }"
        :title="`${p.count} ${p.state}`"
        >{{ p.count }}</span
      >
    </span>

    <span class="ft-rowfill" />

    <span v-if="node.kind === 'host' && multiSite && node.site_id" class="ft-site">{{
      node.site_id
    }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { FolderTreeNode } from '@/types/api'
import { severityPills, stateColorVar } from '@/utils/stateColors'

// Presentational single row: the tree is flattened to a virtualized list in
// FolderTreeBoard, so this component no longer recurses — open/expandable state
// and depth are precomputed by the projection and passed in.
const props = defineProps<{
  node: FolderTreeNode
  // markRaw node fields are patched in place; a changed rev re-renders the row
  // (and re-derives the computeds below) so live status shows without navigation.
  rev: number
  depth: number
  isOpen: boolean
  isExpandable: boolean
  multiSite: boolean
  // Owning host for a service row, so a click can resolve it for the drawer.
  hostName?: string
}>()

const emit = defineEmits<{
  toggle: [string]
  'expand-host': [FolderTreeNode]
  'select-host': [FolderTreeNode]
  'select-service': [string, FolderTreeNode]
  'hover-host': [FolderTreeNode, number, number]
  'hover-service': [string, FolderTreeNode, number, number]
  'hover-clear': []
  'ctx-folder': [FolderTreeNode, number, number]
}>()

const { t } = useI18n()

const isEmpty = computed(() => {
  void props.rev
  return props.node.kind === 'folder' && props.node.is_empty
})
const pills = computed(() => {
  void props.rev
  return severityPills(props.node.severity_counts)
})
// Healthy remainder so the pill breakdown sums to the host count.
const folderOk = computed(() => {
  void props.rev
  return Math.max(0, props.node.host_count - props.node.problem_count)
})

function onChevron() {
  emit('toggle', props.node.path)
  if (props.node.kind === 'host') emit('expand-host', props.node)
}

// The host icon is the expand toggle when the host can drill into services;
// otherwise let the click bubble to the row so it opens the drawer.
function onHostIconClick(e: MouseEvent) {
  if (props.node.kind === 'host' && props.isExpandable) {
    e.stopPropagation()
    onChevron()
  }
}

function onRowClick() {
  if (props.node.kind === 'host') emit('select-host', props.node)
  else if (props.node.kind === 'service') emit('select-service', props.hostName ?? '', props.node)
  else emit('toggle', props.node.path)
}

// Cursor-anchored (rows are full-width, so a row-rect anchor would overflow and
// flip the menu over the navigation).
function onHover(e: MouseEvent) {
  if (props.node.kind === 'host') emit('hover-host', props.node, e.clientX, e.clientY)
  else if (props.node.kind === 'service')
    emit('hover-service', props.hostName ?? '', props.node, e.clientX, e.clientY)
}

// Folders only; host/service rows keep the native menu.
function onCtx(e: MouseEvent) {
  if (props.node.kind !== 'folder') return
  e.preventDefault()
  emit('ctx-folder', props.node, e.clientX, e.clientY)
}
</script>

<style scoped>
.ft-row {
  display: flex;
  align-items: center;
  gap: 7px;

  /* Must match the windowing ROW_H in FolderTreeBoard; driven by its --ft-row-h. */
  height: var(--ft-row-h, 28px);
  padding-left: 6px;
  font-size: 13px;
  color: var(--text);
  border-radius: 4px;
  user-select: none;
}

/* One per ancestor level: an 18px column with a left guide line. The negative
   margin cancels the row's 7px flex gap so columns stay tight (18px each). */
.ft-guide {
  width: 18px;
  flex-shrink: 0;
  align-self: stretch;
  margin-right: -7px;
  border-left: 1px solid var(--border);
}

.ft-row--clickable {
  cursor: pointer;
}

.ft-row--folder {
  cursor: pointer;
  font-weight: 500;
}

.ft-row:hover {
  background: var(--bg-hover);
}

.ft-chevron {
  width: 16px;
  flex-shrink: 0;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 11px;
  padding: 0;
}

.ft-chevron--spacer {
  cursor: default;
}

.ft-icon {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  color: var(--text-muted);
}

.ft-icon--empty {
  opacity: 0.45;
}

/* Host icon doubles as the services expand-toggle when drillable. */
.ft-host-icon--toggle {
  cursor: pointer;
}

.ft-host-icon--toggle:hover {
  color: var(--text);
}

.ft-host-icon--open {
  color: var(--accent);
}

.ft-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 1px var(--border);
}

.ft-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
}

/* Service name can now use the full row width (the plugin-output column moved
   to the hover menu); still ellipsizes when very long. */
.ft-title--svc {
  font-weight: 400;
  flex-shrink: 1;
}

.ft-title--empty {
  color: var(--text-muted);
  font-style: italic;
  font-weight: 400;
}

/* Fills the row so the trailing host-only site badge right-aligns. */
.ft-rowfill {
  flex: 1;
  min-width: 0;
}

.ft-meta {
  color: var(--text-muted);
  font-size: 11px;
}

.ft-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 9px;
  flex-shrink: 0;
}

.ft-badge--empty {
  color: var(--text-muted);
  border: 1px dashed var(--border);
}

.ft-pills {
  display: inline-flex;
  gap: 3px;
  flex-shrink: 0;
}

.ft-pill {
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  padding: 2px 6px;
  border-radius: 9px;
  min-width: 16px;
  text-align: center;
}

.ft-site {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--bg-hover);
  color: var(--text-muted);
  border: 1px solid var(--border);
  flex-shrink: 0;
}
</style>
