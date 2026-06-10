<template>
  <div ref="rootEl" class="orb-hover" :style="positionStyle">
    <div class="orb-hover__card" @mouseenter="onCardEnter" @mouseleave="onCardLeave">
      <!-- No permission: skip all templates and show only this -->
      <div v-if="isNoPermission" class="orb-hover__empty">
        {{ _t('No permission') }}
      </div>

      <!-- NOT_FOUND: object referenced on the board doesn't exist in monitoring data. -->
      <div v-else-if="isNotFound" class="orb-hover__empty">
        <div class="orb-hover__empty-name">
          {{ displayName }}
        </div>
        {{ _t('Not found in monitoring data') }}
      </div>

      <!-- Custom template — sanitized via sanitizeTemplateHtml before rendering -->
      <div v-else-if="renderedTemplate" class="orb-hover__template" v-html="renderedTemplate" />

      <!-- Default content -->
      <template v-else>
        <!-- Header: hostname + state on one line — operator reads
                     "localhost — UP since 2d 11h" as a single headline. -->
        <div class="orb-hover__headline">
          <span v-if="hasMonitoring" class="orb-hover__dot" :class="stateColor" />
          <div class="orb-hover__name">
            {{ displayName }}
          </div>
          <span v-if="hasMonitoring && state" class="orb-hover__state" :class="stateTextColor">
            {{ state.state }}
          </span>
          <span v-if="hasMonitoring && state && stateDuration" class="orb-hover__since">
            {{ _t('since %{duration}', { duration: stateDuration }) }}
          </span>
        </div>
        <!-- Subtitle: type · alias · address · @site (full width, second row) -->
        <div class="orb-hover__subtitle">
          {{ subtitleText }}
        </div>

        <template v-if="hasMonitoring">
          <!-- Status modifiers (ACK / DOWNTIME / STALE / MUTED / Attempts) -->
          <div v-if="state">
            <!-- Attempts: only when interesting (SOFT escalation, attempt > 1) -->
            <div v-if="attemptsBadge" class="orb-hover__attempts" :class="attemptsCls">
              {{ attemptsBadge }}
            </div>
            <!-- Modifier badges (ACK / DOWNTIME / STALE / MUTED) — directly
                             under the state so the operator sees "no action needed" or
                             "I won't be paged" before scrolling to output/pills. -->
            <div
              v-if="
                state.acknowledged ||
                state.in_downtime ||
                state.stale ||
                state.notifications_enabled === false
              "
              class="orb-hover__badges"
            >
              <span v-if="state.acknowledged" class="orb-hover__badge orb-hover__badge--warn">
                <svg
                  class="orb-hover__badge-icon"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="3"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                ACK
              </span>
              <span v-if="state.in_downtime" class="orb-hover__badge orb-hover__badge--downtime">
                <svg class="orb-hover__badge-icon" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                </svg>
                DOWNTIME
              </span>
              <span v-if="state.stale" class="orb-hover__badge orb-hover__badge--stale">
                <svg
                  class="orb-hover__badge-icon"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2.5"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                STALE
              </span>
              <!-- Critical operator awareness: notifications disabled means
                                 nobody gets paged when this host breaks. Don't let the
                                 operator assume otherwise. -->
              <span
                v-if="state.notifications_enabled === false"
                class="orb-hover__badge orb-hover__badge--warn"
                :title="_t('Notifications disabled — alerts will not be sent for this host')"
              >
                <svg
                  class="orb-hover__badge-icon"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M9.143 17.082a24.248 24.248 0 003.844.148m-3.844-.148a23.856 23.856 0 01-5.455-1.31 8.964 8.964 0 002.3-5.542m3.155 6.852a3 3 0 005.667 1.97m1.965-2.277L21 21M4.5 4.5l15 15"
                  />
                </svg>
                MUTED
              </span>
            </div>
          </div>

          <!-- Output -->
          <div v-if="state?.output" class="orb-hover__output">
            {{ state.output }}
          </div>

          <!-- Services summary pills (host objects only). With a Checkmk URL
                         each pill deep-links into the filtered allservices view, so the
                         operator jumps straight from hover to "the 3 CRIT services"
                         without the drawer detour. -->
          <div v-if="servicePills.length" class="orb-hover__pills">
            <component
              :is="pill.url ? 'a' : 'span'"
              v-for="pill in servicePills"
              :key="pill.label"
              class="orb-hover__pill"
              :class="[pill.cls, { 'orb-hover__pill--link': pill.url }]"
              :href="pill.url || undefined"
              :target="pill.url ? '_blank' : undefined"
              :rel="pill.url ? 'noopener noreferrer' : undefined"
            >
              <span class="orb-hover__pill-dot" :class="pill.dot" />
              {{ pill.count }} {{ pill.label }}
            </component>
          </div>

          <!-- CMK Perfometer (loaded async from backend) -->
          <div v-if="cmkPerfometer" class="orb-hover__perfometer">
            <div class="orb-hover__perfometer-label">
              {{ cmkPerfometer.label }}
            </div>
            <div
              v-for="(row, ri) in cmkPerfometer.rows"
              :key="ri"
              class="orb-hover__perfometer-row"
            >
              <div
                v-for="(seg, si) in row"
                :key="si"
                class="orb-hover__perfometer-seg"
                :style="{ width: `${seg.pct}%`, backgroundColor: seg.color }"
              />
            </div>
          </div>

          <!-- Fallback: simple perf_data bars — only when no CMK perfometer is on the way -->
          <div
            v-else-if="cmkPerfometerStatus !== 'loading' && perfMetrics.length"
            class="orb-hover__metrics"
          >
            <template v-for="m in perfMetrics" :key="m.label">
              <div class="orb-hover__metric-head">
                <span class="orb-hover__metric-label">{{ m.label }}</span>
                <span class="orb-hover__metric-value">{{ fmtMetricValue(m) }}</span>
              </div>
              <div v-if="utilPercent(m) > 0" class="orb-hover__metric-bar">
                <div
                  class="orb-hover__metric-fill"
                  :style="{
                    width: `${utilPercent(m)}%`,
                    backgroundColor: utilColor(utilPercent(m))
                  }"
                />
              </div>
            </template>
          </div>

          <!-- Next check (relative; warns when overdue) -->
          <div v-if="nextCheckText" class="orb-hover__next-check" :class="nextCheckText.cls">
            {{ nextCheckText.text }}
          </div>
        </template>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { type CSSProperties, computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

import { metricsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { BoardObject, ObjectState, PerfometerResult } from '@/types/api'
import { buildServiceStateViewUrl } from '@/utils/boardNavigation'
import { VISUAL_ONLY_TYPES, getBoardObjectIdentifier, getObjectTypeLabel } from '@/utils/naming'
import { type PerfMetric, parsePerfData, utilColor, utilPercent } from '@/utils/perf'
import { sanitizeTemplateHtml } from '@/utils/sanitize'
import { interpolateTemplate } from '@/utils/template'
import { formatRelativeDuration, formatRelativeFuture } from '@/utils/time'
import usei18n from '@/vendor/cmk/lib/i18n'

const props = defineProps<{
  object: BoardObject
  state: ObjectState | undefined
  x: number
  y: number
  template?: string | null
  connectionId?: string | null
  // Checkmk GUI base — makes the service-state pills clickable links into
  // the filtered allservices view. Omit (standalone) for plain pills.
  checkmkUrl?: string | null
  // Bounding rect of the hovered icon (in viewport coords). When the tooltip
  // has to flip to avoid overflow we anchor the flipped position at this
  // rect's edges so the tooltip never lands on top of the icon.
  anchorRect?: { left: number; top: number; right: number; bottom: number } | null
}>()

// Card hover round-trip for the close-grace in the host views: the parent
// delays its close on hover-leave so the operator can move onto the card
// (clickable pills, readable output); entering the card cancels the close,
// leaving it re-schedules — the card may overlap its own object, so the
// pointer must be able to slide card→object→card without a flicker.
// Listen on mouseenter (NOT pointerenter): the browser fires pointer events
// before mouse events, so a pointerenter-cancel would run BEFORE the
// object's mouseleave schedules the close and the timer would survive.
const emit = defineEmits<{
  'card-enter': []
  'card-leave': []
}>()

// While the pointer is on the card, freeze the position — the parent may
// keep emitting hover coordinates which would yank the card from under
// the cursor mid-click.
const pinned = ref(false)
function onCardEnter() {
  pinned.value = true
  emit('card-enter')
}
function onCardLeave() {
  pinned.value = false
  emit('card-leave')
}

const { _t } = usei18n()
const authStore = useAuthStore()

const cmkPerfometer = ref<PerfometerResult | null>(null)
// Tracks whether a /metrics/perfometer fetch is in flight, so we can hide the
// raw perf_data fallback while the proper CMK perfometer is still loading —
// otherwise the tooltip flickers between two different bar styles.
const cmkPerfometerStatus = ref<'idle' | 'loading' | 'done'>('idle')

// Viewport-aware positioning: render once invisible to measure, then flip to
// the cursor's left/top side if the tooltip would overflow the right/bottom
// edge of the viewport. Recomputes on prop changes so the same instance can
// follow the cursor across objects without sticking off-screen.
const rootEl = ref<HTMLDivElement | null>(null)
const adjusted = ref<{ left: number; top: number; ready: boolean }>({
  left: props.x,
  top: props.y,
  ready: false
})

const positionStyle = computed<CSSProperties>(() => ({
  left: `${adjusted.value.left}px`,
  top: `${adjusted.value.top}px`,
  visibility: adjusted.value.ready ? 'visible' : 'hidden'
}))

// Effective viewport bounds in *this window's* coordinate system. When OrbVis
// runs inside Checkmk's <iframe name="main">, the outer browser window is
// often smaller than the iframe's own innerHeight, so a position that fits
// `window.innerHeight` can still paint past the visible parent edge. Read the
// top window's size when same-origin allows it, and translate it back into
// our local coords via the iframe's offset.
function getEffectiveBounds(): { width: number; height: number } {
  const fallback = { width: window.innerWidth, height: window.innerHeight }
  if (window === window.top) return fallback
  try {
    const top = window.top
    const frame = window.frameElement as HTMLIFrameElement | null
    if (!top || !frame) return fallback
    const fr = frame.getBoundingClientRect()
    return {
      width: Math.min(fallback.width, top.innerWidth - fr.left),
      height: Math.min(fallback.height, top.innerHeight - fr.top)
    }
  } catch {
    return fallback
  }
}

async function updatePosition() {
  await nextTick()
  if (!rootEl.value) return
  const rect = rootEl.value.getBoundingClientRect()
  const { width: viewportW, height: viewportH } = getEffectiveBounds()
  const margin = 8
  const gap = 8
  let left = props.x
  let top = props.y
  if (left + rect.width > viewportW - margin) {
    // Flip past the icon's *left edge* if we know it; otherwise back off
    // from the cursor by the tooltip width. Cursor-based fallback can
    // overlap a small icon, so anchorRect is strongly preferred.
    const flipFrom = props.anchorRect ? props.anchorRect.left : props.x
    left = Math.max(margin, flipFrom - rect.width - gap)
  }
  if (top + rect.height > viewportH - margin) {
    const flipFrom = props.anchorRect ? props.anchorRect.top : props.y
    top = Math.max(margin, flipFrom - rect.height - gap)
  }
  adjusted.value = { left, top, ready: true }
}

watch(
  () => [props.x, props.y],
  () => {
    // Frozen while the pointer is on the card — repositioning would yank
    // the pill out from under the cursor mid-click.
    if (pinned.value) return
    adjusted.value.ready = false
    void updatePosition()
  }
)

onMounted(() => {
  void updatePosition()
})

onMounted(() => {
  // Perfometer only makes sense for an object linked to a specific service
  // (either a `service` object or a line/graph pointing at one).
  const isServiceLinked =
    props.object.type === 'service' ||
    ((props.object.type === 'line' || props.object.type === 'graph') &&
      !!props.object.service_description)
  if (
    isServiceLinked &&
    props.object.host_name &&
    props.object.service_description &&
    props.connectionId &&
    authStore.accessToken &&
    // No perfdata to fetch when the service doesn't exist or we're locked out.
    props.state?.state !== 'NOT_FOUND' &&
    props.state?.state !== 'NO_PERMISSION'
  ) {
    cmkPerfometerStatus.value = 'loading'
    metricsApi
      .getPerfometer(
        props.connectionId,
        props.object.host_name,
        props.object.service_description,
        authStore.accessToken
      )
      .then((r) => {
        cmkPerfometer.value = r
      })
      .catch(() => {})
      .finally(() => {
        cmkPerfometerStatus.value = 'done'
      })
  }
})

const renderedTemplate = computed(() => {
  if (!props.template) return null
  const html = interpolateTemplate(props.template, props.object, props.state)
  return sanitizeTemplateHtml(html)
})

const displayName = computed(() => getBoardObjectIdentifier(props.object))

const hoverTypeLabel = computed(() => getObjectTypeLabel(props.object))

const hasMonitoring = computed(() => {
  // A line linked to a host/service is not purely decorative — show its state.
  if (props.object.type === 'line') {
    return !!(props.object.host_name || props.object.service_description)
  }
  return !(VISUAL_ONLY_TYPES as readonly string[]).includes(props.object.type)
})

const isNoPermission = computed(() => props.state?.state === 'NO_PERMISSION')
const isNotFound = computed(() => props.state?.state === 'NOT_FOUND')

const STATE_BG: Record<string, string> = {
  UP: 'orb-hover__dot--ok',
  OK: 'orb-hover__dot--ok',
  DOWN: 'orb-hover__dot--down',
  CRITICAL: 'orb-hover__dot--down',
  UNREACHABLE: 'orb-hover__dot--unknown',
  UNKNOWN: 'orb-hover__dot--unknown',
  WARNING: 'orb-hover__dot--warn',
  PENDING: 'orb-hover__dot--pending'
}
const STATE_TEXT: Record<string, string> = {
  UP: 'orb-hover__state--ok',
  OK: 'orb-hover__state--ok',
  DOWN: 'orb-hover__state--down',
  CRITICAL: 'orb-hover__state--down',
  UNREACHABLE: 'orb-hover__state--unknown',
  UNKNOWN: 'orb-hover__state--unknown',
  WARNING: 'orb-hover__state--warn',
  PENDING: 'orb-hover__state--pending'
}

const stateColor = computed(
  () => STATE_BG[props.state?.state ?? 'PENDING'] ?? 'orb-hover__dot--pending'
)
const stateTextColor = computed(
  () => STATE_TEXT[props.state?.state ?? 'PENDING'] ?? 'orb-hover__state--pending'
)

const subtitleText = computed(() => {
  const parts: string[] = [hoverTypeLabel.value]
  const seen = new Set<string>([displayName.value])
  const push = (raw: string | undefined | null, prefix = '') => {
    const v = raw?.trim()
    if (!v || seen.has(v)) return
    seen.add(v)
    parts.push(prefix ? `${prefix}${v}` : v)
  }
  // alias and address help identify the host beyond the (possibly customised)
  // displayName; site is shown last as a "@site" suffix so it reads naturally
  // ("host · 10.0.4.12 · @eu_west").
  push(props.state?.alias)
  push(props.state?.address)
  push(props.state?.site_id, '@')
  return parts.join(' · ')
})

// Reactive clock so "since X" / "next check in X" tick down while the tooltip
// stays open. Driven by a 1-Hz interval that lives only as long as the
// component is mounted, so closed tooltips don't keep timers alive.
const nowMs = ref(Date.now())
let _tick: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  _tick = setInterval(() => {
    nowMs.value = Date.now()
  }, 1000)
})
onUnmounted(() => {
  if (_tick) clearInterval(_tick)
  _tick = null
})

