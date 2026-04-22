<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

export interface Suggestion {
  name: string | null;
  title: string;
}

export interface SuggestionsFixed {
  type: 'fixed';
  suggestions: Suggestion[];
}

interface SuggestionsFiltered {
  type: 'filtered';
  suggestions: Suggestion[];
}

interface SuggestionsCallbackFiltered {
  type: 'callback-filtered';
  querySuggestions: (q: string) => Promise<unknown>;
}

interface Props {
  options: SuggestionsFixed | SuggestionsFiltered | SuggestionsCallbackFiltered;
  label: string;
  selectedOption?: string | null;
  disabled?: boolean;
  required?: boolean;
  inputHint?: string;
  noResultsHint?: string;
  noElementsText?: string;
  width?: 'default' | 'half' | 'fill';
  formValidation?: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{ 'update:selectedOption': [value: string | null] }>();

const open = ref(false);
const query = ref('');
const container = ref<HTMLElement | null>(null);

const suggestions = computed((): Suggestion[] => {
  if (props.options.type === 'fixed') return props.options.suggestions;
  if (props.options.type === 'filtered') return props.options.suggestions;
  return [];
});

const filtered = computed(() => {
  if (!query.value) return suggestions.value;
  const q = query.value.toLowerCase();
  return suggestions.value.filter((s) => s.title.toLowerCase().includes(q));
});

const selectedTitle = computed(() => {
  const found = suggestions.value.find((s) => s.name === props.selectedOption);
  return found ? found.title : (props.selectedOption ?? '');
});

function toggle() {
  if (props.disabled) return;
  open.value = !open.value;
  if (open.value) query.value = '';
}

function select(s: Suggestion) {
  emit('update:selectedOption', s.name);
  open.value = false;
  query.value = '';
}

function onClickOutside(e: MouseEvent) {
  if (container.value && !container.value.contains(e.target as Node)) {
    open.value = false;
  }
}

onMounted(() => document.addEventListener('mousedown', onClickOutside));
onBeforeUnmount(() => document.removeEventListener('mousedown', onClickOutside));
</script>

<template>
  <div
    ref="container"
    class="cmk-dropdown"
    :class="[`cmk-dropdown--${width ?? 'default'}`, { 'cmk-dropdown--disabled': disabled }]"
  >
    <button type="button" class="cmk-dropdown__trigger" :disabled="disabled" @click="toggle">
      <span class="cmk-dropdown__value">{{ selectedTitle || label || inputHint || '…' }}</span>
      <svg
        class="cmk-dropdown__chevron"
        :class="{ 'cmk-dropdown__chevron--open': open }"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
      </svg>
    </button>

    <div v-if="open" class="cmk-dropdown__menu">
      <input
        v-if="options.type !== 'fixed' || suggestions.length > 8"
        v-model="query"
        class="cmk-dropdown__search"
        type="text"
        :placeholder="inputHint ?? ''"
        @click.stop
      />
      <ul class="cmk-dropdown__list">
        <li v-if="filtered.length === 0" class="cmk-dropdown__no-results">
          {{ noResultsHint ?? noElementsText ?? 'No results' }}
        </li>
        <li
          v-for="s in filtered"
          :key="String(s.name)"
          class="cmk-dropdown__item"
          :class="{ 'cmk-dropdown__item--selected': s.name === selectedOption }"
          @mousedown.prevent="select(s)"
        >
          {{ s.title }}
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.cmk-dropdown {
  position: relative;
  display: inline-block;
}
.cmk-dropdown--default {
  min-width: 140px;
}
.cmk-dropdown--half {
  width: 50%;
}
.cmk-dropdown--fill {
  width: 100%;
}

.cmk-dropdown__trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 4px 8px;
  font-size: 13px;
  background: var(--bg-surface, #1e1e1e);
  color: var(--text, #ccc);
  border: 1px solid var(--border, #3a3a3a);
  border-radius: 4px;
  cursor: pointer;
  text-align: left;
  transition: border-color 150ms;
}
.cmk-dropdown__trigger:hover:not(:disabled) {
  border-color: var(--color-corporate-green-50, #0f9b5e);
}
.cmk-dropdown__trigger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cmk-dropdown__value {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cmk-dropdown__chevron {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
  transition: transform 200ms;
}
.cmk-dropdown__chevron--open {
  transform: rotate(180deg);
}

.cmk-dropdown__menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 100%;
  z-index: 200;
  background: var(--bg-surface, #1e1e1e);
  border: 1px solid var(--border, #3a3a3a);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  overflow: hidden;
}

.cmk-dropdown__search {
  width: 100%;
  box-sizing: border-box;
  padding: 6px 8px;
  font-size: 12px;
  background: transparent;
  color: var(--text, #ccc);
  border: none;
  border-bottom: 1px solid var(--border, #3a3a3a);
  outline: none;
}

.cmk-dropdown__list {
  list-style: none;
  margin: 0;
  padding: 4px 0;
  max-height: 240px;
  overflow-y: auto;
}

.cmk-dropdown__item {
  padding: 5px 10px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text, #ccc);
  transition: background 100ms;
}
.cmk-dropdown__item:hover {
  background: var(--bg-hover, rgba(255, 255, 255, 0.06));
}
.cmk-dropdown__item--selected {
  color: var(--color-corporate-green-50, #0f9b5e);
  font-weight: 500;
}

.cmk-dropdown__no-results {
  padding: 8px 10px;
  font-size: 12px;
  color: var(--color-daylight-grey-60, #6b6b6b);
}
</style>
