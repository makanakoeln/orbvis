<template>
  <div class="orb-flow">
    <div v-if="loading" class="orb-flow__center">
      <CmkLoading />
    </div>
    <div v-else-if="error" class="orb-flow__center orb-flow__center--error">
      {{ error }}
    </div>
    <svg v-else ref="svgEl" class="orb-flow__svg" />

    <!-- Zoom controls -->
    <div v-if="!loading && !error && !preview" class="orb-flow__zoom">
      <button title="Zoom in" class="orb-flow__zoom-btn" @click="zoomIn">
        <svg
          style="width: 14px; height: 14px"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
      </button>
      <button title="Fit all" class="orb-flow__zoom-btn" @click="fitView()">
        <svg
          style="width: 14px; height: 14px"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
          />
        </svg>
      </button>
      <button title="Zoom out" class="orb-flow__zoom-btn orb-flow__zoom-btn--last" @click="zoomOut">
        <svg
          style="width: 14px; height: 14px"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 12h-15" />
        </svg>
      </button>
    </div>

    <BoardSearch
      v-if="!loading && !error && !detailObject && !preview"
      v-model="filterText"
      :exclude-prefixes="['hg', 'sg']"
    >
      <template #trailing>
        <ProblemsOnlyToggle
          :model-value="problemsOnly ?? false"
          :title="_t('Show only hosts with problems')"
          @update:model-value="emit('update:problemsOnly', $event)"
        />
      </template>
    </BoardSearch>

    <div
      v-if="topKBreakdown.omitted > 0 && needsServiceDetail && (preview || !topKHintDismissed)"
      class="flow-hint flow-hint--topk"
    >
      <span>{{
        preview
          ? _t('Services shown for %{shown} of %{total} hosts', topKBreakdown)
          : _t(
              'Showing service detail for the top %{shown} of %{total} most affected hosts — others are aggregated as donuts',
              topKBreakdown
            )
      }}</span>
      <button
        v-if="!preview"
        type="button"
        class="flow-hint__dismiss"
        :title="_t('Dismiss this hint')"
        :aria-label="_t('Dismiss this hint')"
        @click="dismissTopKHint"
      >
        ×
      </button>
    </div>

    <!-- Hover popup -->
    <HoverMenu
      v-if="hoverMenu.visible && hoverMenu.object"
      :object="hoverMenu.object"
      :state="hoverState"
      :x="hoverMenu.x"
      :y="hoverMenu.y"
      :connection-id="props.connectionId"
      :checkmk-url="props.checkmkUrl ?? null"
      :template="resolveTemplate(null, props.hoverTemplate, settingsStore.settings.hover_template)"
      @card-enter="hoverGrace.cancelClose()"
      @card-leave="hoverGrace.scheduleClose()"
    />

    <DetailDrawer
      :object="detailObject"
      v-bind="detailStateProps"
      :checkmk-url="props.checkmkUrl ?? null"
      :connection-id="props.connectionId ?? null"
      :selectable-hosts="flowSelectableHosts"
      :readonly="props.readonly ?? false"
      portal-target="#orbvis-board-shell"
      @close="closeDetail"
      @acknowledge="onDetailAck"
      @remove-ack="onDetailRemoveAck"
      @schedule-downtime="onDetailDowntime"
      @remove-downtime="onDetailRemoveDowntime"
      @force-check="onDetailForceCheck"
      @add-comment="onDetailAddComment"
      @enable-notifications="onDetailToggleNotifications(true)"
      @disable-notifications="onDetailToggleNotifications(false)"
      @select-host="onSelectFlowHost"
    />

    <div v-if="selectedIds.size > 0" class="bulk-actions">
      <span class="bulk-actions__count">
        {{ _t('%{count} selected', { count: selectedIds.size }) }}
      </span>
      <button
        type="button"
        class="bulk-actions__btn"
        @click="bulkAction(objectActions.handlers.acknowledge)"
      >
        {{ _t('Acknowledge…') }}
      </button>
      <button
        type="button"
        class="bulk-actions__btn"
        @click="bulkAction(objectActions.handlers.scheduleDowntime)"
      >
        {{ _t('Schedule downtime…') }}
      </button>
      <button
        type="button"
        class="bulk-actions__btn"
        @click="bulkAction(objectActions.handlers.forceCheck)"
      >
        {{ _t('Force check') }}
      </button>
      <button
        type="button"
        class="bulk-actions__btn bulk-actions__btn--clear"
        @click="clearSelection"
      >
        ×
      </button>
    </div>

    <!-- Context menu (right-click) -->
    <ContextMenu
      v-if="contextMenu.visible && contextMenu.object"
      :object="contextMenu.object"
      v-bind="contextMenuStateProps"
      :x="contextMenu.x"
      :y="contextMenu.y"
      :checkmk-url="props.checkmkUrl ?? null"
      :template="
        resolveTemplate(null, props.contextTemplate, settingsStore.settings.context_template)
      "
      @close="closeContextMenu"
      @acknowledge="onContextMenuAck"
      @remove-ack="onContextMenuRemoveAck"
      @schedule-downtime="onContextMenuDowntime"
      @remove-downtime="onContextMenuRemoveDowntime"
      @force-check="onContextMenuForceCheck"
      @add-comment="onContextMenuAddComment"
      @enable-notifications="onContextMenuToggleNotifications(true)"
      @disable-notifications="onContextMenuToggleNotifications(false)"
    />

    <BoardZoomResetPill
      :zoom="displayZoomK"
      :visible="manualZoomActive && !loading && !error"
      :offset="{ bottom: '98px', left: '16px' }"
      @reset="fitView()"
    />
  </div>

  <AckModal
    v-if="ackModalObject && props.checkmkUrl"
    :object="ackModalObject"
    :checkmk-url="props.checkmkUrl"
    @close="closeAckModal"
  />

  <CommentModal
    v-if="commentModalObject && props.checkmkUrl"
    :object="commentModalObject"
    :checkmk-url="props.checkmkUrl"
    @close="commentModalObject = null"
  />

  <DowntimeModal
    v-if="downtimeModalObject && props.checkmkUrl"
    :object="downtimeModalObject"
    :checkmk-url="props.checkmkUrl"
    @close="closeDowntimeModal"
  />

  <RemoveDowntimeModal
    v-if="removeDowntimeModal.visible && props.checkmkUrl"
    :downtimes="removeDowntimeModal.downtimes"
    :checkmk-url="props.checkmkUrl"
    :object-name="removeDowntimeModal.objectName"
    @close="closeRemoveDowntimeModal"
  />
</template>

<script setup lang="ts">
import {
  type SimulationNodeDatum,
  type ZoomTransform,
  drag,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  select,
  zoom,
  zoomIdentity
} from 'd3'
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'

import AckModal from '@/components/board/AckModal.vue'
import BoardSearch from '@/components/board/BoardSearch.vue'
import BoardZoomResetPill from '@/components/board/BoardZoomResetPill.vue'
import CommentModal from '@/components/board/CommentModal.vue'
import ContextMenu from '@/components/board/ContextMenu.vue'
import DetailDrawer from '@/components/board/DetailDrawer.vue'
import DowntimeModal from '@/components/board/DowntimeModal.vue'
import HoverMenu from '@/components/board/HoverMenu.vue'
import ProblemsOnlyToggle from '@/components/board/ProblemsOnlyToggle.vue'
import RemoveDowntimeModal from '@/components/board/RemoveDowntimeModal.vue'
import CmkLoading from '@/components/cmk/CmkLoading'

import { useD3Cleanup } from '@/composables/useD3Cleanup'
import { useFlowFilter } from '@/composables/useFlowFilter'
import {
  type CmdMarker,
  type FLink,
  type FNode,
  useFlowNodeModel
} from '@/composables/useFlowNodeModel'
import { useFlowSelection } from '@/composables/useFlowSelection'
import { useHoverGrace } from '@/composables/useHoverGrace'
import { useObjectActions } from '@/composables/useObjectActions'
import { useTopKHint } from '@/composables/useTopKHint'
import { useTopologyFeed } from '@/composables/useTopologyFeed'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { useStatesStore } from '@/stores/states'
import type {
  BoardObject,
  ClickAction,
  FlowView,
  ObjectState,
  ServiceLayout,
  TopologyNode
} from '@/types/api'
import { buildCheckmkUrl, openUrl } from '@/utils/boardNavigation'
import {
  DONUT_MAX_WIDTH,
  type DonutArc,
  FAN_SPREAD,
  NODE_R,
  buildDonutArc,
  donutOuterRadius,
  donutPie,
  fanR,
  finiteOr,
  firstFinite,
  orbitR,
  problemScoreFromTopo,
  severityRank,
  showSvcLabel,
  svcR
} from '@/utils/flowGeometry'
import { stateColor } from '@/utils/stateColors'
import { resolveTemplate } from '@/utils/template'
import usei18n from '@/vendor/cmk/lib/i18n'

const props = defineProps<{
  connectionId: string
  serviceLayout: ServiceLayout
  readonly?: boolean
  clickAction?: ClickAction
  checkmkUrl?: string | null
  flowView?: FlowView | null
  preview?: boolean
  problemsOnly?: boolean
  hoverTemplate?: string | null
  contextTemplate?: string | null
}>()
const emit = defineEmits<{
  (e: 'update:serviceLayout', value: ServiceLayout): void
  (
    e: 'update:problems',
    value: { critical: number; warning: number; hostsWithProblems: number; total: number }
  ): void
  (e: 'drawer-object', value: BoardObject | null): void
  (e: 'positions-changed', value: Record<string, { x: number; y: number }>): void
  (e: 'update:problemsOnly', value: boolean): void
}>()
const { _t } = usei18n()
const auth = useAuthStore()
const statesStore = useStatesStore()
const settingsStore = useSettingsStore()

function layoutR(N: number): number {
  return props.serviceLayout === 'fan' ? fanR(N) : orbitR(N)
}

const MORE_NODE_MARKER = '__more__'