const attemptsBadge = computed(() => {
  const cur = props.state?.current_attempt ?? 0
  const max = props.state?.max_attempts ?? 0
  if (!cur || !max) return ''
  // Steady-state HARD checks don't need to advertise "1/3" — show only when
  // there's something interesting (SOFT progression or non-first attempt).
  if (props.state?.state_type === 'SOFT' || cur > 1) {
    return `${props.state?.state_type ?? ''} ${cur}/${max}`.trim()
  }
  return ''
})

const stateDuration = computed(() =>
  formatRelativeDuration(props.state?.last_state_change, nowMs.value)
)

// SOFT-state escalation deserves an amber attention cue; HARD steady-state is
// rendered muted (or hidden entirely by attemptsBadge's own gate).
const attemptsCls = computed(() =>
  props.state?.state_type === 'SOFT' ? 'orb-hover__attempts--soft' : ''
)

interface NextCheckText {
  text: string
  cls: string
}
// CMC's check scheduling can make `next_check` lag behind "now" by a
// second or two even when the check is healthy. Suppress the "overdue"
// label until the LAST check is itself stale by this many seconds.
const OVERDUE_GRACE_SECONDS = 60
const nextCheckText = computed((): NextCheckText | null => {
  const ts = props.state?.next_check
  if (!ts) return null
  const future = formatRelativeFuture(ts, nowMs.value)
  if (future) {
    return {
      text: _t('next check in %{duration}', { duration: future }),
      cls: ''
    }
  }
  // next_check is in the past. CMC schedules checks sub-second and
  // returns a `next_check` value that's already a hair behind "now"
  // even immediately after a successful check — flashing "overdue"
  // every render would be wrong. Only treat the check as overdue if
  // the LAST one is also stale; otherwise show the freshness via
  // last_check.
  const lastCheck = props.state?.last_check
  const sinceLastCheckSec =
    lastCheck && lastCheck > 0 ? Math.floor(nowMs.value / 1000 - lastCheck) : Infinity
  if (sinceLastCheckSec < OVERDUE_GRACE_SECONDS) {
    return null
  }
  const overdue = formatRelativeDuration(ts, nowMs.value)
  if (!overdue) return null
  return {
    text: _t('check overdue by %{duration}', { duration: overdue }),
    cls: 'orb-hover__next-check--overdue'
  }
})

