<template>
  <div
    ref="containerRef"
    class="pres"
    :class="{ 'pres--edit': interactive }"
    @pointerdown="onStagePointerDown"
  >
    <div
      class="pres__stage"
      :style="stageStyle"
      @pointerdown.stop="onSlidePointerDown"
      @dblclick="onSlideDblClick"
    >
      <div class="pres__bg" :style="bgStyle" />

      <!-- Connectors render in their own slide-space layer (behind boxes) so a
           docked line can run at any angle between the elements it links. -->
      <svg class="pres__connectors" :style="overlaySvgStyle">
        <!-- Highlight the element an endpoint would dock to on release. -->
        <rect
          v-if="dockCandidate"
          class="pres__dock-target"
          :x="dockCandidate.x"
          :y="dockCandidate.y"
          :width="dockCandidate.w"
          :height="dockCandidate.h"
          :stroke-width="2 / scale"
          :rx="6 / scale"
        />
        <PresentationConnector
          v-for="c in connectors"
          :key="c.el.id"
          :element="c.el"
          :start="c.start"
          :end="c.end"
          :state="stateFor(c.el)"
          :selected="interactive && selectedIds.includes(c.el.id)"
          :interactive="interactive"
          :scale="scale"
          @pointerdown="onConnectorPointerDown(c.el, $event)"
          @endpoint-down="(which, e) => onEndpointPointerDown(c.el, which, e)"
        />
      </svg>

      <div v-if="interactive && !elements.length" class="pres__empty">
        {{ _t('Pick a tool above to start your slide') }}
      </div>

      <div
        v-for="el in inlineElements"
        :key="el.id"
        class="pres__el"
        :class="{
          'pres__el--selected': interactive && selectedIds.includes(topLevelId(el.id)),
          'pres__el--locked': el.locked,
          'pres__el--hidden': interactive && el.hidden
        }"
        :style="elementStyle(el)"
        @pointerdown.stop="onElementPointerDown(el, $event)"
      >
        <PresentationElementView
          :element="el"
          :state="stateFor(el)"
          :editing-text="editingTextId === el.id"
          @text-change="onTextChange(el.id, $event)"
        />
      </div>

      <svg v-if="interactive && activeGuides.length" class="pres__guides" :style="overlaySvgStyle">
        <line
          v-for="(g, i) in activeGuides"
          :key="i"
          :x1="g.axis === 'x' ? g.pos : g.start"
          :y1="g.axis === 'x' ? g.start : g.pos"
          :x2="g.axis === 'x' ? g.pos : g.end"
          :y2="g.axis === 'x' ? g.end : g.pos"
          stroke="#f472b6"
          :stroke-width="1 / scale"
        />
      </svg>

      <div v-if="interactive && selectionBox" class="pres__sel" :style="selBoxStyle">
        <template v-if="selectedIds.length === 1 && !primaryLocked && !singleIsConnector">
          <div
            v-for="h in handles"
            :key="h"
            class="pres__handle"
            :class="`pres__handle--${h}`"
            :style="handleStyle(h)"
            @pointerdown.stop="onHandlePointerDown(h, $event)"
          />
          <div
            class="pres__rotate"
            :style="rotateHandleStyle"
            @pointerdown.stop="onRotatePointerDown($event)"
          />
        </template>
      </div>

      <div v-if="marquee.visible.value" class="pres__marquee" :style="marqueeStyle" />
    </div>

    <div v-if="interactive" class="pres__palette">
      <button
        v-for="tool in contentTools"
        :key="tool.kind"
        class="pres__tool"
        :title="tool.title"
        @pointerdown.stop
        @click="insert(tool.kind)"
      >
        <span v-html="tool.icon" />
      </button>
      <div class="pres__tool-sep" />
      <button
        v-for="tool in shapeTools"
        :key="tool.kind"
        class="pres__tool"
        :title="tool.title"
        @pointerdown.stop
        @click="insert(tool.kind)"
      >
        <span v-html="tool.icon" />
      </button>
      <div class="pres__tool-sep" />
      <button
        class="pres__tool"
        :class="{ 'pres__tool--on': settingsOpen }"
        :title="_t('Slide settings')"
        @click.stop="toggleSettings"
      >
        <span v-html="ICONS.settings" />
      </button>
      <button
        class="pres__tool"
        :class="{ 'pres__tool--on': layersOpen }"
        :title="_t('Layers')"
        @click.stop="toggleLayers"
      >
        <span v-html="ICONS.layers" />
      </button>
    </div>

    <div
      v-if="interactive && settingsOpen"
      v-click-outside="closeSettings"
      class="pres__settings"
      @pointerdown.stop
    >
      <div class="pres__settings-head">
        <span>{{ _t('Slide settings') }}</span>
        <button class="pres__layers-x" @click="settingsOpen = false">×</button>
      </div>
      <div class="pres__settings-body">
        <label class="pres__settings-label">{{ _t('Theme') }}</label>
        <select v-model="local.theme" class="pres__select" @change="onSlideMetaChange">
          <option v-for="t in themeChoices" :key="t.name" :value="t.name">{{ t.title }}</option>
        </select>

        <label class="pres__settings-label">{{ _t('Aspect / size') }}</label>
        <div class="pres__preset-grid">
          <button
            v-for="p in slidePresets"
            :key="p.label"
            class="pres__preset"
            :class="{ 'pres__preset--on': local.width === p.w && local.height === p.h }"
            @click="applyPreset(p.w, p.h)"
          >
            {{ p.label }}
          </button>
        </div>

        <div class="pres__settings-row">
          <label class="pres__num">
            {{ _t('Width') }}
            <input
              type="number"
              min="320"
              max="8192"
              :value="local.width"
              @change="setSlideSize(numVal($event), local.height)"
            />
          </label>
          <label class="pres__num">
            {{ _t('Height') }}
            <input
              type="number"
              min="320"
              max="8192"
              :value="local.height"
              @change="setSlideSize(local.width, numVal($event))"
            />
          </label>
        </div>

        <label class="pres__settings-label">{{ _t('Background') }}</label>
        <div class="pres__bg-row">
          <ColorField
            :label="_t('Background color')"
            :value="local.background ?? null"
            @set="setBackground"
          />
          <span class="pres__bg-hint">{{
            local.background ? local.background : _t('Theme default')
          }}</span>
        </div>
        <ImagePicker
          :model-value="local.background_image ?? ''"
          :placeholder="_t('Background image…')"
          @update:model-value="setBackgroundImage"
        />
      </div>
    </div>

    <div v-if="interactive" class="pres__hud">
      <button
        class="pres__hud-btn"
        :disabled="!history.canUndo.value"
        :title="_t('Undo')"
        @click="undo"
      >
        <span v-html="ICONS.undo" />
      </button>
      <button
        class="pres__hud-btn"
        :disabled="!history.canRedo.value"
        :title="_t('Redo')"
        @click="redo"
      >
        <span v-html="ICONS.redo" />
      </button>
      <span class="pres__hud-status">{{ saveLabel }}</span>
    </div>

    <div v-if="interactive && selectedIds.length >= 2" class="pres__align">
      <button
        v-for="a in alignActions"
        :key="a.id"
        class="pres__tool"
        :title="a.title"
        @click="a.run()"
      >
        <span v-html="a.icon" />
      </button>
    </div>

    <PresentationInspector
      v-if="interactive && inspectorEl && inspectorPos"
      :element="inspectorEl"
      :connection-id="config.connection_id"
      :targets="connectorTargets"
      :style="{ left: inspectorPos.x + 'px', top: inspectorPos.y + 'px' }"
      class="pres__inspector"
      :class="{ 'pres__inspector--below': inspectorPos.below }"
      @patch="onInspectorPatch"
      @delete="deleteSelected"
      @duplicate="duplicateSelected"
    />

    <div
      v-if="interactive && layersOpen"
      v-click-outside="closeLayers"
      class="pres__layers"
      @pointerdown.stop
    >
      <div class="pres__layers-head">
        <span>{{ _t('Layers') }}</span>
        <button class="pres__layers-x" @click="layersOpen = false">×</button>
      </div>
      <div class="pres__layers-hint">{{ _t('Shift-click to select multiple') }}</div>
      <div
        v-for="el in layersList"
        :key="el.id"
        class="pres__layer"
        :class="{
          'pres__layer--sel': selectedIds.includes(el.id),
          'pres__layer--hidden': el.hidden
        }"
        @click="onLayerClick(el.id, $event)"
      >
        <span class="pres__layer-name">{{ layerName(el) }}</span>
        <button
          class="pres__layer-btn"
          :class="{ 'pres__layer-btn--on': el.locked }"
          :title="el.locked ? _t('Unlock') : _t('Lock')"
          @click.stop="toggleLock(el.id)"
        >
          <span v-html="el.locked ? ICONS.lock : ICONS.unlock" />
        </button>
        <button
          class="pres__layer-btn"
          :class="{ 'pres__layer-btn--on': el.hidden }"
          :title="el.hidden ? _t('Show') : _t('Hide')"
          @click.stop="toggleHidden(el.id)"
        >
          <span v-html="el.hidden ? ICONS.eyeOff : ICONS.eye" />
        </button>
      </div>
      <div class="pres__layers-foot">
        <button
          class="pres__layer-action"
          :disabled="selectedIds.length < 2"
          @click="groupSelected"
        >
          {{ _t('Group') }}
        </button>
        <button class="pres__layer-action" :disabled="!hasGroupSelected" @click="ungroupSelected">
          {{ _t('Ungroup') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { boardsApi } from '@/api/client'
import { useHistory } from '@/composables/useHistory'
import { useMarquee } from '@/composables/useMarquee'
import { usePresentationSelectionGeometry } from '@/composables/usePresentationSelectionGeometry'
import { useSlideViewport } from '@/composables/useSlideViewport'
import { type Box, type Guide, computeSmartGuides } from '@/composables/useSmartGuides'
import { useAuthStore } from '@/stores/auth'
import { useBoardsStore } from '@/stores/boards'
import type {
  BoardConfig,
  ObjectState,
  PresentationElement,
  PresentationView,
  ShapeElement
} from '@/types/api'
import { type GroupMember, applyGroupDelta } from '@/utils/groupDrag'
import { ICONS, SLIDE_PRESETS } from '@/utils/presentationCanvasChrome'
import {
  type InsertKind,
  createElement,
  newElementId,
  resolveImageRef
} from '@/utils/presentationElements'
import { themeOptions, themeTokens } from '@/utils/presentationThemes'
import usei18n from '@/vendor/cmk/lib/i18n'
import useClickOutside from '@/vendor/cmk/lib/useClickOutside'

import ImagePicker from '../ImagePicker.vue'
import ColorField from './ColorField.vue'
import PresentationConnector from './PresentationConnector.vue'
import PresentationElementView from './PresentationElementView.vue'
import PresentationInspector from './PresentationInspector.vue'

const { _t } = usei18n()

const props = defineProps<{
  config: BoardConfig
  states: Record<string, ObjectState>
  editMode: boolean
  readonly?: boolean
  preview?: boolean
  kiosk?: boolean
}>()

const auth = useAuthStore()
const boardsStore = useBoardsStore()
const vClickOutside = useClickOutside()

// JSON clone (not structuredClone): the view is pure JSON, and structuredClone
// throws DataCloneError on Vue reactive proxies.
function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v))
}