// Phyllotaxis (sunflower) layout: even-density spiral with no holes. Sorting
// by severity rank (desc) means hosts with the worst state get the inner
// slots, healthy hosts the outer. The combined effect is a compact disk
// whose center is dominated by problems and whose rim is mostly green —
// readable at a glance even on 500-host boards.
const PHYLLOTAXIS_ANGLE = Math.PI * (3 - Math.sqrt(5))
const SPIRAL_SPACING = 55
function rankBySeverity(hosts: FNode[]): FNode[] {
  return [...hosts].sort((a, b) => {
    const sa = severityRank(a.topo)
    const sb = severityRank(b.topo)
    if (sa !== sb) return sb - sa
    return a.id.localeCompare(b.id)
  })
}
function preLayoutHosts(hosts: FNode[]): void {
  if (!hosts.length) return
  rankBySeverity(hosts).forEach((d, i) => {
    const angle = i * PHYLLOTAXIS_ANGLE
    const r = SPIRAL_SPACING * Math.sqrt(i + 1)
    d.x = r * Math.cos(angle)
    d.y = r * Math.sin(angle)
  })
}
// Half-disk phyllotaxis below the site: mirror the negative-y points so the
// entire spiral lands in the lower half-plane. Hosts visually hang under
// their site root instead of orbiting around (0,0).
function preLayoutHostsBelowSite(
  sitePos: { x: number; y: number },
  hosts: FNode[],
  gap: number
): void {
  if (!hosts.length) return
  rankBySeverity(hosts).forEach((d, i) => {
    const angle = i * PHYLLOTAXIS_ANGLE
    const r = SPIRAL_SPACING * Math.sqrt(i + 1)
    d.x = sitePos.x + r * Math.cos(angle)
    d.y = sitePos.y + gap + Math.abs(r * Math.sin(angle))
  })
}

const TOP_K_LIMIT = 5
const TOP_K_THRESHOLD = 50
const topKWorstIds = computed<Set<string>>(() => {
  if (nodes.value.length < TOP_K_THRESHOLD) return new Set()
  const scored = nodes.value
    .map((n) => ({ id: n.name, score: problemScoreFromTopo(n) }))
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score)
  return new Set(scored.slice(0, TOP_K_LIMIT).map((s) => s.id))
})

const svgEl = ref<SVGSVGElement | null>(null)
useD3Cleanup(svgEl)

const { nodes, loading, error, fetchTopology } = useTopologyFeed({
  connectionId: () => props.connectionId,
  flowView: () => props.flowView,
  withServices: () => needsServices(props.serviceLayout)
})

const {
  worstServiceState,
  hostHalo,
  commandMarkers,
  badgeXY,
  donutSegments,
  boardObjectFromFNode,
  objectStateFromFNode
} = useFlowNodeModel({
  nodes: () => nodes.value,
  connectionId: () => props.connectionId,
  topKWorstIds: () => topKWorstIds.value
})

const hoverMenu = reactive<{
  visible: boolean
  object: BoardObject | null
  state: ObjectState | undefined
  x: number
  y: number
}>({ visible: false, object: null, state: undefined, x: 0, y: 0 })

// The hovered node, kept so the tooltip's state can be re-derived live. Reading
// topologyTimingVersion makes next-check/overdue tick in an open tooltip the
// same way the detail drawer does, instead of freezing at the hover moment.
const hoverFNode = ref<FNode | null>(null)

// Close-grace so the operator can move from a node onto the hover card and
// click a service-state pill (HoverMenu @card-enter/-leave round-trip).
const hoverGrace = useHoverGrace(() => {
  hoverMenu.visible = false
  hoverMenu.object = null
  hoverFNode.value = null
})
const hoverState = computed<ObjectState | undefined>(() => {
  const cur = hoverFNode.value
  if (!cur) return undefined
  void nodes.value
  void statesStore.topologyTimingVersion
  const fresh = lastFNodes.find((n) => n.id === cur.id) ?? cur
  return objectStateFromFNode(fresh)
})

const contextMenu = reactive<{
  visible: boolean
  object: BoardObject | null
  state: ObjectState | undefined
  x: number
  y: number
}>({ visible: false, object: null, state: undefined, x: 0, y: 0 })

// ContextMenu's `state?:` prop rejects an explicit `undefined` under
// exactOptionalPropertyTypes — spread the prop in only when a value exists.
const contextMenuStateProps = computed<{ state?: ObjectState }>(() =>
  contextMenu.state !== undefined ? { state: contextMenu.state } : {}
)

function closeContextMenu(): void {
  contextMenu.visible = false
  contextMenu.object = null
}

const {
  selectedIds,
  toggleSelection,
  clearSelection,
  attachLasso,
  applySelectionStyles,
  bulkAction
} = useFlowSelection({ svgEl, hostHalo, boardObjectFromFNode })

const detailObject = ref<BoardObject | null>(null)
const detailFNode = ref<FNode | null>(null)
// Recompute the drawer body whenever topology changes — otherwise a site
// drawer keeps showing the aggregate from the click moment, going stale on
// active boards.
const detailState = computed<ObjectState | undefined>(() => {
  const cur = detailFNode.value
  if (!cur) return undefined
  // Touch nodes.value so the computed re-runs on every topology push, and the
  // timing version so a check-timing-only patch (which mutates nodes in place
  // without replacing the array) refreshes the drawer's last/next-check too.
  void nodes.value
  void statesStore.topologyTimingVersion
  // Re-resolve the FNode by id from the latest render so a structural change
  // (state flip, ack/downtime) to the open node is reflected, not just timing;
  // a render replaces the node object the captured FNode pointed at.
  const fresh = lastFNodes.find((n) => n.id === cur.id) ?? cur
  return objectStateFromFNode(fresh)
})

// Same exactOptionalPropertyTypes dance as for the context menu above.
const detailStateProps = computed<{ state?: ObjectState }>(() =>
  detailState.value !== undefined ? { state: detailState.value } : {}
)

// The initial render schedules a refining fitView once the force-simulation
// settles. If the operator clicks a node before that fires, we'd animate the
// layout into a new transform mid-interaction — registered here, called from
// any interaction that should "claim" the current view.
let _cancelPendingFit: (() => void) | null = null
function cancelPendingFit(): void {
  if (_cancelPendingFit) {
    _cancelPendingFit()
    _cancelPendingFit = null
  }
}

function openDetail(obj: BoardObject, fNode: FNode): void {
  cancelPendingFit()
  detailObject.value = obj
  detailFNode.value = fNode
  closeContextMenu()
}

function closeDetail(): void {
  detailObject.value = null
  detailFNode.value = null
}

function onDetailAck(): void {
  objectActions.handlers.acknowledge(detailObject.value)
}
function onDetailRemoveAck(): void {
  objectActions.handlers.removeAck(detailObject.value)
}
function onDetailDowntime(): void {
  objectActions.handlers.scheduleDowntime(detailObject.value)
}
function onDetailRemoveDowntime(): void {
  objectActions.handlers.removeDowntime(detailObject.value)
}
function onDetailForceCheck(): void {
  objectActions.handlers.forceCheck(detailObject.value)
}
function onDetailAddComment(): void {
  objectActions.handlers.addComment(detailObject.value)
}
function onDetailToggleNotifications(enable: boolean): void {
  objectActions.handlers.toggleNotifications(detailObject.value, enable)
}

function onDocumentClick(): void {
  if (contextMenu.visible) closeContextMenu()
}

// Hostnames the Flow Board currently renders — Drawer-Topology entries that
// match these become click-to-jump buttons. Recomputes on every topology push.
const flowSelectableHosts = computed(() => nodes.value.map((n) => n.name))

function onSelectFlowHost(hostName: string): void {
  const node = nodes.value.find((n) => n.name === hostName)
  if (!node) return
  // Synthesize a BoardObject the Drawer can render — Flow Board nodes don't
  // come from boardConfig.objects, they live in the live topology snapshot.
  detailObject.value = {
    id: `flow-host-${hostName}`,
    type: 'host',
    x: 0,
    y: 0,
    host_name: hostName
  } as BoardObject
}

const objectActions = useObjectActions(() => props.checkmkUrl ?? null, closeContextMenu)
const { ackModalObject, downtimeModalObject, commentModalObject, removeDowntimeModal } =
  objectActions
const onContextMenuAck = () => objectActions.handlers.acknowledge(contextMenu.object)
const onContextMenuRemoveAck = () => objectActions.handlers.removeAck(contextMenu.object)
const onContextMenuDowntime = () => objectActions.handlers.scheduleDowntime(contextMenu.object)
const onContextMenuRemoveDowntime = () => objectActions.handlers.removeDowntime(contextMenu.object)
const onContextMenuAddComment = () => objectActions.handlers.addComment(contextMenu.object)
const onContextMenuForceCheck = () => objectActions.handlers.forceCheck(contextMenu.object)
const onContextMenuToggleNotifications = (enable: boolean) =>
  objectActions.handlers.toggleNotifications(contextMenu.object, enable)

// Layouts that need the full per-host service list. Donut renders only
// services_summary aggregates and therefore skips the bulk query entirely —
// that's the main scaling win for large installations.
function needsServices(layout: typeof props.serviceLayout): boolean {
  return layout === 'fan' || layout === 'orbit' || layout === 'row'
}

// Off-layout hides per-service health; aggregate problem counts to surface
// them in a click-to-fix CTA so a green-dot board doesn't mask CRIT/WARN.
// Total includes UNKNOWN (so unknown-only sites still trigger the banner)
// but the locale string only enumerates the more actionable CRIT/WARN.
const aggregatedProblems = computed(() => {
  let critical = 0
  let warning = 0
  let unknown = 0
  let hostsWithProblems = 0
  for (const n of nodes.value) {
    const s = n.services_summary
    if (!s) continue
    if (s.critical || s.warning || s.unknown) hostsWithProblems++
    critical += s.critical
    warning += s.warning
    unknown += s.unknown
  }
  return {
    critical,
    warning,
    hostsWithProblems,
    total: critical + warning + unknown
  }
})

watch(aggregatedProblems, (v) => emit('update:problems', v), { immediate: true })

// Lifted to BoardView so the parent can hide overlapping bottom-right controls
// and render a triage breadcrumb. Emits the actual object so the parent can
// label the breadcrumb without keeping a parallel state copy.
watch(detailObject, (v) => emit('drawer-object', v))