interface ServicePill {
  label: 'OK' | 'WARN' | 'CRIT' | 'UNKN' | 'PEND'
  count: number
  cls: string
  dot: string
  /** Deep-link into the filtered Checkmk allservices view (hosts only). */
  url: string | null
}

const servicePills = computed((): ServicePill[] => {
  // Hosts: per-host service-state breakdown.
  // Hostgroups/Servicegroups: per-member state breakdown — the backend
  // populates the same ``services_summary`` shape (UP→ok, DOWN→critical,
  // UNREACHABLE→unknown for hostgroups), so the same pill row works.
  if (
    props.object.type !== 'host' &&
    props.object.type !== 'hostgroup' &&
    props.object.type !== 'servicegroup'
  )
    return []
  const summary = props.state?.services_summary
  if (!summary) return []
  // Severity-descending: a CRIT pill catches the eye before "all green",
  // matching the operator's "what's broken?" mental model. OK is still
  // shown last as confirmation.
  // Pills deep-link only for plain hosts: group pills count MEMBER states
  // (hosts/services of the group), so a per-host svcstate URL would lie.
  const linkable = props.object.type === 'host'
  const url = (state: string | null): string | null =>
    linkable && state
      ? buildServiceStateViewUrl(props.checkmkUrl ?? null, { host: props.object.host_name }, state)
      : null
  // Severity-descending: a CRIT pill catches the eye before "all green";
  // OK stays last as confirmation.
  const defs: Array<{
    key: keyof typeof summary
    label: ServicePill['label']
    tone: string
    state: string | null
  }> = [
    { key: 'critical', label: 'CRIT', tone: 'crit', state: 'CRITICAL' },
    { key: 'unknown', label: 'UNKN', tone: 'unknown', state: 'UNKNOWN' },
    { key: 'warning', label: 'WARN', tone: 'warn', state: 'WARNING' },
    { key: 'pending', label: 'PEND', tone: 'pending', state: 'PENDING' },
    { key: 'ok', label: 'OK', tone: 'ok', state: 'OK' }
  ]
  return defs
    .filter((d) => (summary[d.key] ?? 0) > 0)
    .map((d) => ({
      label: d.label,
      count: summary[d.key] ?? 0,
      cls: `orb-hover__pill--${d.tone}`,
      dot: `orb-hover__pill-dot--${d.tone}`,
      url: url(d.state)
    }))
})