function initialView(): PresentationView {
  const v = props.config.view
  if (v.type === 'presentation') return clone(v)
  return { type: 'presentation', width: 1920, height: 1080, theme: 'midnight', elements: [] }
}

const local = ref<PresentationView>(initialView())
const version = ref(props.config.version ?? 0)
const interactive = computed(
  () => props.editMode && !props.readonly && !props.preview && !props.kiosk
)

watch(
  () => props.config.name,
  () => {
    local.value = initialView()
    version.value = props.config.version ?? 0
    selectedIds.value = []
    history.reset()
  }
)

const containerRef = ref<HTMLElement | null>(null)
const slideW = computed(() => local.value.width)
const slideH = computed(() => local.value.height)
const { scale, offsetX, offsetY, screenToSlide } = useSlideViewport(containerRef, slideW, slideH)

const themeVars = computed(() => themeTokens(local.value.theme))
const stageStyle = computed(() => ({
  ...themeVars.value,
  position: 'absolute' as const,
  left: `${offsetX.value}px`,
  top: `${offsetY.value}px`,
  width: `${slideW.value}px`,
  height: `${slideH.value}px`,
  transform: `scale(${scale.value})`,
  transformOrigin: 'top left'
}))
// Slide background: an optional image (image-store filename or external URL)
// layered over the chosen color (or the theme's default when unset).
const bgStyle = computed(() => {
  const color = local.value.background || 'var(--pres-bg)'
  const url = resolveImageRef(local.value.background_image)
  if (!url) return { background: color }
  return {
    backgroundColor: color,
    backgroundImage: `url("${url}")`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat'
  }
})
const overlaySvgStyle = computed(() => ({
  width: `${slideW.value}px`,
  height: `${slideH.value}px`
}))

const selectedIds = ref<string[]>([])
const editingTextId = ref<string | null>(null)

const elements = computed(() => local.value.elements)

// Top-level elements are everything not referenced as a group child.
const childToGroup = computed(() => {
  const map = new Map<string, string>()
  for (const el of elements.value) {
    if (el.kind === 'group') for (const c of el.children) map.set(c, el.id)
  }
  return map
})
function topLevelId(id: string): string {
  return childToGroup.value.get(id) ?? id
}