// Coalesce burst drags into a single save: dragging multiple hosts in
// succession or multi-select drags would otherwise hammer boards.update.
let _emitPinnedTimer: ReturnType<typeof setTimeout> | null = null
function emitPinnedPositions(): void {
  if (_emitPinnedTimer) clearTimeout(_emitPinnedTimer)
  _emitPinnedTimer = setTimeout(() => {
    const positions: Record<string, { x: number; y: number }> = {}
    for (const node of nodeCache.values()) {
      if (
        (node.nodeType === 'host' || node.nodeType === 'site') &&
        typeof node.fx === 'number' &&
        typeof node.fy === 'number' &&
        Number.isFinite(node.fx) &&
        Number.isFinite(node.fy)
      ) {
        positions[node.id] = { x: node.fx, y: node.fy }
      }
    }
    emit('positions-changed', positions)
  }, 400)
}
onUnmounted(() => {
  if (_emitPinnedTimer) clearTimeout(_emitPinnedTimer)
})

defineExpose({ closeDetail })

// Top-K cutoff visibility: when fan/orbit/row layouts are active and the
// backend omitted full service detail for some hosts, surface the ratio so
// operators understand why many hosts only show donut rings.
const topKBreakdown = computed(() => {
  const total = nodes.value.length
  let omitted = 0
  for (const n of nodes.value) if (n.services_omitted) omitted++
  return { total, shown: total - omitted, omitted }
})

const needsServiceDetail = computed(() => needsServices(props.serviceLayout))

const { topKHintDismissed, dismissTopKHint } = useTopKHint(() => auth.user?.user_id)

const { filterText, applyFilterOpacity } = useFlowFilter({
  svgEl,
  problemsOnly: () => props.problemsOnly,
  worstServiceState
})

// Re-fetch and clear service cache when serviceLayout prop changes. With WS
// the topology is pushed unconditionally with services, so the layout switch
// is a pure render-side concern; we still drop cached service positions so
// the new layout starts from scratch.
watch(
  () => props.serviceLayout,
  (newVal, oldVal) => {
    for (const k of nodeCache.keys()) {
      if (k.includes('::')) nodeCache.delete(k)
    }
    // Drop cached host positions for non-pinned hosts so preLayoutHosts
    // re-spreads them at spacing appropriate for the new layout. Without
    // this the donut-tight phyllotaxis carries over into fan/orbit/row
    // and the bigger service rings overlap neighbouring hosts once zoomed
    // in. User-dragged hosts (fx/fy set) keep their position.
    for (const node of nodeCache.values()) {
      if (node.nodeType !== 'host') continue
      if (node.fx !== undefined && node.fy !== undefined) continue
      node.x = undefined
      node.y = undefined
      node.vx = undefined
      node.vy = undefined
    }
    if (newVal !== 'off' && oldVal === 'off') {
      for (const node of nodeCache.values()) {
        node.x = undefined
        node.y = undefined
        node.vx = undefined
        node.vy = undefined
      }
    }
    _hasFitOnce = false
    if (!statesStore.wsAvailable) {
      fetchTopology()
    } else if (svgEl.value && nodes.value.length) {
      // Re-render immediately with the new layout. Without this the
      // user waits for the next WS topology push (up to ~15 s) before
      // anything changes on screen — feels broken.
      render(svgEl.value, nodes.value)
    }
  }
)

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
})

onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick)
  if (pendingZoomRaf !== null) {
    cancelAnimationFrame(pendingZoomRaf)
    pendingZoomRaf = null
    pendingZoomTransform = null
  }
  simulation?.stop()
  if (svgEl.value) select(svgEl.value).selectAll('*').remove()
})

// ---- D3 force types ----
let simulation: ReturnType<typeof forceSimulation<FNode>> | null = null
// Track last seen host id set so we can skip the (expensive) force-sim restart
// on status-only WebSocket updates. The fNode rebuild + visual attr updates
// still run, but without a sim restart there are no ticks → no DOM transform
// thrashing for hundreds of hosts on every push.
let _lastHostIds: Set<string> = new Set()
let zoomBeh: ReturnType<typeof zoom<SVGSVGElement, unknown>> | null = null
let lastFNodes: FNode[] = []
let _hasFitOnce = false

// rAF-coalesce state: high-frequency wheel/drag events (e.g. trackpads firing
// >60 Hz) would otherwise write the SVG transform multiple times per frame and
// re-trigger a layout cascade on each. We capture the latest transform and
// apply it once per animation frame instead.
let pendingZoomTransform: ZoomTransform | null = null
let pendingZoomRaf: number | null = null
let panActiveFlag = false
// F3 LoD: when zoomed out below this scale we hide service / "+more" nodes and
// their links — they're unreadable at that size and dominate the tick cost.
// At fit-to-view on multi-hundred-host boards the initial scale lands around
// 0.3–0.5, so 0.8 keeps the cheap host-only view active until the user zooms
// in deliberately.
const LOD_LOW_SCALE = 0.8
let lodLow = false
// `currentZoomK` is read from hot-path renderers (donut arc, host labels,
// site scale) per zoom frame; keeping it as a plain let avoids ref proxy
// overhead. `displayZoomK` is the reactive mirror consumed by the pill
// template only.
let currentZoomK = 1
const displayZoomK = ref(1)
const manualZoomActive = ref(false)

function refreshDonutWidths(): void {
  if (!svgEl.value) return
  const arc = buildDonutArc(currentZoomK)
  const sel = select(svgEl.value)
  sel.selectAll<SVGPathElement, DonutArc>('g.donut path').attr('d', (a) => arc(a) ?? '')
  refreshHostLabelOffsets()
  refreshSiteScale()
}

// Host labels sit just outside the donut ring. Donut outer radius depends on
// the current zoom (see donutOuterRadius), so the label y offset has to track
// that — otherwise at fit-zoom-out the wide donut overlaps the hostname text
// and at zoom-in the label sits unnecessarily far away.
function refreshHostLabelOffsets(): void {
  if (!svgEl.value) return
  const labelY = donutOuterRadius(currentZoomK) + 5
  select(svgEl.value)
    .selectAll<SVGTextElement, FNode>('g.node text.node-label')
    .filter((d) => d.nodeType === 'host')
    .attr('y', labelY)
}

// Site root box scales up at low zoom so the label stays legible. At fit-zoom
// (k≈0.25) the 110-px-wide rect would render as ~28px without this — too
// small to read. At full zoom the scale stays 1 (no inflation).
function siteScaleForZoom(zoomK: number): number {
  const inv = 1 / Math.max(finiteOr(zoomK, 1), 0.0001)
  return Math.min(3.5, Math.max(1, inv))
}
function refreshSiteScale(): void {
  if (!svgEl.value) return
  const scale = siteScaleForZoom(currentZoomK)
  select(svgEl.value)
    .selectAll<SVGGElement, FNode>('g.node')
    .filter((d) => d.nodeType === 'site')
    .attr('transform', (d) => `translate(${finiteOr(d.x)},${finiteOr(d.y)}) scale(${scale})`)
}

function applyLod(): void {
  if (!svgEl.value) return
  // Toggle a single class on the SVG root; the scoped CSS below hides
  // service / "+more" nodes and service-links via descendant selectors.
  // Inline-styling 3000+ elements per LoD flip stutters mid-zoom on
  // multi-hundred-host boards.
  svgEl.value.classList.toggle('lod-low', lodLow)
}

function flushZoomTransform(): void {
  pendingZoomRaf = null
  if (!pendingZoomTransform || !svgEl.value) return
  const t = pendingZoomTransform
  pendingZoomTransform = null
  // Refuse a corrupted transform rather than writing NaN into the DOM and
  // caching a NaN zoom level that would cascade into every label / site glyph.
  if (!Number.isFinite(t.k) || !Number.isFinite(t.x) || !Number.isFinite(t.y)) return
  select(svgEl.value).select<SVGGElement>('g.zoom-layer').attr('transform', t.toString())
  const newLow = t.k < LOD_LOW_SCALE
  if (newLow !== lodLow) {
    lodLow = newLow
    applyLod()
  }
  currentZoomK = t.k
  displayZoomK.value = t.k
  // Donut widths and host-label offsets are refreshed on zoom end, not per
  // frame — rebinding 500+ donut path d-attributes mid-zoom is the main
  // source of stutter on dense boards.
}

// Reset auto-fit when switching boards
watch(
  () => props.connectionId,
  () => {
    _hasFitOnce = false
    lodLow = false
  }
)

// Persisting positions creates a new flowView object reference each save.
// Vue's watch source returning an array would fire on every reference change
// (Object.is on the array), resetting _hasFitOnce and triggering a refit even
// when root/layers haven't actually changed. Compare the keys as a single
// string via computed so identical values are deduped before the watch sees
// them.
const flowViewKey = computed(() => {
  const v = props.flowView
  return `${v?.root ?? ''}|${v?.child_layers ?? ''}|${v?.parent_layers ?? ''}`
})
watch(flowViewKey, () => {
  nodeCache.clear()
  _hasFitOnce = false
  // Hide the previous root's nodes while the new topology arrives.
  loading.value = true
  fetchTopology()
})

// Stable node map — keeps d3 positions across topology refreshes
const nodeCache = new Map<string, FNode>()

// ---- BFS level (loose — for forceY only) ----
function bfsLevels(topoNodes: TopologyNode[]): Map<string, number> {
  const nameSet = new Set(topoNodes.map((n) => n.name))
  const levels = new Map<string, number>()
  const roots = topoNodes.filter(
    (n) => !n.parents.length || n.parents.every((p) => !nameSet.has(p))
  )
  const queue: string[] = roots.map((r) => r.name)
  roots.forEach((r) => levels.set(r.name, 0))
  while (queue.length) {
    const name = queue.shift()!
    const lvl = levels.get(name)!
    for (const n of topoNodes) {
      if (n.parents.includes(name) && !levels.has(n.name)) {
        levels.set(n.name, lvl + 1)
        queue.push(n.name)
      }
    }
  }
  topoNodes.filter((n) => !levels.has(n.name)).forEach((n) => levels.set(n.name, levels.size))
  return levels
}