const perfMetrics = computed((): PerfMetric[] => {
  // Same reasoning as `isServiceLinked` above — only service-linked objects have perf data.
  const showPerf =
    props.object.type === 'service' ||
    ((props.object.type === 'line' || props.object.type === 'graph') &&
      !!props.object.service_description)
  if (!showPerf) return []
  return parsePerfData(props.state?.perf_data ?? '').slice(0, 4)
})

function fmtMetricValue(m: PerfMetric): string {
  const v = Number.isInteger(m.value) ? String(m.value) : m.value.toFixed(2).replace(/\.?0+$/, '')
  return `${v}${m.unit}`
}
</script>

<style scoped>
.orb-hover {
  position: fixed;
  z-index: 50;
  pointer-events: none;
}

a.orb-hover__pill {
  cursor: pointer;
  text-decoration: none;
}

a.orb-hover__pill:hover {
  filter: brightness(1.25);
  text-decoration: underline;
}

/* The card is interactive (tooltip stays while the pointer is on it; the
   pills are links). It can overlap neighbouring objects — leaving it
   re-schedules the close so anything underneath becomes hoverable again. */
.orb-hover__card {
  pointer-events: auto;
  min-width: 208px;
  max-width: 288px;
  padding: 14px;
  background: var(--bg-glass);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  box-shadow:
    0 0 0 1px var(--border),
    0 25px 50px -12px rgb(0 0 0 / 60%);
}