const orderedElements = computed(() =>
  [...elements.value].filter((e) => !e.hidden || interactive.value).sort((a, b) => a.z - b.z)
)

const layersList = computed(() =>
  [...elements.value].sort((a, b) => b.z - a.z).filter((e) => !childToGroup.value.has(e.id))
)

function byId(id: string | undefined): PresentationElement | undefined {
  return id ? elements.value.find((e) => e.id === id) : undefined
}
const selectedElements = computed(() =>
  selectedIds.value.map(byId).filter((e): e is PresentationElement => !!e)
)
const primaryLocked = computed(() => selectedElements.value.some((e) => e.locked))
const hasGroupSelected = computed(() => selectedElements.value.some((e) => e.kind === 'group'))

// ── Connectors (line + arrow shapes) ────────────────────────────────────────
// Every line/arrow renders in a slide-space overlay (any angle) instead of
// inline, so its endpoints can be dragged freely and docked to other elements.
function centerOf(id: string | null | undefined): { x: number; y: number } | null {
  const el = byId(id ?? undefined)
  if (!el) return null
  return { x: el.x + el.w / 2, y: el.y + el.h / 2 }
}
function isConnectorShape(el: PresentationElement): el is ShapeElement {
  return el.kind === 'shape' && (el.shape === 'line' || el.shape === 'arrow')
}
// Free endpoints are the box's opposite corners (so an arbitrary-angle line is
// representable); a docked endpoint follows the referenced element's centre.
function connectorEndpoints(el: ShapeElement): {
  start: { x: number; y: number }
  end: { x: number; y: number }
} {
  const start = centerOf(el.start_ref) ?? { x: el.x, y: el.y }
  const end = centerOf(el.end_ref) ?? { x: el.x + el.w, y: el.y + el.h }
  return { start, end }
}
function isDocked(el: ShapeElement): boolean {
  return !!(centerOf(el.start_ref) || centerOf(el.end_ref))
}
const connectorIds = computed(
  () => new Set(elements.value.filter(isConnectorShape).map((e) => e.id))
)
const connectors = computed(() =>
  [...elements.value]
    .filter((e): e is ShapeElement => isConnectorShape(e))
    .filter((e) => !e.hidden || interactive.value)
    .sort((a, b) => a.z - b.z)
    .map((el) => ({ el, ...connectorEndpoints(el) }))
)
// Elements rendered inline in the main layer: everything except connectors.
const inlineElements = computed(() =>
  orderedElements.value.filter((e) => !connectorIds.value.has(e.id))
)
// Connectable endpoint targets handed to the inspector (named, non-self, non-group).
const connectorTargets = computed(() =>
  elements.value.filter((e) => e.kind !== 'group').map((e) => ({ id: e.id, name: layerName(e) }))
)

function stateFor(el: PresentationElement): ObjectState | undefined {
  // Data elements and monitoring-bound shapes both receive states keyed by id.
  return el.kind === 'data' || el.kind === 'shape' ? props.states[el.id] : undefined
}

function elementStyle(el: PresentationElement): Record<string, string> {
  return {
    left: `${el.x}px`,
    top: `${el.y}px`,
    width: `${el.w}px`,
    height: `${el.h}px`,
    opacity: String(el.opacity),
    transform: el.rotation ? `rotate(${el.rotation}deg)` : 'none',
    zIndex: String(el.z),
    pointerEvents: !interactive.value || el.locked ? 'none' : 'auto'
  }
}

const history = useHistory<PresentationElement[]>(
  (els) => JSON.stringify(els),
  (s) => JSON.parse(s)
)
function snapshot(): void {
  history.record(clone(elements.value))
}

let saveTimer: ReturnType<typeof setTimeout> | null = null
const saving = ref(false)
const savedAt = ref(false)
const saveLabel = computed(() => (saving.value ? _t('Saving…') : savedAt.value ? _t('Saved') : ''))

function scheduleSave(): void {
  savedAt.value = false
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(saveNow, 400)
}

async function saveNow(): Promise<void> {
  if (!auth.accessToken) return
  const name = props.config.name
  saving.value = true
  try {
    const payload = { view: clone(local.value) }
    const cfg = await boardsApi.update(name, payload, auth.accessToken, version.value)
    version.value = cfg.version ?? version.value
    if (boardsStore.currentBoard?.name === cfg.name) {
      boardsStore.currentBoard.version = cfg.version ?? 0
      boardsStore.currentBoard.view = cfg.view
    }
    savedAt.value = true
  } catch {
    // Version conflict or transient error: realign to the canonical version
    // without tearing the working copy down (fetchBoard nulls currentBoard,
    // which would unmount this component and drop in-progress edits).
    try {
      const cfg = await boardsApi.get(name, auth.accessToken)
      version.value = cfg.version ?? 0
    } catch {
      /* leave version as-is; the next edit retries */
    }
  } finally {
    saving.value = false
  }
}

function mutate(fn: () => void): void {
  snapshot()
  fn()
  scheduleSave()
}
function setElements(next: PresentationElement[]): void {
  local.value = { ...local.value, elements: next }
}

const marquee = useMarquee(4)
const marqueeStyle = computed(() => ({
  left: `${marquee.rect.value.left}px`,
  top: `${marquee.rect.value.top}px`,
  width: `${marquee.rect.value.width}px`,
  height: `${marquee.rect.value.height}px`
}))

interface DragState {
  mode: 'none' | 'move' | 'resize' | 'rotate' | 'marquee' | 'endpoint'
  handle: string
  start: { x: number; y: number }
  members: GroupMember[]
  grabbedInit: { x: number; y: number }
  origin: { x: number; y: number; w: number; h: number; rotation: number }
  recorded: boolean
  // Endpoint drag: which end of which connector, and the fixed other endpoint.
  endpoint?: 'start' | 'end' | null
  otherEnd?: { x: number; y: number }
}
const drag = ref<DragState>({
  mode: 'none',
  handle: '',
  start: { x: 0, y: 0 },
  members: [],
  grabbedInit: { x: 0, y: 0 },
  origin: { x: 0, y: 0, w: 0, h: 0, rotation: 0 },
  recorded: false
})
const activeGuides = ref<Guide[]>([])
// While dragging a connector endpoint, the element it would dock to on release.
const dockCandidateId = ref<string | null>(null)
const dockCandidate = computed(() => {
  const el = byId(dockCandidateId.value ?? undefined)
  return el ? { x: el.x, y: el.y, w: el.w, h: el.h } : null
})

function selectOne(id: string): void {
  selectedIds.value = [id]
}

function onStagePointerDown(e: PointerEvent): void {
  if (!interactive.value) return
  editingTextId.value = null
  // A pointer-down on the bare canvas gutter (the area around the slide, not an
  // element, panel, or HUD control — those stop propagation or are child nodes)
  // deselects, which closes the inspector. Without this, only clicks that land
  // on the slide itself would dismiss it.
  if (e.target === containerRef.value) selectedIds.value = []
}