// ---- Zoom controls ----
function fitView({ animated = true }: { animated?: boolean } = {}) {
  const svg = svgEl.value
  if (!svg || !zoomBeh || !lastFNodes.length) return
  manualZoomActive.value = false
  const W = svg.clientWidth || 900
  const H = svg.clientHeight || 600
  const PAD = 64
  // Fit only over nodes with a known position, kept as (x,y) pairs so a
  // still-settling node can't poison the extent or split it across axes.
  const pts = lastFNodes
    .map((n) => ({ x: firstFinite(n.x, n.fx), y: firstFinite(n.y, n.fy) }))
    .filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y))
  if (!pts.length) return
  const xs = pts.map((p) => p.x)
  const ys = pts.map((p) => p.y)
  const minX = Math.min(...xs) - NODE_R - PAD
  const maxX = Math.max(...xs) + NODE_R + PAD
  const minY = Math.min(...ys) - NODE_R - PAD
  const maxY = Math.max(...ys) + NODE_R + PAD
  const scale = Math.min(3, Math.max(0.15, Math.min(W / (maxX - minX), H / (maxY - minY))))
  const tx = W / 2 - scale * ((minX + maxX) / 2)
  const ty = H / 2 - scale * ((minY + maxY) / 2)
  if (!Number.isFinite(scale) || !Number.isFinite(tx) || !Number.isFinite(ty)) return
  const target = zoomIdentity.translate(tx, ty).scale(scale)
  const sel = select(svg)
  if (animated) {
    sel.transition().duration(400).call(zoomBeh.transform, target)
  } else {
    sel.call(zoomBeh.transform, target)
  }
}

function zoomIn() {
  if (!svgEl.value || !zoomBeh) return
  select(svgEl.value).transition().duration(200).call(zoomBeh.scaleBy, 1.4)
}

function zoomOut() {
  if (!svgEl.value || !zoomBeh) return
  select(svgEl.value)
    .transition()
    .duration(200)
    .call(zoomBeh.scaleBy, 1 / 1.4)
}

// ---- D3 rendering ----
watch(
  [nodes, svgEl],
  () => {
    const svg = svgEl.value
    if (!svg || !nodes.value.length) return
    render(svg, nodes.value)
  },
  { flush: 'post' }
)