.orb-hover__empty {
  font-size: var(--font-size-large);
  line-height: 20px;
  font-style: italic;
  color: var(--text-muted);
}

.orb-hover__empty-name {
  margin-bottom: var(--dimension-3);
  font-style: normal;
  font-weight: 600;
  color: var(--text);
}

.orb-hover__template {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text);
}

.orb-hover__headline {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: var(--dimension-4);
}

.orb-hover__dot {
  align-self: center;
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 9999px;
}

.orb-hover__dot--ok {
  background: var(--color-corporate-green-50);
}

.orb-hover__dot--down {
  background: var(--color-light-red-50);
}

.orb-hover__dot--unknown {
  background: var(--color-orange-40);
}

.orb-hover__dot--warn {
  background: var(--color-warning);
}

.orb-hover__dot--pending {
  background: var(--color-pending);
}

.orb-hover__name {
  overflow: hidden;
  flex: 1;
  min-width: 0;
  font-size: var(--font-size-large);
  line-height: 1.25;
  font-weight: 600;
  color: var(--text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-hover__state {
  flex-shrink: 0;
  font-size: var(--font-size-large);
  line-height: 1.25;
  font-weight: 700;
}

.orb-hover__state--ok {
  color: var(--color-corporate-green-60);
}

.dark .orb-hover__state--ok {
  color: var(--color-corporate-green-50);
}

.orb-hover__state--down {
  color: var(--color-light-red-60);
}

.dark .orb-hover__state--down {
  color: var(--color-light-red-40);
}

.orb-hover__state--unknown {
  color: var(--color-orange-60);
}

.dark .orb-hover__state--unknown {
  color: var(--color-orange-40);
}

.orb-hover__state--warn {
  color: var(--color-yellow-60);
}

.dark .orb-hover__state--warn {
  color: var(--color-warning);
}

.orb-hover__state--pending {
  color: var(--text-muted);
}

.orb-hover__since {
  flex-shrink: 0;
  font-size: 10px;
  color: var(--text-muted);
}

.orb-hover__subtitle {
  overflow: hidden;
  margin-top: var(--dimension-2);
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-hover__attempts {
  margin-top: 6px;
  font-size: 10px;
  color: var(--text-muted);
}

.orb-hover__attempts--soft {
  font-weight: 600;
  color: var(--color-yellow-60);
}

.dark .orb-hover__attempts--soft {
  color: var(--color-yellow-50);
}

.orb-hover__badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.orb-hover__badge {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) 6px;
  font-size: 10px;
  font-weight: 600;
  border-radius: 9999px;
}

.orb-hover__badge--warn {
  color: var(--color-yellow-60);
  background: color-mix(in srgb, var(--color-warning) 20%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-warning) 40%, transparent);
}

.dark .orb-hover__badge--warn {
  color: var(--color-yellow-50);
  background: color-mix(in srgb, var(--color-warning) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-warning) 25%, transparent);
}