function onSlidePointerDown(e: PointerEvent): void {
  if (!interactive.value) return
  // A click on the slide ends any in-progress text edit (the contenteditable's
  // blur commits it) and clears the selection, dismissing the inspector. The
  // element being edited swallows its own pointer events, so reaching here
  // always means the click landed outside it.
  editingTextId.value = null
  selectedIds.value = []
  const p = screenToSlide(e.clientX, e.clientY)
  marquee.begin(p.x, p.y, e.shiftKey)
  drag.value.mode = 'marquee'
  ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
}

function onElementPointerDown(el: PresentationElement, e: PointerEvent): void {
  if (!interactive.value || el.locked) return
  // Selecting another element ends an in-progress text edit (blur commits it).
  // The element being edited stops its own pointer events, so this never fires
  // for the element currently being edited.
  editingTextId.value = null
  const tid = topLevelId(el.id)
  if (e.shiftKey) {
    selectedIds.value = selectedIds.value.includes(tid)
      ? selectedIds.value.filter((i) => i !== tid)
      : [...selectedIds.value, tid]
  } else if (!selectedIds.value.includes(tid)) {
    selectedIds.value = [tid]
  }
  beginMove(e)
  ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
}

// A connector lives in the overlay, not the inline element layer, so it gets its
// own pointer handler. Stop propagation so the stage's deselect doesn't fire.
// A fully free connector (no docked end) can still be dragged by its body.
function onConnectorPointerDown(el: ShapeElement, e: PointerEvent): void {
  if (!interactive.value || el.locked) return
  e.stopPropagation()
  editingTextId.value = null
  selectedIds.value = [el.id]
  if (!isDocked(el)) beginMove(e)
}

// Topmost dockable element under a slide point (not the connector itself, not
// another line/arrow, not a group).
function elementAt(p: { x: number; y: number }, excludeId: string): string | null {
  const hit = [...elements.value]
    .filter(
      (e) =>
        e.id !== excludeId &&
        e.kind !== 'group' &&
        !isConnectorShape(e) &&
        !childToGroup.value.has(e.id) &&
        p.x >= e.x &&
        p.x <= e.x + e.w &&
        p.y >= e.y &&
        p.y <= e.y + e.h
    )
    .sort((a, b) => b.z - a.z)[0]
  return hit?.id ?? null
}

// Grab a connector endpoint to drag it: dropping it on an element docks that
// end; dropping it on empty canvas leaves it free at the release position.
function onEndpointPointerDown(el: ShapeElement, which: 'start' | 'end', e: PointerEvent): void {
  if (!interactive.value || el.locked) return
  e.stopPropagation()
  selectedIds.value = [el.id]
  const { start, end } = connectorEndpoints(el)
  drag.value = {
    mode: 'endpoint',
    handle: '',
    start: { x: 0, y: 0 },
    members: [],
    grabbedInit: { x: 0, y: 0 },
    origin: { x: 0, y: 0, w: 0, h: 0, rotation: 0 },
    recorded: false,
    endpoint: which,
    otherEnd: which === 'start' ? end : start
  }
  ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
}

function moveEndpoint(p: { x: number; y: number }): void {
  const el = byId(selectedIds.value[0])
  if (!el || !isConnectorShape(el)) return
  const candidate = elementAt(p, el.id)
  dockCandidateId.value = candidate
  const target = candidate ? (centerOf(candidate) ?? p) : p
  const other = drag.value.otherEnd ?? p
  // Lay the box so its two corners are the (fixed) other endpoint and the
  // dragged target; clear this end's dock ref so the corner drives it live.
  if (drag.value.endpoint === 'start') {
    el.x = target.x
    el.y = target.y
    el.w = other.x - target.x
    el.h = other.y - target.y
    el.start_ref = null
  } else {
    el.x = other.x
    el.y = other.y
    el.w = target.x - other.x
    el.h = target.y - other.y
    el.end_ref = null
  }
}

// Elements that physically move when the selection is dragged (selected
// top-level elements plus the children of any selected group).
function movingIds(): string[] {
  const ids = new Set(selectedIds.value)
  for (const id of selectedIds.value) {
    const el = byId(id)
    if (el?.kind === 'group') for (const c of el.children) ids.add(c)
  }
  return [...ids]
}

function beginMove(e: PointerEvent): void {
  const p = screenToSlide(e.clientX, e.clientY)
  const ids = movingIds()
  const grabbed = byId(selectedIds.value[0])
  drag.value = {
    mode: 'move',
    handle: '',
    start: p,
    grabbedInit: grabbed ? { x: grabbed.x, y: grabbed.y } : { x: 0, y: 0 },
    members: ids
      .filter((i) => i !== selectedIds.value[0])
      .map((i) => {
        const el = byId(i)!
        return { id: i, init: [el.x, el.y] as [number, number] }
      }),
    origin: { x: 0, y: 0, w: 0, h: 0, rotation: 0 },
    recorded: false
  }
}

function onHandlePointerDown(handle: string, e: PointerEvent): void {
  const el = byId(selectedIds.value[0])
  if (!el) return
  drag.value = {
    mode: 'resize',
    handle,
    start: screenToSlide(e.clientX, e.clientY),
    members: [],
    grabbedInit: { x: 0, y: 0 },
    origin: { x: el.x, y: el.y, w: el.w, h: el.h, rotation: el.rotation },
    recorded: false
  }
  ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
}

function onRotatePointerDown(e: PointerEvent): void {
  const el = byId(selectedIds.value[0])
  if (!el) return
  drag.value = {
    mode: 'rotate',
    handle: '',
    start: screenToSlide(e.clientX, e.clientY),
    members: [],
    grabbedInit: { x: 0, y: 0 },
    origin: { x: el.x, y: el.y, w: el.w, h: el.h, rotation: el.rotation },
    recorded: false
  }
  ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
}

function onPointerMove(e: PointerEvent): void {
  const d = drag.value
  if (d.mode === 'none') return
  const p = screenToSlide(e.clientX, e.clientY)

  if (d.mode === 'marquee') {
    marquee.update(p.x, p.y)
    applyMarquee()
    return
  }
  if (!d.recorded) {
    snapshot()
    d.recorded = true
  }
  if (d.mode === 'move') moveBy(p, e.shiftKey)
  else if (d.mode === 'resize') resizeBy(p, e.shiftKey)
  else if (d.mode === 'rotate') rotateBy(p, e.shiftKey)
  else if (d.mode === 'endpoint') moveEndpoint(p)
}