function render(svg: SVGSVGElement, topoNodes: TopologyNode[]) {
  const el = select(svg)
  const W = svg.clientWidth || 900
  const H = svg.clientHeight || 600

  // --- Ensure static containers exist (created once) ---
  let gZoom = el.select<SVGGElement>('g.zoom-layer')
  if (gZoom.empty()) {
    // Top-K glow filter: a soft outer halo on the worst-state hosts so
    // they stand out at fit-zoom where stroke-width alone disappears.
    const defs = el.append('defs')
    const filter = defs
      .append('filter')
      .attr('id', 'top-k-glow')
      .attr('x', '-50%')
      .attr('y', '-50%')
      .attr('width', '200%')
      .attr('height', '200%')
    filter
      .append('feGaussianBlur')
      .attr('in', 'SourceGraphic')
      .attr('stdDeviation', 3)
      .attr('result', 'blur')
    const merge = filter.append('feMerge')
    merge.append('feMergeNode').attr('in', 'blur')
    merge.append('feMergeNode').attr('in', 'blur')
    merge.append('feMergeNode').attr('in', 'SourceGraphic')

    gZoom = el.append('g').attr('class', 'zoom-layer')
    gZoom.append('g').attr('class', 'links')
    gZoom.append('g').attr('class', 'nodes')
  }

  // --- Zoom behaviour (attached once) ---
  if (!(el.node() as SVGSVGElement & { __zoom_attached?: boolean }).__zoom_attached) {
    ;(el.node() as SVGSVGElement & { __zoom_attached?: boolean }).__zoom_attached = true
    zoomBeh = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.15, 3])
      // d3's default wheelDelta applies a x10 multiplier when ctrlKey is
      // set (so trackpad pinch-zoom matches), but on a mouse wheel that
      // makes ctrl+wheel feel like an order of magnitude bigger jump per
      // tick than a bare wheel. Drop the multiplier so both gestures use
      // the same per-tick step.
      .wheelDelta(
        (event) => -event.deltaY * (event.deltaMode === 1 ? 0.05 : event.deltaMode ? 1 : 0.002)
      )
      // Shift+drag is reserved for lasso multi-select; let the lasso
      // listener handle those events instead of panning.
      .filter((event) => {
        if (event.type === 'mousedown' && event.shiftKey) return false
        return !event.button || event.button === 0
      })
      // Freeze the force simulation while the user actively pans/zooms,
      // resume it on release if it still had energy left. Otherwise tick
      // handlers run alongside transform updates and the combined
      // per-frame work blows past the 16 ms budget on Fan.
      .on('start.simfreeze', () => {
        cancelPendingFit()
        simulation?.stop()
      })
      .on('end.simfreeze', () => {
        if (panActiveFlag && svgEl.value) {
          svgEl.value.classList.remove('pan-active')
          panActiveFlag = false
        }
        if (simulation && simulation.alpha() > simulation.alphaMin()) {
          simulation.restart()
        }
      })
      .on('end.refresh-donut', () => {
        // Reapply donut widths and host-label offsets once after the
        // zoom gesture finishes; doing it per-frame stutters at scale.
        refreshDonutWidths()
      })
      .on('zoom', (event) => {
        pendingZoomTransform = event.transform
        if (pendingZoomRaf === null) {
          pendingZoomRaf = requestAnimationFrame(flushZoomTransform)
        }
        // sourceEvent is null when the transform was issued
        // programmatically (e.g. fitView). Only flag manual zoom for
        // real user gestures so the pill stays hidden right after a
        // fit-to-view.
        if (event.sourceEvent) manualZoomActive.value = true
        // Defer pan-active until an actual transform change (rather
        // than mousedown) so a bare click on a service — which has
        // no d3-drag pointer-capture — still receives its click
        // event after mouseup; setting pointer-events:none on
        // mousedown would otherwise route mouseup to the SVG bg.
        if (!panActiveFlag && svgEl.value) {
          panActiveFlag = true
          svgEl.value.classList.add('pan-active')
        }
      })
    el.call(zoomBeh)
    attachLasso(svg)
    // Center immediately so nodes don't flash at top-left on first render
    el.call(zoomBeh.transform, zoomIdentity.translate(W / 2, H / 2))
  }

  // --- Build FNode list (reuse cached positions) ---
  const levels = bfsLevels(topoNodes)
  const maxLvl = Math.max(0, ...levels.values())
  // When services are visible, increase vertical spacing to fit service rings.
  // Fan only extends downward so it needs ~half the inter-host gap of orbit.
  const maxSvcN = Math.max(0, ...[...(nodes.value ?? []).map((n) => n.services?.length ?? 0)])
  const minVSpacing =
    needsServices(props.serviceLayout) && maxSvcN > 0
      ? props.serviceLayout === 'fan'
        ? fanR(maxSvcN) + 50
        : orbitR(maxSvcN) * 2 + 50
      : 0
  const vSpacing = Math.max(minVSpacing, Math.min(130, (H * 0.8) / Math.max(1, maxLvl + 1)))

  // Host nodes first. New (uncached) hosts seed their pinned position from
  // the saved board view, so reload preserves the operator's layout.
  const savedPositions = props.flowView?.positions ?? {}
  const fNodes: FNode[] = topoNodes.map((n) => {
    const cached = nodeCache.get(n.name)
    if (cached) {
      const updated: FNode = {
        ...cached,
        state: n.state,
        output: n.output,
        bfsLevel: levels.get(n.name) ?? 0,
        nodeType: 'host',
        topo: n
      }
      nodeCache.set(n.name, updated)
      return updated
    }
    const saved = savedPositions[n.name]
    const node: FNode = {
      id: n.name,
      state: n.state,
      output: n.output,
      bfsLevel: levels.get(n.name) ?? 0,
      nodeType: 'host',
      topo: n,
      ...(saved ? { x: saved.x, y: saved.y, fx: saved.x, fy: saved.y } : {})
    }
    nodeCache.set(n.name, node)
    return node
  })

  // Service nodes appended after host nodes. When the backend reports a
  // truncation (services_truncated_count > 0) we append one "+M more" pseudo
  // node so users still see that the host has additional services.
  function pushChildNode(seed: Omit<FNode, keyof SimulationNodeDatum>): void {
    const cached = nodeCache.get(seed.id)
    const node: FNode = cached ? { ...cached, ...seed } : { ...seed }
    nodeCache.set(seed.id, node)
    fNodes.push(node)
  }
  if (needsServices(props.serviceLayout)) {
    for (const n of topoNodes) {
      if (!n.services) continue
      const hostLevel = levels.get(n.name) ?? 0
      const truncated = n.services_truncated_count ?? 0
      const N = n.services.length + (truncated > 0 ? 1 : 0)
      for (const svc of n.services) {
        pushChildNode({
          id: `${n.name}::${svc.name}`,
          state: svc.state,
          output: svc.output,
          bfsLevel: hostLevel,
          nodeType: 'service',
          hostId: n.name,
          svcTotalCount: N,
          svc,
          parentTopo: n
        })
      }
      if (truncated > 0) {
        pushChildNode({
          id: `${n.name}::${MORE_NODE_MARKER}`,
          state: 'PENDING',
          output: `${truncated} more service${truncated === 1 ? '' : 's'}`,
          bfsLevel: hostLevel,
          nodeType: 'more',
          hostId: n.name,
          svcTotalCount: N,
          moreCount: truncated,
          parentTopo: n
        })
      }
    }
  }

  // Synthetic site root nodes: surface a per-site root so the operator
  // always sees "X hosts on site Y" at a glance. Single-site Checkmk setups
  // don't tag rows with site_id (the federated multisite path does), so
  // fall back to the connection id.
  //
  // For flat topologies the site anchors a half-disk of hosts below it
  // (hosts visually hang under the site). For hierarchical topologies BFS
  // already drives the vertical layout, so the site just sits above the
  // topmost layer to avoid an empty chain.
  const rootCount = topoNodes.filter((n) => n.parents.length === 0).length
  const isMostlyFlat = topoNodes.length > 0 && rootCount / topoNodes.length >= 0.5
  const HOST_SITE_GAP = 140
  function siteIdFor(n: TopologyNode): string {
    return n.site_id || props.connectionId
  }
  const siteIds: string[] = []
  const hostsBySite = new Map<string, FNode[]>()
  if (topoNodes.length > 0) {
    const seen = new Set<string>()
    for (const fNode of fNodes) {
      if (fNode.nodeType !== 'host' || !fNode.topo) continue
      const sid = siteIdFor(fNode.topo)
      if (!seen.has(sid)) {
        seen.add(sid)
        siteIds.push(sid)
      }
      const arr = hostsBySite.get(sid) ?? []
      arr.push(fNode)
      hostsBySite.set(sid, arr)
    }
  }
  const siteSpread = Math.max(0, (siteIds.length - 1) * 600)
  const sitePositions = new Map<string, { x: number; y: number }>()
  siteIds.forEach((sid, i) => {
    const id = `__site__::${sid}`
    const xTarget =
      siteIds.length === 1 ? 0 : -siteSpread / 2 + (i * siteSpread) / (siteIds.length - 1)
    // Site initially sits above its host group. Scale offset with the
    // disk radius so the umbrella stays visually tied to its hosts on
    // small boards and clears the dispersion-induced spread on large
    // ones. Once the operator drags the site, the position is owned by
    // the user — we keep the cached fx/fy instead of snapping back.
    const groupSize = hostsBySite.get(sid)?.length ?? 0
    const groupDiskR = SPIRAL_SPACING * Math.sqrt(Math.max(1, groupSize))
    const defaultY = -(groupDiskR + 160)
    const cached = nodeCache.get(id)
    const node: FNode = cached
      ? { ...cached, nodeType: 'site', state: 'UP', siteId: sid }
      : {
          id,
          state: 'UP',
          output: '',
          bfsLevel: 0,
          nodeType: 'site',
          siteId: sid
        }
    if (!cached) {
      const saved = savedPositions[id]
      const fx = saved?.x ?? xTarget
      const fy = saved?.y ?? defaultY
      node.fx = fx
      node.fy = fy
      node.x = fx
      node.y = fy
    }
    nodeCache.set(id, node)
    fNodes.push(node)
    sitePositions.set(sid, { x: node.x ?? xTarget, y: node.y ?? defaultY })
  })

  // Severity-based pre-layout: hosts that don't have a cached position get
  // an initial arrangement so the force simulation has a glance-readable
  // starting point. On flat boards we group hosts per site and lay each
  // group out in a half-disk below its site root; on hierarchical boards
  // BFS drives the vertical layout, so the legacy phyllotaxis spiral is
  // kept around the origin.
  const uncachedHosts = fNodes.filter((n) => n.nodeType === 'host' && n.x === undefined)
  if (isMostlyFlat && siteIds.length > 0) {
    for (const sid of siteIds) {
      const sitePos = sitePositions.get(sid)
      if (!sitePos) continue
      const group = (hostsBySite.get(sid) ?? []).filter((n) => n.x === undefined)
      preLayoutHostsBelowSite(sitePos, group, HOST_SITE_GAP)
    }
  } else {
    preLayoutHosts(uncachedHosts)
  }
  const anchorX = new Map<string, number>()
  const anchorY = new Map<string, number>()
  for (const n of fNodes) {
    if (n.nodeType !== 'host') continue
    anchorX.set(n.id, finiteOr(n.x))
    anchorY.set(n.id, finiteOr(n.y))
  }

  // Remove stale cached nodes
  const activeIds = new Set(fNodes.map((n) => n.id))
  for (const k of nodeCache.keys()) {
    if (!activeIds.has(k)) nodeCache.delete(k)
  }

  const nodeById = new Map(fNodes.map((n) => [n.id, n]))

  // Parent → direct children map for "unpin on drag": dragging a parent
  // host should let its descendants float via forceLink instead of staying
  // anchored to an old fx/fy (which can linger from legacy subtree-pin
  // saves or earlier explicit drags). We unpin the whole subtree on
  // drag.start so the spring connection can actually pull them along.
  const hostNameSet = new Set(topoNodes.map((n) => n.name))
  const childMap = new Map<string, string[]>()
  for (const n of topoNodes) {
    for (const p of n.parents) {
      if (!hostNameSet.has(p)) continue
      const arr = childMap.get(p) ?? []
      arr.push(n.name)
      childMap.set(p, arr)
    }
  }

  const fLinks: FLink[] = []
  // Host-to-host links
  for (const n of topoNodes) {
    for (const p of n.parents) {
      const src = nodeById.get(p)
      const tgt = nodeById.get(n.name)
      if (src && tgt)
        fLinks.push({
          source: src,
          target: tgt,
          sourceState: src.state,
          isServiceLink: false
        })
    }
  }
  // Site-to-host links (only when synthetic site roots are active).
  // In a hierarchical topology only top-level hosts hang directly off the
  // site — child hosts already inherit a visual chain via parent_child.
  if (siteIds.length > 0) {
    const linkedHosts = isMostlyFlat ? topoNodes : topoNodes.filter((n) => n.parents.length === 0)
    for (const n of linkedHosts) {
      const siteId = `__site__::${siteIdFor(n)}`
      const arr = childMap.get(siteId) ?? []
      arr.push(n.name)
      childMap.set(siteId, arr)
      const src = nodeById.get(siteId)
      const tgt = nodeById.get(n.name)
      if (src && tgt)
        fLinks.push({
          source: src,
          target: tgt,
          sourceState: 'UP',
          isServiceLink: false
        })
    }
  }
  // Host-to-service links (and host-to-"+more" link if truncated)
  if (needsServices(props.serviceLayout)) {
    for (const n of topoNodes) {
      if (!n.services) continue
      const hostNode = nodeById.get(n.name)
      if (!hostNode) continue
      const moreNode = nodeById.get(`${n.name}::${MORE_NODE_MARKER}`)
      if (moreNode)
        fLinks.push({
          source: hostNode,
          target: moreNode,
          sourceState: hostNode.state,
          isServiceLink: true
        })
      for (const svc of n.services) {
        const svcNode = nodeById.get(`${n.name}::${svc.name}`)
        if (svcNode)
          fLinks.push({
            source: hostNode,
            target: svcNode,
            sourceState: hostNode.state,
            isServiceLink: true
          })
      }
    }
  }

  // Pre-compute service groups per host for fan layout. The "+more" pseudo
  // node participates in the layout so it gets its own slot in the orbit/fan.
  const servicesByHost = new Map<string, FNode[]>()
  for (const n of fNodes) {
    if ((n.nodeType === 'service' || n.nodeType === 'more') && n.hostId) {
      const arr = servicesByHost.get(n.hostId) ?? []
      arr.push(n)
      servicesByHost.set(n.hostId, arr)
    }
  }

  // Measured row spacings per host (populated after first DOM render)
  const rowSpacings = new Map<string, number>()

  // Service positioning
  function updateFanPositions() {
    for (const [hostId, services] of servicesByHost) {
      const host = nodeById.get(hostId)
      if (!host) continue
      const hx = finiteOr(host.x)
      const hy = finiteOr(host.y)
      const N = services.length

      if (props.serviceLayout === 'fan') {
        // Semicircle below host — radius scales with N so points don't overlap
        const R = fanR(N)
        const spread = N > 1 ? FAN_SPREAD : 0
        services.forEach((svc, i) => {
          const angle = Math.PI / 2 + (N > 1 ? -spread / 2 + (i * spread) / (N - 1) : 0)
          svc.fx = hx + R * Math.cos(angle)
          svc.fy = hy + R * Math.sin(angle)
        })
      } else if (props.serviceLayout === 'orbit') {
        const R = orbitR(N)
        services.forEach((svc, i) => {
          const angle = (2 * Math.PI * i) / N - Math.PI / 2
          svc.fx = hx + R * Math.cos(angle)
          svc.fy = hy + R * Math.sin(angle)
        })
      } else {
        // Row: compact grid with automatic wrapping
        const r = svcR(N)
        const cols = Math.min(N, Math.max(4, Math.ceil(Math.sqrt(N * 1.5))))
        const measured = rowSpacings.get(hostId)
        const fallback = services.reduce(
          (max, svc) => {
            const label = svc.id.split('::').at(-1) ?? svc.id
            return Math.max(max, label.length * 5.5 + 8)
          },
          r * 2 + 14
        )
        const spacingX = measured ?? fallback
        const spacingY = r * 2 + (showSvcLabel(N) ? 26 : 6)
        const yOffset = NODE_R + r + 22
        services.forEach((svc, i) => {
          const col = i % cols
          const row = Math.floor(i / cols)
          svc.fx = hx + (col - (cols - 1) / 2) * spacingX
          svc.fy = hy + yOffset + row * spacingY
        })
      }
    }
  }
  updateFanPositions()
  lastFNodes = fNodes

  // --- Update simulation ---
  if (simulation) simulation.stop()

  // Both host-host and site-host links participate in forceLink so a site
  // drag pulls its hosts along the same way a parent-host drag pulls its
  // children: the link acts as a spring. Service links remain excluded —
  // they're laid out geometrically by updateFanPositions().
  const springLinks = fLinks.filter((l) => !l.isServiceLink)

  simulation = forceSimulation<FNode>(fNodes)
    .force(
      'link',
      forceLink<FNode, FLink>(springLinks)
        .id((d) => d.id)
        .distance((d) => {
          const src = d.source as FNode
          const tgt = d.target as FNode
          // Site → host: scale with the host's service ring so a
          // dense top-K host doesn't sit on top of the site box.
          if (src.nodeType === 'site' || tgt.nodeType === 'site') {
            const host = src.nodeType === 'site' ? tgt : src
            const N = servicesByHost.get(host.id)?.length ?? 0
            return N > 0 ? Math.max(220, layoutR(N) + 80) : 220
          }
          // Host → host
          const srcN = servicesByHost.get(src.id)?.length ?? 0
          const tgtN = servicesByHost.get(tgt.id)?.length ?? 0
          if (srcN === 0 && tgtN === 0) return 160
          return Math.max(200, layoutR(srcN) + layoutR(tgtN) + 60)
        })
        // Site links pull more softly than host parent-child links so
        // the severity-disk pre-layout still dominates at rest while
        // the spring is visible on an actual site drag.
        .strength((d) => {
          const src = d.source as FNode
          const tgt = d.target as FNode
          if (src.nodeType === 'site' || tgt.nodeType === 'site') return 0.08
          return 0.4
        })
    )
    .force(
      'charge',
      // Only host nodes attract/repel each other; service and "+more"
      // pseudo-nodes are positioned geometrically by the layout helpers,
      // so applying charge to them just burns ticks at O(N log N). On
      // flat topologies with donut/off layouts the severity-ring
      // pre-layout already spreads hosts evenly, so charge is
      // suppressed — otherwise the all-to-all repulsion wins against
      // the anchor and flattens the rings into a wide ellipse. For
      // service-aware layouts (fan/orbit/row) we keep the charge so
      // top-K hosts with big service rings repel their (donut)
      // neighbours which would otherwise stay clamped by the severity
      // spiral anchor in the inner ring.
      forceManyBody<FNode>().strength((d) => {
        if (d.nodeType !== 'host') return 0
        if (maxLvl === 0 && !needsServices(props.serviceLayout)) return 0
        const N = servicesByHost.get(d.id)?.length ?? 0
        return N > 0 ? -Math.max(700, layoutR(N) * 9) : -600
      })
    )
    // Anchor strength: full grip on donut/off (where collide-radius is small
    // and the severity-spiral pre-layout already fits), softer on
    // fan/orbit/row so the much bigger top-K service rings can actually
    // push neighbours aside instead of being yanked back by the anchor.
    // Hosts that actually render service rings (services rendered, i.e.
    // not services_omitted) get no anchor at all so charge+collide can
    // disperse them freely.
    .force(
      'center',
      forceX<FNode>((d) => (d.nodeType === 'host' ? (anchorX.get(d.id) ?? 0) : 0)).strength((d) => {
        if (d.nodeType !== 'host') return 0
        if (!needsServices(props.serviceLayout)) return 0.18
        const N = servicesByHost.get(d.id)?.length ?? 0
        return N > 0 ? 0 : 0.06
      })
    )
    .force(
      'collide',
      forceCollide<FNode>((d) => {
        if (d.nodeType === 'service') return 0
        if (d.nodeType === 'site') return 70
        const svcs = servicesByHost.get(d.id) ?? []
        const N = svcs.length
        if (N === 0 || !needsServices(props.serviceLayout)) {
          // Donut sits directly on the host — reserve the donut width
          // for donut layout and for top-K-omitted hosts in fan/orbit/row.
          const wantsDonut = props.serviceLayout === 'donut' || (d.topo?.services_omitted ?? false)
          return wantsDonut ? NODE_R + 14 : NODE_R + 10
        }
        if (props.serviceLayout === 'fan' || props.serviceLayout === 'orbit')
          return layoutR(N) + svcR(N) + 35
        // Row grid
        const cols = Math.min(N, Math.max(4, Math.ceil(Math.sqrt(N * 1.5))))
        const spacingX = rowSpacings.get(d.id) ?? 60
        return (cols / 2) * spacingX + svcR(N) + 20
      }).iterations(needsServices(props.serviceLayout) ? 5 : maxLvl > 0 ? 3 : 1)
    )
    .force(
      'y',
      // For real BFS hierarchies (maxLvl > 0) keep the layered look; for
      // flat topologies anchor each host to its severity-ring slot so the
      // pre-layout's glance-readable structure survives the force pass.
      maxLvl > 0
        ? forceY<FNode>((d) => (d.bfsLevel - maxLvl / 2) * vSpacing).strength((d) =>
            d.nodeType === 'service' ? 0 : 0.4
          )
        : forceY<FNode>((d) => (d.nodeType === 'host' ? (anchorY.get(d.id) ?? 0) : 0)).strength(
            (d) => {
              if (d.nodeType !== 'host') return 0
              if (!needsServices(props.serviceLayout)) return 0.18
              const N = servicesByHost.get(d.id)?.length ?? 0
              return N > 0 ? 0 : 0.06
            }
          )
    )
    // Faster alpha decay on flat boards: the severity-spiral pre-layout
    // already places hosts in their target slots, so the sim only needs
    // to resolve overlaps — 30 ticks is enough. For real BFS hierarchies
    // keep the slower decay so the layered layout has time to settle.
    // Service-aware layouts (fan/orbit/row) also need the slower decay
    // because collide has to push the much bigger top-K rings apart
    // against the (softened) anchor pull.
    .alphaDecay(maxLvl > 0 || needsServices(props.serviceLayout) ? 0.05 : 0.1)
    .stop()

  // --- Drag behaviour ---
  // Each draggable node is treated independently: only the dragged node
  // gets pinned to the cursor. Children/parents react through the running
  // force simulation (forceLink + forceCollide + forceManyBody), so
  // related hosts float along with a natural spring delay instead of
  // tracking the cursor rigidly. The site is just another draggable node;
  // because site→host links are visual-only the site moves independently.
  let dragMoved = false
  function collectDescendants(rootId: string, out: Set<string>): void {
    const queue: string[] = [rootId]
    while (queue.length) {
      const id = queue.shift()!
      const children = childMap.get(id)
      if (!children) continue
      for (const childId of children) {
        if (out.has(childId)) continue
        out.add(childId)
        queue.push(childId)
      }
    }
  }
  const dragBehavior = drag<SVGGElement, FNode>()
    .on('start', (event, d) => {
      cancelPendingFit()
      dragMoved = false
      // Wake the simulation here, not in drag.drag — d3-drag's
      // `event.active` is 0 only in start/end (the gesture isn't
      // counted yet/anymore). In drag.drag it's always ≥ 1, so the
      // textbook `if (!event.active) sim.alphaTarget(0.3).restart()`
      // gate would never fire there, leaving the sim stopped after
      // it settled the first time → subsequent drags would update
      // fx but never tick to push the change into d.x / transform.
      if (!event.active && simulation) simulation.alphaTarget(0.3).restart()
      // Free the dragged parent's descendants so forceLink can pull
      // them along as the parent (or site) moves. Without this any
      // child that had a saved fx/fy (from a prior direct drag) stays
      // frozen and the spring connection looks broken.
      if (d.nodeType === 'host' || d.nodeType === 'site') {
        const subtree = new Set<string>()
        collectDescendants(d.id, subtree)
        for (const id of subtree) {
          const node = nodeCache.get(id)
          if (!node) continue
          node.fx = null
          node.fy = null
        }
      }
    })
    .on('drag', (event, d) => {
      const root = nodeCache.get(d.id)
      if (!root) return
      dragMoved = true
      root.fx = event.x
      root.fy = event.y
    })
    .on('end', (event, d) => {
      // Always release the alphaTarget so the sim cools down after the
      // drag — even bare clicks (no movement) get a brief wake from
      // start.alphaTarget(0.3) and need to be cooled back to 0.
      if (!event.active && simulation) simulation.alphaTarget(0)
      if (!dragMoved) return
      const root = nodeCache.get(d.id) ?? d
      if (typeof root.fx === 'number') root.x = root.fx
      if (typeof root.fy === 'number') root.y = root.fy
      // Readonly boards (demos) allow interactive drags but don't
      // persist them — every session gets its own layout playground.
      if (!props.readonly && (root.nodeType === 'host' || root.nodeType === 'site')) {
        emitPinnedPositions()
      }
      dragMoved = false
    })

  // --- Links ---
  const gLinks = gZoom.select<SVGGElement>('g.links')
  const linkSel = gLinks
    .selectAll<SVGLineElement, FLink>('line')
    .data(fLinks, (d) => `${(d.source as FNode).id}→${(d.target as FNode).id}`)
  linkSel.exit().remove()
  const linkEnter = linkSel.enter().append('line')
  const linkMerge = linkEnter
    .merge(linkSel)
    .attr('class', (d) => (d.isServiceLink ? 'link link-service' : 'link'))
    .attr('stroke', (d) => {
      const src = d.source as FNode
      // Site→host links carry no state, so they use the theme-aware muted
      // text colour (via currentColor on g.links) to stay legible on both
      // light and dark board backgrounds rather than a fixed faint grey.
      if (src.nodeType === 'site') return 'currentColor'
      return stateColor(src.state)
    })
    .attr('stroke-opacity', (d) => {
      if ((d.source as FNode).nodeType === 'site') return 0.55
      return d.isServiceLink ? 0.3 : 0.45
    })
    .attr('stroke-width', (d) => {
      if ((d.source as FNode).nodeType === 'site') return 1
      return d.isServiceLink ? 1 : 1.5
    })
    .attr('stroke-dasharray', (d) => {
      if ((d.source as FNode).nodeType === 'site') return '2,3'
      return d.isServiceLink ? '3,3' : null
    })

  // --- Nodes ---
  const gNodes = gZoom.select<SVGGElement>('g.nodes')
  const nodeSel = gNodes.selectAll<SVGGElement, FNode>('g.node').data(fNodes, (d) => d.id)
  nodeSel.exit().remove()

  const nodeEnter = nodeSel
    .enter()
    .append('g')
    .attr('class', (d) => `node node-${d.nodeType}`)
    .attr('cursor', (d) => {
      // Readonly boards (e.g. the bundled demos) still allow drags so
      // the layout feels interactive — only the persistence is gated.
      if (d.nodeType === 'site' || d.nodeType === 'host') return 'grab'
      return props.clickAction === 'none' ? 'default' : 'pointer'
    })
    .on('click', (event: MouseEvent, d) => {
      // Site root opens an aggregated drawer; no shift-select / context
      // menu since site-level bulk ops aren't a thing.
      if (d.nodeType === 'site') {
        hoverGrace.cancelClose()
        hoverMenu.visible = false
        openDetail(boardObjectFromFNode(d), d)
        return
      }
      if (props.clickAction === 'none') return
      // Shift-click toggles multi-select. Modifier (Ctrl/Cmd) keeps the
      // legacy "open in Checkmk" behavior. Plain click opens the in-app
      // detail drawer so the operator doesn't lose context with new tabs.
      if (event.shiftKey) {
        toggleSelection(d)
        return
      }
      if (event.ctrlKey || event.metaKey) {
        const url = buildCheckmkUrl(
          boardObjectFromFNode(d),
          props.checkmkUrl ?? null,
          objectStateFromFNode(d).site_id
        )
        if (url) openUrl(url, '_blank')
        return
      }
      hoverGrace.cancelClose()
      hoverMenu.visible = false
      openDetail(boardObjectFromFNode(d), d)
    })
    .on('contextmenu', (event: MouseEvent, d) => {
      if (d.nodeType === 'site') return
      event.preventDefault()
      hoverGrace.cancelClose()
      hoverMenu.visible = false
      contextMenu.object = boardObjectFromFNode(d)
      contextMenu.state = objectStateFromFNode(d)
      contextMenu.x = event.pageX
      contextMenu.y = event.pageY
      contextMenu.visible = true
    })
    .on('mouseenter', (event: MouseEvent, d) => {
      if (props.preview || d.nodeType === 'site') return
      hoverGrace.cancelClose()
      const nodeRect = (event.currentTarget as SVGGElement).getBoundingClientRect()
      hoverFNode.value = d
      hoverMenu.object = boardObjectFromFNode(d)
      hoverMenu.x = nodeRect.right + 8
      hoverMenu.y = nodeRect.top
      hoverMenu.visible = true
    })
    .on('mouseleave', () => {
      // Grace instead of hiding outright: the card carries clickable state
      // pills, so the pointer must survive the trip onto it.
      hoverGrace.scheduleClose()
    })

  // Readonly boards keep drag interactive (persistence inside drag.end
  // gates on props.readonly); only preview iframes opt out entirely.
  if (!props.preview) {
    nodeEnter
      .filter((d) => d.nodeType === 'host' || d.nodeType === 'site')
      .call(dragBehavior as never)
  }

  // Site root nodes (synthetic): rounded rect with site name.
  const siteEnter = nodeEnter.filter((d) => d.nodeType === 'site')
  const SITE_RECT_W = 110
  const SITE_RECT_H = 36
  siteEnter
    .append('rect')
    .attr('x', -SITE_RECT_W / 2)
    .attr('y', -SITE_RECT_H / 2)
    .attr('width', SITE_RECT_W)
    .attr('height', SITE_RECT_H)
    .attr('rx', 8)
    .attr('fill', 'var(--bg-surface)')
    .attr('stroke', 'var(--text-muted)')
    .attr('stroke-width', 1.5)
  siteEnter
    .append('text')
    .attr('class', 'type-char')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('fill', 'var(--text-muted)')
    .attr('font-size', 9)
    .attr('font-weight', '600')
    .attr('letter-spacing', '0.08em')
    .attr('pointer-events', 'none')
    .attr('y', -8)
    .text('SITE')
  siteEnter
    .append('text')
    .attr('class', 'node-label')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('font-size', 13)
    .attr('font-weight', '700')
    .attr('pointer-events', 'none')
    .style('fill', 'var(--text)')
    .attr('y', 6)
    .text((d) => d.siteId ?? '')

  // Host nodes
  const hostEnter = nodeEnter.filter((d) => d.nodeType === 'host')
  hostEnter
    .append('circle')
    .attr('r', NODE_R)
    .attr('stroke', 'rgba(0,0,0,0.4)')
    .attr('stroke-width', 1.5)
  // Empty donut container — actual segments are bound in the update pass below.
  hostEnter.append('g').attr('class', 'donut').attr('pointer-events', 'none')
  hostEnter
    .append('text')
    .attr('class', 'type-char')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('fill', 'rgba(255,255,255,0.9)')
    .attr('font-size', 11)
    .attr('font-weight', '700')
    .attr('pointer-events', 'none')
    .text('H')
  hostEnter
    .append('text')
    .attr('class', 'node-label')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'hanging')
    .attr('font-size', 11)
    .attr('font-weight', '500')
    .attr('pointer-events', 'none')
    .style('fill', 'var(--text)')
    // y is recomputed by refreshHostLabelOffsets() to clear the donut ring;
    // start with the worst-case offset so the first paint never overlaps.
    .attr('y', NODE_R + DONUT_MAX_WIDTH + 5)

  // Service nodes
  const svcEnter = nodeEnter.filter((d) => d.nodeType === 'service')
  svcEnter
    .append('circle')
    .attr('r', (d) => svcR(d.svcTotalCount ?? 1))
    .attr('stroke', 'rgba(0,0,0,0.4)')
    .attr('stroke-width', 1)
  svcEnter
    .append('text')
    .attr('class', 'type-char')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('fill', 'rgba(255,255,255,0.9)')
    .attr('font-size', (d) => (svcR(d.svcTotalCount ?? 1) <= 7 ? 6 : 8))
    .attr('font-weight', '700')
    .attr('pointer-events', 'none')
    .text('S')
  svcEnter
    .append('text')
    .attr('class', 'node-label')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'hanging')
    .attr('font-size', 9)
    .attr('font-weight', '400')
    .attr('pointer-events', 'none')
    .style('fill', 'var(--text)')
    .attr('y', (d) => svcR(d.svcTotalCount ?? 1) + 4)
    .style('display', (d) => (showSvcLabel(d.svcTotalCount ?? 1) ? null : 'none'))

  // "+N more" pseudo nodes: same shape as services but with a neutral fill
  // and a `+N` glyph. They're not real services — clicking opens the host's
  // service list in Checkmk (handled in the shared click handler below).
  const moreEnter = nodeEnter.filter((d) => d.nodeType === 'more')
  moreEnter
    .append('circle')
    .attr('r', (d) => svcR(d.svcTotalCount ?? 1))
    .attr('stroke', 'rgba(0,0,0,0.4)')
    .attr('stroke-width', 1)
  moreEnter
    .append('text')
    .attr('class', 'type-char')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('fill', 'rgba(255,255,255,0.95)')
    .attr('font-size', (d) => (svcR(d.svcTotalCount ?? 1) <= 7 ? 7 : 9))
    .attr('font-weight', '700')
    .attr('pointer-events', 'none')
    .text((d) => `+${d.moreCount ?? 0}`)
  moreEnter
    .append('text')
    .attr('class', 'node-label')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'hanging')
    .attr('font-size', 9)
    .attr('font-weight', '400')
    .attr('pointer-events', 'none')
    .style('fill', 'var(--text)')
    .attr('y', (d) => svcR(d.svcTotalCount ?? 1) + 4)
    .text((d) => `+${d.moreCount ?? 0} more`)
    .style('display', (d) => (showSvcLabel(d.svcTotalCount ?? 1) ? null : 'none'))

  // Command-state badge container (ack / downtime / notifications-off),
  // rendered last so badges sit above the node circle. pointer-events none so
  // they never steal drag/click; the hover menu carries the same info textually.
  nodeEnter
    .filter((d) => d.nodeType === 'host' || d.nodeType === 'service')
    .append('g')
    .attr('class', 'cmd-markers')
    .attr('pointer-events', 'none')

  const nodeMerge = nodeEnter.merge(nodeSel)
  nodeMerge.select('circle').attr('fill', (d) => stateColor(d.state))
  nodeMerge
    .filter((d) => d.nodeType === 'host')
    .each(function (d) {
      const circle = (this as SVGGElement).querySelector('circle')
      if (!circle) return
      const halo = hostHalo(d)
      circle.setAttribute('stroke', halo.stroke)
      circle.setAttribute('stroke-width', String(halo.width))
      // Top-K glow filter is anchored on the host group (not the circle)
      // so the worst-N hosts are visually unmissable even at fit-zoom
      // where stroke width alone collapses to <1 screen pixel.
      const isTopK = topKWorstIds.value.has(d.id)
      if (isTopK) {
        ;(this as SVGGElement).setAttribute('filter', 'url(#top-k-glow)')
      } else {
        ;(this as SVGGElement).removeAttribute('filter')
      }
    })

  // Donut update — bind aggregated services_summary as proportional arcs on
  // each host. Always rendered in donut layout; in fan/orbit/row only for
  // hosts whose service detail wasn't fetched (top-K cutoff in the backend),
  // so the user still sees an at-a-glance state aggregate. The exit() removes
  // leftover paths when a host transitions out of either condition.
  const donutArc = buildDonutArc(currentZoomK)
  nodeMerge
    .filter((d) => d.nodeType === 'host')
    .each(function (d) {
      // Off respects the operator's explicit choice — no automatic
      // services_omitted fallback. Donut always shows arcs. Detail
      // layouts (fan/orbit/row) fall back to donut only when the
      // backend dropped per-service rows for top-K cutoff.
      const layout = props.serviceLayout
      const showDonut =
        layout === 'donut' || (layout !== 'off' && (d.topo?.services_omitted ?? false))
      const segments = showDonut && d.topo ? donutSegments(d.topo) : []
      const arcs = donutPie(segments)
      const donutG = select(this).select<SVGGElement>('g.donut')
      const paths = donutG
        .selectAll<SVGPathElement, (typeof arcs)[number]>('path')
        .data(arcs, (a) => a.data.state)
      paths.exit().remove()
      paths
        .enter()
        .append('path')
        .merge(paths)
        .attr('d', (a) => donutArc(a) ?? '')
        .attr('fill', (a) => stateColor(a.data.state))
        .attr('stroke', 'rgba(0,0,0,0.35)')
        .attr('stroke-width', 0.5)
    })
  // Command-state markers — bind active flags as small corner badges. Runs on
  // every render; ack/downtime/notif changes are in the topology change-hash
  // so a real change triggers a re-render here (no extra timing dependency).
  nodeMerge
    .filter((d) => d.nodeType === 'host' || d.nodeType === 'service')
    .each(function (d) {
      const R = d.nodeType === 'service' ? svcR(d.svcTotalCount ?? 1) : NODE_R
      const rb = Math.max(4, R * 0.34)
      const g = select(this).select<SVGGElement>('g.cmd-markers')
      const sel = g
        .selectAll<SVGGElement, CmdMarker>('g.cmd-badge')
        .data(commandMarkers(d), (m) => m.key)
      sel.exit().remove()
      const en = sel.enter().append('g').attr('class', 'cmd-badge')
      en.append('circle').attr('stroke', 'var(--bg-surface)').attr('stroke-width', 1.5)
      en.append('text')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('font-weight', '700')
      en.append('title')
      const m = en.merge(sel)
      m.attr('transform', (mk) => {
        const [x, y] = badgeXY(mk.corner, R)
        return `translate(${x},${y})`
      })
      m.select('circle')
        .attr('r', rb)
        .attr('fill', (mk) => mk.fill)
      m.select('text')
        .attr('font-size', rb * 1.3)
        .attr('fill', (mk) => mk.fg)
        .text((mk) => mk.glyph)
      m.select('title').text((mk) => mk.title)
    })

  nodeMerge.select('text.node-label').text((d) => {
    if (d.nodeType === 'more') return `+${d.moreCount ?? 0} more`
    if (d.nodeType === 'service') {
      // split() always yields ≥ 1 element
      return d.id.split('::').at(-1)!
    }
    if (d.nodeType === 'site') return d.siteId ?? ''
    return d.id
  })
  // Refresh service / more-label visibility — may change when switching layout or on re-render
  nodeMerge
    .filter((d) => d.nodeType === 'service' || d.nodeType === 'more')
    .select('text.node-label')
    .style('display', (d) => (showSvcLabel(d.svcTotalCount ?? 1) ? null : 'none'))

  // --- Tick handler ---
  // The first paint can race the d3-force `initializeNodes` step on layout
  // switches that null out cached host positions, so coerce non-finite
  // coordinates to 0 to avoid SVG attribute errors (the next tick fixes them).
  const _coord = finiteOr
  function ticked() {
    updateFanPositions()
    linkMerge
      .attr('x1', (d) => _coord((d.source as FNode).x))
      .attr('y1', (d) => _coord((d.source as FNode).y))
      .attr('x2', (d) => _coord((d.target as FNode).x))
      .attr('y2', (d) => _coord((d.target as FNode).y))
      // Keep site→host links on the theme-aware muted colour (currentColor)
      // here too — the tick handler otherwise reverts them to stateColor.
      .attr('stroke', (d) =>
        (d.source as FNode).nodeType === 'site'
          ? 'currentColor'
          : stateColor((d.source as FNode).state)
      )

    nodeMerge
      .attr('transform', (d) => {
        const x = _coord(d.x)
        const y = _coord(d.y)
        if (d.nodeType === 'site') {
          return `translate(${x},${y}) scale(${siteScaleForZoom(currentZoomK)})`
        }
        return `translate(${x},${y})`
      })
      .select('circle')
      .attr('fill', (d) => stateColor(d.state))
  }

  // Measure actual row-label widths from the DOM before the simulation starts;
  // updateFanPositions reads `rowSpacings` to lay out the row grid.
  if (props.serviceLayout === 'row') {
    for (const [hostId, services] of servicesByHost) {
      const N = services.length
      if (!showSvcLabel(N)) {
        rowSpacings.set(hostId, svcR(N) * 2 + 6)
        continue
      }
      let maxW = 0
      for (const svc of services) {
        const g = gNodes
          .selectAll<SVGGElement, FNode>('g.node')
          .filter((d) => d.id === svc.id)
          .node()
        const textEl = g?.querySelector<SVGTextElement>('text.node-label')
        if (textEl) maxW = Math.max(maxW, textEl.getComputedTextLength())
      }
      if (maxW > 0) rowSpacings.set(hostId, maxW + 10)
    }
  }

  // Paint once with cached/initial positions so users see something immediately.
  updateFanPositions()
  ticked()
  // Reapply LoD so newly entered service / "+more" nodes pick up the
  // current zoom-driven display state.
  applyLod()
  refreshHostLabelOffsets()
  refreshSiteScale()
  applyFilterOpacity()
  applySelectionStyles()

  // F1: don't synchronously tick(250) — that blocks the main thread for
  // hundreds of ms at scale. Let the simulation converge asynchronously and
  // refine the fit once it has settled.
  const isInitial = !_hasFitOnce
  // Compare the new host id set against the previous render to detect
  // genuine structural changes (host added/removed/renamed) vs. pure
  // status-only updates. WS push every few seconds — without this gate
  // every push restarts the force sim for 1-2s of CPU spike on 500-host
  // boards even though nothing structurally changed.
  const newHostIds = new Set<string>(topoNodes.map((n) => n.name))
  const structurallyChanged =
    newHostIds.size !== _lastHostIds.size || [...newHostIds].some((id) => !_lastHostIds.has(id))
  _lastHostIds = newHostIds

  simulation.on('tick', ticked)
  if (isInitial || structurallyChanged) {
    // Lower initial alpha on flat boards: pre-layout already approximates
    // the steady state, so 0.4 settles in ~25 ticks instead of ~75 from
    // alpha=1. Hierarchical boards still need full-energy initial sim.
    // Service-aware layouts need full energy too — collide has to push the
    // top-K rings apart from the donut-packed spiral starting point.
    const initAlpha = isInitial ? (maxLvl > 0 || needsServices(props.serviceLayout) ? 1 : 0.4) : 0.2
    simulation.alpha(initAlpha).restart()
  } else {
    // Status-only update: state colors / donut segments / halos already
    // refreshed via nodeMerge above. No need to advance the sim — the
    // operator's existing layout stays put and CPU is idle until the
    // next structural change. Drive alpha to zero so a subsequent
    // pan/zoom doesn't resurrect the freshly-constructed sim — the
    // forceSimulation() constructor leaves alpha at 1, and end.simfreeze
    // would otherwise see "alpha > alphaMin" and call restart(), kicking
    // every host back into a force-relaxation pass on each WS push.
    simulation.alpha(0).stop()
  }
  if (isInitial) {
    _hasFitOnce = true
    // Pre-layout already arranged hosts in a severity spiral, so an
    // immediate (un-animated) fit gives the operator structure on first
    // paint instead of a 4-6s wait for simulation.end.
    fitView({ animated: false })
    // Refine the fit once collide/charge have spread overlapping nodes.
    // Lower tick cap because pre-layout starts close to the steady state.
    let fitFired = false
    const detachListeners = (): void => {
      simulation?.on('tick.fit', null)
      simulation?.on('end.fit', null)
    }
    const fireFit = (): void => {
      if (fitFired) return
      fitFired = true
      detachListeners()
      fitView({ animated: true })
    }
    // Operator interactions (open detail, drag, manual zoom) call this to
    // claim the current view before the refining fit can yank it.
    _cancelPendingFit = () => {
      fitFired = true
      detachListeners()
    }
    const maxTicks = needsServices(props.serviceLayout) ? 120 : 30
    let ticks = 0
    simulation.on('end.fit', fireFit)
    simulation.on('tick.fit', () => {
      ticks++
      if (ticks >= maxTicks) fireFit()
    })
  }
}