.orb-hover__badge--downtime {
  color: var(--color-light-blue-70);
  background: color-mix(in srgb, var(--color-light-blue-50) 20%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-light-blue-50) 40%, transparent);
}

.dark .orb-hover__badge--downtime {
  color: var(--color-light-blue-50);
  background: color-mix(in srgb, var(--color-light-blue-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-light-blue-50) 25%, transparent);
}

.orb-hover__badge--stale {
  color: var(--text-muted);
  background: color-mix(in srgb, var(--color-pending) 20%, transparent);
  box-shadow: 0 0 0 1px var(--border);
}

.orb-hover__badge-icon {
  width: 10px;
  height: 10px;
}

.orb-hover__output {
  /* stylelint-disable-next-line value-no-vendor-prefix */
  display: -webkit-box;
  overflow: hidden;
  margin-top: 10px;
  font-size: var(--font-size-normal);
  line-height: 1.375;
  color: var(--text-muted);
  overflow-wrap: break-word;
  -webkit-line-clamp: 3;
  /* stylelint-disable-next-line property-no-vendor-prefix */
  -webkit-box-orient: vertical;
}

.orb-hover__pills {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-3);
  margin-top: 10px;
}

.orb-hover__pill {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) 6px;
  font-size: 10px;
  font-weight: 600;
  border-radius: 9999px;
}