function moveBy(p: { x: number; y: number }, _shift: boolean): void {
  const grabbed = byId(selectedIds.value[0])
  if (!grabbed) return
  let nx = drag.value.grabbedInit.x + (p.x - drag.value.start.x)
  let ny = drag.value.grabbedInit.y + (p.y - drag.value.start.y)

  // Smart guides: snap the grabbed element's box to its neighbours.
  const others = elements.value
    .filter((e) => !movingIds().includes(e.id) && e.kind !== 'group')
    .map((e) => ({ x: e.x, y: e.y, w: e.w, h: e.h }) as Box)
  const box: Box = { x: nx, y: ny, w: grabbed.w, h: grabbed.h }
  const g = computeSmartGuides(box, others)
  nx += g.dx
  ny += g.dy
  activeGuides.value = g.guides

  const dx = nx - drag.value.grabbedInit.x
  const dy = ny - drag.value.grabbedInit.y
  grabbed.x = nx
  grabbed.y = ny
  const moved = applyGroupDelta(drag.value.members, [dx, dy])
  for (const [id, [mx, my]] of moved) {
    const el = byId(id)
    if (el) {
      el.x = mx
      el.y = my
    }
  }
}

function resizeBy(p: { x: number; y: number }, shift: boolean): void {
  const el = byId(selectedIds.value[0])
  if (!el) return
  const o = drag.value.origin
  // Project the pointer delta onto the element's local axes so a rotated
  // element resizes along its own edges, not the slide's.
  const rdx = p.x - drag.value.start.x
  const rdy = p.y - drag.value.start.y
  const a = (-(o.rotation || 0) * Math.PI) / 180
  const dx = rdx * Math.cos(a) - rdy * Math.sin(a)
  const dy = rdx * Math.sin(a) + rdy * Math.cos(a)
  const h = drag.value.handle
  let x = o.x
  let y = o.y
  let w = o.w
  let hh = o.h
  if (h.includes('e')) w = o.w + dx
  if (h.includes('s')) hh = o.h + dy
  if (h.includes('w')) {
    w = o.w - dx
    x = o.x + dx
  }
  if (h.includes('n')) {
    hh = o.h - dy
    y = o.y + dy
  }
  const MIN = 8
  if (w < MIN) w = MIN
  if (hh < MIN) hh = MIN
  if (shift && o.w > 0 && o.h > 0) {
    const ratio = o.w / o.h
    if (Math.abs(dx) > Math.abs(dy)) hh = w / ratio
    else w = hh * ratio
  }
  el.x = x
  el.y = y
  el.w = w
  el.h = hh
}

function rotateBy(p: { x: number; y: number }, shift: boolean): void {
  const el = byId(selectedIds.value[0])
  if (!el) return
  const o = drag.value.origin
  const cx = o.x + o.w / 2
  const cy = o.y + o.h / 2
  let deg = (Math.atan2(p.y - cy, p.x - cx) * 180) / Math.PI + 90
  if (shift) deg = Math.round(deg / 15) * 15
  el.rotation = Math.round(deg)
}

function onPointerUp(): void {
  const d = drag.value
  if (d.mode === 'marquee') marquee.reset()
  // Endpoint released over an element → dock that end to it.
  if (d.mode === 'endpoint' && dockCandidateId.value) {
    const el = byId(selectedIds.value[0])
    if (el && isConnectorShape(el)) {
      if (d.endpoint === 'start') el.start_ref = dockCandidateId.value
      else el.end_ref = dockCandidateId.value
    }
  }
  dockCandidateId.value = null
  activeGuides.value = []
  if (d.recorded) scheduleSave()
  drag.value.mode = 'none'
}

function applyMarquee(): void {
  const r = marquee.rect.value
  const hits = elements.value
    .filter((e) => !childToGroup.value.has(e.id))
    .filter(
      (e) =>
        e.x < r.left + r.width && e.x + e.w > r.left && e.y < r.top + r.height && e.y + e.h > r.top
    )
    .map((e) => e.id)
  selectedIds.value = marquee.additive.value ? [...new Set([...selectedIds.value, ...hits])] : hits
}

// Read-only overlay geometry (selection box, handle styles, inspector anchor).
const {
  selectionBox,
  singleIsConnector,
  selBoxStyle,
  handles,
  handleStyle,
  rotateHandleStyle,
  inspectorEl,
  inspectorPos
} = usePresentationSelectionGeometry({
  selectedIds: () => selectedIds.value,
  selectedElements: () => selectedElements.value,
  scale: () => scale.value,
  offsetX: () => offsetX.value,
  offsetY: () => offsetY.value,
  connectorEndpoints,
  isConnectorShape
})

function onInspectorPatch(patch: Record<string, unknown>): void {
  const el = inspectorEl.value
  if (!el) return
  mutate(() => Object.assign(el, patch))
}

const nextZ = computed(() => elements.value.reduce((m, e) => Math.max(m, e.z), 0) + 1)
function insert(kind: InsertKind): void {
  const cx = slideW.value / 2 - 100 + (elements.value.length % 6) * 16
  const cy = slideH.value / 2 - 70 + (elements.value.length % 6) * 16
  const el = createElement(kind, Math.round(cx), Math.round(cy))
  el.z = nextZ.value
  mutate(() => setElements([...elements.value, el]))
  selectedIds.value = [el.id]
  if (kind === 'text') editingTextId.value = el.id
}

function deleteSelected(): void {
  if (!selectedIds.value.length) return
  const remove = new Set(movingIds())
  mutate(() => setElements(elements.value.filter((e) => !remove.has(e.id))))
  selectedIds.value = []
}

// Snapshot a selection for clone/clipboard: the selected top-level elements
// plus any group's children, so groups duplicate as a self-contained unit.
function collectWithChildren(topIds: string[]): { els: PresentationElement[]; tops: string[] } {
  const seen = new Set<string>()
  const els: PresentationElement[] = []
  const walk = (id: string): void => {
    if (seen.has(id)) return
    seen.add(id)
    const el = byId(id)
    if (!el) return
    els.push(clone(el))
    if (el.kind === 'group') el.children.forEach(walk)
  }
  topIds.forEach(walk)
  return { els, tops: topIds.filter((id) => byId(id)) }
}

// Re-id a snapshot (fresh ids, remapped group children), offset it, and stack
// it on top. Returns the copies plus the new ids of the formerly-top elements.
function instantiate(src: { els: PresentationElement[]; tops: string[] }): {
  copies: PresentationElement[]
  newTops: string[]
} {
  const idMap = new Map<string, string>()
  const copies = src.els.map((el) => {
    const c = clone(el)
    c.id = newElementId(el.kind)
    idMap.set(el.id, c.id)
    return c
  })
  copies.forEach((c, i) => {
    c.x += 24
    c.y += 24
    c.z = nextZ.value + i
    if (c.kind === 'group') c.children = c.children.map((ch) => idMap.get(ch) ?? ch)
  })
  const newTops = src.tops.map((id) => idMap.get(id)).filter((x): x is string => !!x)
  return { copies, newTops }
}