function closeAckModal(): void {
  ackModalObject.value = null
  statesStore.refreshAfterCommand()
}

function closeDowntimeModal(): void {
  downtimeModalObject.value = null
  statesStore.refreshAfterCommand()
}

function closeRemoveDowntimeModal(): void {
  removeDowntimeModal.visible = false
  statesStore.refreshAfterCommand()
}
</script>

<style scoped>
/* Level-of-detail: at low zoom the service rings + "+more" badges and the
   service-links between them are unreadable, so we hide them via a single
   class on the SVG root rather than inline-styling thousands of elements. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(svg.lod-low g.node-service),
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(svg.lod-low g.node-more),
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(svg.lod-low g.links line.link-service) {
  display: none;
}

/* Promote the panned/zoomed group to its own GPU-composited layer so the
   browser can re-rasterize the (large) SVG subtree once and just translate
   the layer per frame, instead of repainting all 500+ host icons +
   service rings every pan/zoom step. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(g.zoom-layer) {
  will-change: transform;
}

/* During an active pan/zoom gesture, suppress hit-testing on the entire
   zoom-layer so pointermove doesn't traverse ~3000 SVG descendants per
   frame just to figure out hover targets the user can't interact with
   while dragging anyway. d3-zoom's start/end handlers toggle this class. */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(svg.pan-active g.zoom-layer) {
  pointer-events: none;
}