.orb-hover__pill--crit {
  color: var(--color-light-red-70);
  background: color-mix(in srgb, var(--color-light-red-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-light-red-50) 30%, transparent);
}

.dark .orb-hover__pill--crit {
  color: var(--color-light-red-40);
}

.orb-hover__pill--unknown {
  color: var(--color-orange-70);
  background: color-mix(in srgb, var(--color-orange-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-orange-50) 30%, transparent);
}

.dark .orb-hover__pill--unknown {
  color: var(--color-orange-40);
}

.orb-hover__pill--warn {
  color: var(--color-yellow-60);
  background: color-mix(in srgb, var(--color-warning) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-warning) 30%, transparent);
}

.dark .orb-hover__pill--warn {
  color: var(--color-yellow-50);
}

.orb-hover__pill--pending {
  color: var(--text-muted);
  background: color-mix(in srgb, var(--color-pending) 15%, transparent);
  box-shadow: 0 0 0 1px var(--border);
}

.orb-hover__pill--ok {
  color: var(--color-corporate-green-70);
  background: color-mix(in srgb, var(--color-corporate-green-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 30%, transparent);
}

.dark .orb-hover__pill--ok {
  color: var(--color-corporate-green-50);
}

.orb-hover__pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 9999px;
}

.orb-hover__pill-dot--crit {
  background: var(--color-light-red-50);
}

.orb-hover__pill-dot--unknown {
  background: var(--color-orange-40);
}

.orb-hover__pill-dot--warn {
  background: var(--color-warning);
}

.orb-hover__pill-dot--pending {
  background: var(--color-pending);
}

.orb-hover__pill-dot--ok {
  background: var(--color-corporate-green-50);
}

.orb-hover__perfometer {
  margin-top: 10px;
}

.orb-hover__perfometer > * + * {
  margin-top: var(--dimension-3);
}

.orb-hover__perfometer-label {
  margin-bottom: var(--dimension-3);
  font-size: 10px;
  font-weight: 500;
  color: var(--text);
}

.orb-hover__perfometer-row {
  display: flex;
  overflow: hidden;
  height: 12px;
  border-radius: var(--border-radius);
  box-shadow: 0 0 0 1px rgb(255 255 255 / 10%);
}

.orb-hover__perfometer-seg {
  height: 100%;
  transition: all 0.15s;
}

.orb-hover__metrics {
  margin-top: 10px;
}

.orb-hover__metrics > * + * {
  margin-top: 6px;
}

.orb-hover__metric-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--dimension-3);
  font-size: 10px;
}

.orb-hover__metric-label {
  overflow: hidden;
  color: var(--text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-hover__metric-value {
  flex-shrink: 0;
  font-weight: 500;
  color: var(--text);
}

.orb-hover__metric-bar {
  overflow: hidden;
  height: 6px;
  margin-top: -2px;
  background: var(--bg-hover);
  border-radius: 9999px;
}

.orb-hover__metric-fill {
  height: 100%;
  border-radius: 9999px;
}

.orb-hover__next-check {
  margin-top: 10px;
  font-size: 10px;
  color: var(--text-muted);
}

.orb-hover__next-check--overdue {
  color: var(--color-yellow-60);
}

.dark .orb-hover__next-check--overdue {
  color: var(--color-yellow-50);
}
</style>