function duplicateSelected(): void {
  if (!selectedIds.value.length) return
  const { copies, newTops } = instantiate(collectWithChildren(selectedIds.value))
  mutate(() => setElements([...elements.value, ...copies]))
  selectedIds.value = newTops
}

let clipboard: { els: PresentationElement[]; tops: string[] } = { els: [], tops: [] }
function copySelected(): void {
  clipboard = collectWithChildren(selectedIds.value)
}
function paste(): void {
  if (!clipboard.els.length) return
  const { copies, newTops } = instantiate(clipboard)
  mutate(() => setElements([...elements.value, ...copies]))
  selectedIds.value = newTops
}

function onSlideDblClick(e: MouseEvent): void {
  if (!interactive.value) return
  const p = screenToSlide(e.clientX, e.clientY)
  const hit = [...orderedElements.value]
    .reverse()
    .find((el) => p.x >= el.x && p.x <= el.x + el.w && p.y >= el.y && p.y <= el.y + el.h)
  if (hit && hit.kind === 'text') {
    selectedIds.value = [hit.id]
    editingTextId.value = hit.id
  }
}
function onTextChange(id: string, text: string): void {
  const el = byId(id)
  if (!el || el.kind !== 'text') return
  // Blur always reports the text so editing reliably ends; only record a
  // history step + save when it actually changed (a no-op blur mustn't spam
  // undo or saves).
  if (text !== el.text) {
    mutate(() => {
      el.text = text
    })
  }
  editingTextId.value = null
}

function alignTo(fn: (e: PresentationElement, b: Box) => void): void {
  const b = selectionBox.value
  if (!b) return
  mutate(() => selectedElements.value.forEach((e) => fn(e, b)))
}
function distribute(axis: 'x' | 'y'): void {
  const els = [...selectedElements.value].sort((a, b) => (axis === 'x' ? a.x - b.x : a.y - b.y))
  const head = els[0]
  const tail = els[els.length - 1]
  if (els.length < 3 || !head || !tail) return
  const sizeKey = axis === 'x' ? 'w' : 'h'
  const posKey = axis
  const first = head[posKey]
  const last = tail[posKey] + tail[sizeKey]
  const total = els.reduce((s, e) => s + e[sizeKey], 0)
  const gap = (last - first - total) / (els.length - 1)
  let cursor = first
  mutate(() =>
    els.forEach((e) => {
      e[posKey] = Math.round(cursor)
      cursor += e[sizeKey] + gap
    })
  )
}
const alignActions = computed(() => [
  {
    id: 'l',
    title: _t('Align left'),
    icon: ICONS.alignL,
    run: () => alignTo((e, b) => (e.x = b.x))
  },
  {
    id: 'c',
    title: _t('Align center'),
    icon: ICONS.alignC,
    run: () => alignTo((e, b) => (e.x = b.x + b.w / 2 - e.w / 2))
  },
  {
    id: 'r',
    title: _t('Align right'),
    icon: ICONS.alignR,
    run: () => alignTo((e, b) => (e.x = b.x + b.w - e.w))
  },
  {
    id: 't',
    title: _t('Align top'),
    icon: ICONS.alignT,
    run: () => alignTo((e, b) => (e.y = b.y))
  },
  {
    id: 'm',
    title: _t('Align middle'),
    icon: ICONS.alignM,
    run: () => alignTo((e, b) => (e.y = b.y + b.h / 2 - e.h / 2))
  },
  {
    id: 'b',
    title: _t('Align bottom'),
    icon: ICONS.alignB,
    run: () => alignTo((e, b) => (e.y = b.y + b.h - e.h))
  },
  { id: 'dx', title: _t('Distribute horizontally'), icon: ICONS.distH, run: () => distribute('x') },
  { id: 'dy', title: _t('Distribute vertically'), icon: ICONS.distV, run: () => distribute('y') }
])

const layersOpen = ref(false)
// Plain click selects a single layer; Shift/Ctrl/Cmd toggles it in/out of the
// current selection so the operator can build a multi-selection to Group.
function onLayerClick(id: string, e: MouseEvent): void {
  if (e.shiftKey || e.ctrlKey || e.metaKey) {
    selectedIds.value = selectedIds.value.includes(id)
      ? selectedIds.value.filter((i) => i !== id)
      : [...selectedIds.value, id]
  } else {
    selectOne(id)
  }
}
function layerName(el: PresentationElement): string {
  if (el.name) return el.name
  if (el.kind === 'text') return el.text.slice(0, 18) || _t('Text')
  if (el.kind === 'data') return el.label?.text || el.host_name || _t('Data')
  if (el.kind === 'group') return _t('Group')
  if (el.kind === 'shape') return el.shape.charAt(0).toUpperCase() + el.shape.slice(1)
  return el.kind
}
function toggleLock(id: string): void {
  const el = byId(id)
  if (el) mutate(() => (el.locked = !el.locked))
}
function toggleHidden(id: string): void {
  const el = byId(id)
  if (el) mutate(() => (el.hidden = !el.hidden))
}
function groupSelected(): void {
  if (selectedIds.value.length < 2) return
  const b = selectionBox.value!
  const group: PresentationElement = {
    id: newElementId('group'),
    kind: 'group',
    x: b.x,
    y: b.y,
    w: b.w,
    h: b.h,
    rotation: 0,
    z: nextZ.value,
    opacity: 1,
    locked: false,
    hidden: false,
    name: null,
    children: [...selectedIds.value]
  }
  mutate(() => setElements([...elements.value, group]))
  selectedIds.value = [group.id]
}
function ungroupSelected(): void {
  const groups = selectedElements.value.filter((e) => e.kind === 'group').map((e) => e.id)
  if (!groups.length) return
  mutate(() => setElements(elements.value.filter((e) => !groups.includes(e.id))))
  selectedIds.value = []
}

const settingsOpen = ref(false)
// Opening one floating panel closes the other so they never overlap; both
// also close on an outside click (v-click-outside).
function toggleSettings(): void {
  settingsOpen.value = !settingsOpen.value
  if (settingsOpen.value) layersOpen.value = false
}
function toggleLayers(): void {
  layersOpen.value = !layersOpen.value
  if (layersOpen.value) settingsOpen.value = false
}
function closeSettings(): void {
  settingsOpen.value = false
}
function closeLayers(): void {
  layersOpen.value = false
}
const slidePresets = SLIDE_PRESETS
function numVal(e: Event): number {
  return Number((e.target as HTMLInputElement).value)
}
// Slide-level changes (theme/size/background) are board metadata, not element
// edits, so they save without touching the element undo history.
function onSlideMetaChange(): void {
  scheduleSave()
}
function setSlideSize(w: number, h: number): void {
  const cw = Math.min(8192, Math.max(320, Math.round(w) || local.value.width))
  const ch = Math.min(8192, Math.max(320, Math.round(h) || local.value.height))
  local.value = { ...local.value, width: cw, height: ch }
  scheduleSave()
}
function applyPreset(w: number, h: number): void {
  setSlideSize(w, h)
}
function setBackground(color: string | null): void {
  local.value = { ...local.value, background: color }
  scheduleSave()
}
function setBackgroundImage(name: string): void {
  local.value = { ...local.value, background_image: name || null }
  scheduleSave()
}