/* Site→host links are stroked with currentColor; bind it to the theme-aware
   muted text colour so they stay visible in both light and dark themes. */
:deep(g.links) {
  color: var(--text-muted);
}

.orb-flow {
  position: absolute;
  inset: 0;
  background: var(--bg);
}

.orb-flow__center {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.orb-flow__center--error {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--color-light-red-40);
}

.orb-flow__svg {
  display: block;
  width: 100%;
  height: 100%;
}

.orb-flow__zoom {
  position: absolute;
  bottom: var(--dimension-6);
  left: var(--dimension-6);
  z-index: 10;
  display: flex;
  overflow: hidden;
  flex-direction: column;
  border-radius: 12px;
  box-shadow:
    0 0 0 1px var(--border),
    0 20px 25px -5px rgb(0 0 0 / 40%),
    0 8px 10px -6px rgb(0 0 0 / 40%);
}

.orb-flow__zoom-btn {
  padding: 5px;
  color: var(--text-muted);
  background: color-mix(in srgb, var(--bg-surface) 90%, transparent);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(12px);
  transition:
    color 0.15s cubic-bezier(0.4, 0, 0.2, 1),
    background-color 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.orb-flow__zoom-btn:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.orb-flow__zoom-btn--last {
  border-bottom: none;
}

.flow-hint {
  /* Beside the zoom controls rather than over the topology center, where it
       collided with the root node at some zoom levels. */
  position: absolute;
  bottom: 16px;
  left: 56px;
  z-index: 6;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 4px 4px 10px;
  border-radius: var(--border-radius);
  background: var(--bg-glass);
  color: var(--text);
  font-size: 11px;
  backdrop-filter: blur(6px);
  border: 1px solid var(--border);
  pointer-events: none;
  max-width: min(60%, 520px);
  text-align: left;
}

.flow-hint__dismiss {
  pointer-events: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
}

.flow-hint__dismiss:hover {
  color: var(--text);
  background: rgb(255 255 255 / 10%);
}

.bulk-actions {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 6;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--border-radius);
  box-shadow: 0 6px 24px rgb(0 0 0 / 40%);
}

.bulk-actions__count {
  font-size: 12px;
  font-weight: var(--font-weight-semibold);
  color: var(--text);
  margin-right: 4px;
}

.bulk-actions__btn {
  background: var(--bg);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: var(--border-radius);
  padding: 4px 10px;
  font-size: 11px;
  cursor: pointer;
}

.bulk-actions__btn:hover {
  background: var(--bg-hover);
}

.bulk-actions__btn--clear {
  width: 24px;
  padding: 0;
  text-align: center;
  color: var(--text-muted);
}
</style>
