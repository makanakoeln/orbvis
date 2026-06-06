<template>
  <div class="orb-ctx" :style="{ left: `${x}px`, top: `${y}px` }">
    <!-- Header -->
    <div class="orb-ctx__header">
      <p class="orb-ctx__name">
        {{ displayName }}
      </p>
      <p class="orb-ctx__type">
        {{ getObjectTypeLabel(object) }}
      </p>
    </div>

    <!-- Custom template block -->
    <!-- eslint-disable-next-line vue/no-v-html -->
    <div v-if="renderedTemplate" class="orb-ctx__template" v-html="renderedTemplate" />

    <a v-if="hostUrl" :href="hostUrl" target="_blank" class="orb-ctx__item">
      <svg
        class="orb-ctx__icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
        />
      </svg>
      <span>{{ _t('Host in Checkmk') }}</span>
    </a>
    <a v-if="hostServicesUrl" :href="hostServicesUrl" target="_blank" class="orb-ctx__item">
      <svg
        class="orb-ctx__icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
        />
      </svg>
      <span>{{ _t('Problem services') }}</span>
    </a>
    <a v-if="serviceUrl" :href="serviceUrl" target="_blank" class="orb-ctx__item">
      <svg
        class="orb-ctx__icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
        />
      </svg>
      <span>{{ _t('Service in Checkmk') }}</span>
    </a>
    <a v-if="groupUrl" :href="groupUrl" target="_blank" class="orb-ctx__item">
      <svg
        class="orb-ctx__icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
        />
      </svg>
      <span>{{ _t('Group in Checkmk') }}</span>
    </a>
    <a v-if="aggregationUrl" :href="aggregationUrl" target="_blank" class="orb-ctx__item">
      <svg
        class="orb-ctx__icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
        />
      </svg>
      <span>{{ _t('Aggregation tree in Checkmk') }}</span>
    </a>
    <a
      v-if="aggregationOverviewUrl"
      :href="aggregationOverviewUrl"
      target="_blank"
      class="orb-ctx__item"
    >
      <svg
        class="orb-ctx__icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
        />
      </svg>
      <span>{{ _t('All aggregations in Checkmk') }}</span>
    </a>

    <div
      v-if="
        !hostUrl && !hostServicesUrl && !serviceUrl && !groupUrl && !aggregationUrl && !checkmkUrl
      "
      class="orb-ctx__empty"
    >
      {{ _t('No Checkmk URL configured') }}
    </div>

    <!-- Operational actions (ack, downtime, force-check, comment, notifications)
             live exclusively in the detail drawer to avoid two competing paths
             for the same operation. Right-click stays as a navigation/edit
             quickpath. -->

    <div class="orb-ctx__footer">
      <button v-if="showEdit && lineHasBend" class="orb-ctx__item" @click="$emit('straighten')">
        <svg
          class="orb-ctx__icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 18L20 6" />
        </svg>
        {{ _t('Remove bend') }}
      </button>
      <button v-if="showEdit" class="orb-ctx__item" @click="$emit('edit')">
        <svg
          class="orb-ctx__icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125"
          />
        </svg>
        {{ _t('Edit properties') }}
      </button>
      <button v-if="showEdit" class="orb-ctx__item" @click="$emit('duplicate')">
        <svg
          class="orb-ctx__icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75"
          />
        </svg>
        {{ _t('Duplicate') }}
      </button>
      <button v-if="showEdit" class="orb-ctx__item orb-ctx__item--danger" @click="$emit('delete')">
        <svg
          class="orb-ctx__icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
          />
        </svg>
        {{ _t('Delete') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { BoardObject, ObjectState } from '@/types/api'
import { getBoardObjectName, getObjectTypeLabel } from '@/utils/naming'
import { sanitizeTemplateHtml } from '@/utils/sanitize'
import { interpolateTemplate } from '@/utils/template'
import usei18n from '@/vendor/cmk/lib/i18n'

const { _t } = usei18n()

const props = defineProps<{
  object: BoardObject
  state?: ObjectState
  x: number
  y: number
  checkmkUrl?: string | null
  showEdit?: boolean
  template?: string | null
}>()

defineEmits<{
  close: []
  edit: []
  duplicate: []
  delete: []
  straighten: []
}>()

// A bent line can be straightened back to a direct two-point line.
const lineHasBend = computed(
  () => props.object.type === 'line' && props.object.mid_x != null && props.object.mid_y != null
)

const renderedTemplate = computed(() =>
  props.template
    ? sanitizeTemplateHtml(interpolateTemplate(props.template, props.object, props.state))
    : null
)

// "Show problem services" is only useful when the host actually has problem
// services to drill into.
const _OK_STATES = new Set(['UP', 'OK', 'PENDING'])
const isProblematic = computed(
  () => props.state !== undefined && !_OK_STATES.has(props.state.state)
)

const displayName = computed(() => getBoardObjectName(props.object))

const base = computed(() => {
  // Strip trailing /check_mk or /check_mk/ so we can safely append /check_mk/view.py
  return props.checkmkUrl?.replace(/\/check_mk\/?$/, '').replace(/\/$/, '') ?? null
})

const site = computed(() => props.state?.site_id ?? null)

const hostUrl = computed(() => {
  if (!base.value || !props.object.host_name) return null
  const p: Record<string, string> = { view_name: 'hoststatus', host: props.object.host_name }
  if (site.value) p.site = site.value
  return `${base.value}/check_mk/view.py?${new URLSearchParams(p)}`
})

const serviceUrl = computed(() => {
  if (!base.value || !props.object.host_name || !props.object.service_description) return null
  const p: Record<string, string> = {
    view_name: 'service',
    host: props.object.host_name,
    service: props.object.service_description
  }
  if (site.value) p.site = site.value
  return `${base.value}/check_mk/view.py?${new URLSearchParams(p)}`
})

const groupUrl = computed(() => {
  if (!base.value || !props.object.group_name) return null
  const view = props.object.type === 'hostgroup' ? 'hostgroup' : 'servicegroup'
  const key = props.object.type === 'hostgroup' ? 'hostgroup' : 'servicegroup'
  const p: Record<string, string> = { view_name: view, [key]: props.object.group_name }
  if (site.value) p.site = site.value
  return `${base.value}/check_mk/view.py?${new URLSearchParams(p)}`
})

const aggregationUrl = computed(() => {
  if (!base.value || props.object.type !== 'aggregation' || !props.object.aggregation_id)
    return null
  const p: Record<string, string> = {
    view_name: 'aggr_single',
    aggr_name: props.object.aggregation_id,
    po_aggr_expand: '1'
  }
  if (site.value) p.site = site.value
  return `${base.value}/check_mk/view.py?${new URLSearchParams(p)}`
})

const aggregationOverviewUrl = computed(() => {
  if (!base.value || props.object.type !== 'aggregation') return null
  const p: Record<string, string> = { view_name: 'aggr_all' }
  if (site.value) p.site = site.value
  return `${base.value}/check_mk/view.py?${new URLSearchParams(p)}`
})

const hostServicesUrl = computed(() => {
  if (!base.value || props.object.type !== 'host' || !props.object.host_name) return null
  if (!isProblematic.value) return null
  // When the host itself is down/unreachable, services can't be checked independently
  const hostState = props.state?.state
  if (hostState === 'DOWN' || hostState === 'UNREACHABLE') return null
  const p: Record<string, string> = {
    view_name: 'host',
    host: props.object.host_name,
    filled_in: 'filter',
    _active: 'serviceregex;svcstate;host;siteopt',
    st1: 'on',
    st2: 'on',
    st3: 'on',
    stp: 'on'
  }
  if (site.value) p.site = site.value
  return `${base.value}/check_mk/view.py?${new URLSearchParams(p)}`
})
</script>
<style scoped>
.orb-ctx {
  position: fixed;
  z-index: 50;
  min-width: 192px;
  padding: 6px 0;
  background: var(--bg-glass);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  box-shadow:
    0 0 0 1px var(--border),
    0 25px 50px -12px rgb(0 0 0 / 60%);
}

.orb-ctx__header {
  margin-bottom: var(--dimension-3);
  padding: var(--dimension-4) 14px;
  border-bottom: 1px solid var(--border);
}

.orb-ctx__name {
  overflow: hidden;
  max-width: 208px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: 600;
  color: var(--text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-ctx__type {
  margin-top: var(--dimension-2);
  font-size: 10px;
  color: var(--text-muted);
}

.orb-ctx__template {
  margin-bottom: var(--dimension-3);
  padding: var(--dimension-4) 14px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text);
  border-bottom: 1px solid var(--border);
}

.orb-ctx__item {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  width: 100%;
  padding: var(--dimension-4) 14px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
  text-align: left;
  transition:
    color 0.15s,
    background-color 0.15s;
}

.orb-ctx__item:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.orb-ctx__item--danger {
  color: var(--color-light-red-40);
}

.orb-ctx__item--danger:hover {
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 8%, transparent);
}

.orb-ctx__icon {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
}

.orb-ctx__empty {
  padding: var(--dimension-4) 14px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-style: italic;
  color: var(--text-muted);
}

.orb-ctx__footer {
  margin-top: var(--dimension-3);
  padding-top: var(--dimension-3);
  border-top: 1px solid var(--border);
}
</style>