// Arrow-key nudge of the selection (1px, 10px with Shift) — a design-tool staple.
// Held repeats coalesce into one undo step (like a drag), and an all-locked
// selection is a no-op so it can't spam empty history entries.
let lastNudgeAt = 0
function nudge(dx: number, dy: number): void {
  const movable = movingIds()
    .map(byId)
    .filter((e): e is PresentationElement => !!e && !e.locked)
  if (!movable.length) return
  const now = Date.now()
  if (now - lastNudgeAt > 600) snapshot()
  lastNudgeAt = now
  for (const el of movable) {
    el.x += dx
    el.y += dy
  }
  scheduleSave()
}

function undo(): void {
  const restored = history.undo(clone(elements.value))
  if (restored) {
    setElements(restored)
    scheduleSave()
  }
}
function redo(): void {
  const restored = history.redo(clone(elements.value))
  if (restored) {
    setElements(restored)
    scheduleSave()
  }
}

// True while a form control (inspector field, etc.) has focus, so canvas
// shortcuts don't hijack typing — Backspace must edit text, not delete elements.
function isTypingTarget(): boolean {
  const el = document.activeElement as HTMLElement | null
  if (!el) return false
  return (
    el.tagName === 'INPUT' ||
    el.tagName === 'TEXTAREA' ||
    el.tagName === 'SELECT' ||
    el.isContentEditable
  )
}

function onKey(e: KeyboardEvent): void {
  if (!interactive.value || editingTextId.value || isTypingTarget()) return
  const meta = e.ctrlKey || e.metaKey
  if (meta && e.key.toLowerCase() === 'z') {
    e.preventDefault()
    if (e.shiftKey) redo()
    else undo()
  } else if (meta && e.key.toLowerCase() === 'y') {
    e.preventDefault()
    redo()
  } else if (meta && e.key.toLowerCase() === 'c') {
    copySelected()
  } else if (meta && e.key.toLowerCase() === 'v') {
    e.preventDefault()
    paste()
  } else if (meta && e.key.toLowerCase() === 'd') {
    e.preventDefault()
    duplicateSelected()
  } else if ((e.key === 'Delete' || e.key === 'Backspace') && selectedIds.value.length) {
    e.preventDefault()
    deleteSelected()
  } else if (e.key.startsWith('Arrow') && selectedIds.value.length) {
    e.preventDefault()
    const s = e.shiftKey ? 10 : 1
    if (e.key === 'ArrowLeft') nudge(-s, 0)
    else if (e.key === 'ArrowRight') nudge(s, 0)
    else if (e.key === 'ArrowUp') nudge(0, -s)
    else if (e.key === 'ArrowDown') nudge(0, s)
  } else if (e.key === 'Escape') {
    selectedIds.value = []
    editingTextId.value = null
  }
}

onMounted(() => {
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('keydown', onKey)
  if (saveTimer) clearTimeout(saveTimer)
})

const themeChoices = themeOptions()
type PaletteTool = { kind: InsertKind; title: string; icon: string }
// Lead with the monitoring operator's primary content — live status and text —
// then the decorative shapes and image.
const contentTools: PaletteTool[] = [
  { kind: 'data', title: _t('Live status'), icon: ICONS.data },
  { kind: 'text', title: _t('Text'), icon: ICONS.text }
]
const shapeTools: PaletteTool[] = [
  { kind: 'rect', title: _t('Rectangle'), icon: ICONS.rect },
  { kind: 'ellipse', title: _t('Ellipse'), icon: ICONS.ellipse },
  { kind: 'line', title: _t('Line'), icon: ICONS.line },
  { kind: 'arrow', title: _t('Arrow'), icon: ICONS.arrow },
  { kind: 'image', title: _t('Image'), icon: ICONS.image }
]
</script>

<style scoped>
.pres {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background:
    repeating-conic-gradient(rgb(128 128 128 / 7%) 0% 25%, transparent 0% 50%) 50% / 22px 22px,
    var(--bg, #0f1117);
}

.pres__stage {
  box-shadow: 0 12px 48px rgb(0 0 0 / 50%);
  user-select: none;
}

.pres__bg {
  position: absolute;
  inset: 0;
}

.pres__empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--pres-muted, #7c89a8);
  font-family: var(--pres-font, sans-serif);
  font-size: 28px;
  letter-spacing: 0.02em;
  pointer-events: none;
}

.pres__el {
  position: absolute;
  transform-origin: center center;
}

.pres__el--selected {
  cursor: move;
}

.pres__el--locked {
  cursor: default;
}

/* Hidden elements stay visible while editing (so they remain reachable) but
   dimmed + checkered, making a Hide toggle visibly take effect. They vanish
   entirely outside edit mode via the orderedElements filter. */
.pres__el--hidden {
  opacity: 0.3 !important;
}

.pres__guides {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: visible;
}

/* Connector layer sits above the background but below the element boxes. The
   svg itself ignores pointer events; each connector re-enables them on its own
   hit line, so clicks elsewhere fall through to the stage. */
.pres__connectors {
  position: absolute;
  inset: 0;
  overflow: visible;
  pointer-events: none;
}

.pres__dock-target {
  fill: color-mix(in srgb, var(--accent, #15d1a0) 14%, transparent);
  stroke: var(--accent, #15d1a0);
  pointer-events: none;
}

.pres__sel {
  position: absolute;
  outline: solid var(--accent, #15d1a0);
  pointer-events: none;
}

.pres__handle {
  position: absolute;
  background: rgb(255 255 255);
  border: solid var(--accent, #15d1a0);
  border-radius: 2px;
  box-shadow: 0 0 0 1px rgb(0 0 0 / 25%);
  pointer-events: auto;
}

.pres__handle--nw,
.pres__handle--se {
  cursor: nwse-resize;
}

.pres__handle--ne,
.pres__handle--sw {
  cursor: nesw-resize;
}

.pres__handle--n,
.pres__handle--s {
  cursor: ns-resize;
}

.pres__handle--e,
.pres__handle--w {
  cursor: ew-resize;
}

.pres__rotate {
  position: absolute;
  background: rgb(255 255 255);
  border: solid var(--accent, #15d1a0);
  border-radius: 9999px;
  box-shadow: 0 0 0 1px rgb(0 0 0 / 25%);
  cursor: grab;
  pointer-events: auto;
}

.pres__marquee {
  position: absolute;
  background: color-mix(in srgb, var(--accent, #15d1a0) 12%, transparent);
  border: 1px solid var(--accent, #15d1a0);
  pointer-events: none;
}

.pres__palette,
.pres__align {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 4px;
  padding: 5px;
  border-radius: 10px;
  background: var(--bg-surface, #1b1f2a);
  border: 1px solid var(--border, rgb(255 255 255 / 8%));
  box-shadow: 0 8px 24px rgb(0 0 0 / 30%);
  z-index: 5;
}

.pres__align {
  top: 56px;
  animation: pres-pop-center 0.12s ease-out;
}

@keyframes pres-pop-center {
  from {
    opacity: 0;
    transform: translate(-50%, 6px);
  }

  to {
    opacity: 1;
    transform: translate(-50%, 0);
  }
}

@keyframes pres-pop {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .pres__align,
  .pres__settings,
  .pres__layers {
    animation: none;
  }
}

.pres__tool {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--text, #e5e7eb);
  cursor: pointer;
}

.pres__tool:hover {
  background: var(--bg-hover, rgb(255 255 255 / 8%));
}

.pres__tool--on {
  background: color-mix(in srgb, var(--accent, #15d1a0) 18%, transparent);
  color: var(--text, #e5e7eb);
}

.pres__tool-sep {
  width: 1px;
  margin: 4px 2px;
  background: var(--border, rgb(255 255 255 / 12%));
}

.pres__settings {
  position: absolute;
  top: 56px;
  left: 50%;
  transform: translateX(-50%);
  width: 280px;
  border-radius: 10px;
  background: var(--bg-surface, #1b1f2a);
  border: 1px solid var(--border, rgb(255 255 255 / 8%));
  box-shadow: 0 10px 30px rgb(0 0 0 / 35%);
  color: var(--text, #e5e7eb);
  z-index: 6;
  animation: pres-pop-center 0.12s ease-out;
}

.pres__settings-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  font-weight: 600;
  border-bottom: 1px solid var(--border, rgb(255 255 255 / 8%));
}

.pres__settings-body {
  padding: 10px 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pres__settings-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted, #8b93a7);
  margin-top: 6px;
}

.pres__preset-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.pres__preset {
  padding: 6px 4px;
  border: 1px solid var(--border, rgb(255 255 255 / 14%));
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 12px;
}

.pres__preset:hover {
  background: var(--bg-hover, rgb(255 255 255 / 6%));
}

.pres__preset--on {
  border: 1px solid var(--accent, #15d1a0);
  background: color-mix(in srgb, var(--accent, #15d1a0) 18%, transparent);
}

.pres__num {
  display: inline-flex;
  flex-direction: column;
  gap: 2px;
  font-size: 10px;
  color: var(--text-muted, #8b93a7);
}

.pres__settings-row {
  display: flex;
  gap: 8px;
}

.pres__settings-row .pres__num {
  flex: 1;
}

.pres__num input,
.pres__select {
  height: 30px;
  box-sizing: border-box;
  border: 1px solid var(--default-form-element-border-color, var(--border, rgb(255 255 255 / 14%)));
  border-radius: 6px;
  background-color: var(--bg-input, rgb(255 255 255 / 4%));
  color: var(--text, #e5e7eb);
  padding: 0 8px;
  width: 100%;
  transition:
    border-color 0.12s ease,
    box-shadow 0.12s ease;
}

.pres__select {
  appearance: none;
  padding-right: 24px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' fill='none' stroke='%23888' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 9px center;
}

.pres__num input:focus,
.pres__select:focus {
  outline: none;
  border-color: var(--accent, #15d1a0);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent, #15d1a0) 22%, transparent);
}

.pres__bg-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pres__bg-hint {
  font-size: 12px;
  color: var(--text-muted, #8b93a7);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pres__hud {
  position: absolute;
  bottom: 12px;
  left: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 10px;
  background: var(--bg-surface, #1b1f2a);
  border: 1px solid var(--border, rgb(255 255 255 / 8%));
  box-shadow: 0 8px 24px rgb(0 0 0 / 30%);
  z-index: 5;
}

.pres__hud-btn {
  display: inline-flex;
  width: 28px;
  height: 28px;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text, #e5e7eb);
  cursor: pointer;
}

.pres__hud-btn:disabled {
  opacity: 0.3;
  cursor: default;
}

.pres__hud-status {
  font-size: 12px;
  color: var(--text-muted, #8b93a7);
  min-width: 48px;
}

.pres__inspector {
  position: absolute;
  z-index: 6;
  transform: translate(-50%, calc(-100% - 12px));
}

.pres__inspector--below {
  transform: translate(-50%, 12px);
}

.pres__layers {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 224px;
  max-height: 70%;
  overflow: auto;
  border-radius: 10px;
  background: var(--bg-surface, #1b1f2a);
  border: 1px solid var(--border, rgb(255 255 255 / 8%));
  box-shadow: 0 10px 30px rgb(0 0 0 / 35%);
  color: var(--text, #e5e7eb);
  z-index: 6;
  animation: pres-pop 0.12s ease-out;
}

.pres__layers-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  font-weight: 600;
  border-bottom: 1px solid var(--border, rgb(255 255 255 / 8%));
}

.pres__layers-x {
  border: none;
  background: transparent;
  color: inherit;
  font-size: 18px;
  cursor: pointer;
}

.pres__layers-hint {
  padding: 6px 10px 4px;
  font-size: 11px;
  color: var(--text-muted, #8b93a7);
}

.pres__layer {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  cursor: pointer;
}

.pres__layer:hover {
  background: var(--bg-hover, rgb(255 255 255 / 6%));
}

.pres__layer--sel {
  background: color-mix(in srgb, var(--accent, #15d1a0) 15%, transparent);
}

.pres__layer-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.pres__layer--hidden .pres__layer-name {
  opacity: 0.5;
  font-style: italic;
}

.pres__layer-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: var(--text-muted, #8b93a7);
  cursor: pointer;
}

.pres__layer-btn :deep(svg) {
  width: 15px;
  height: 15px;
}

.pres__layer-btn:hover {
  background: var(--bg-hover, rgb(255 255 255 / 8%));
  color: var(--text, #e5e7eb);
}

.pres__layer-btn--on {
  color: var(--accent, #15d1a0);
}

.pres__layers-foot {
  display: flex;
  gap: 6px;
  padding: 8px 10px;
  border-top: 1px solid var(--border, rgb(255 255 255 / 8%));
}

.pres__layer-action {
  flex: 1;
  padding: 5px;
  border: 1px solid var(--border, rgb(255 255 255 / 15%));
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 12px;
}

.pres__layer-action:disabled {
  opacity: 0.4;
  cursor: default;
}
</style>
