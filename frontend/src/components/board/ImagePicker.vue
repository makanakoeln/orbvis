<template>
  <div class="orb-imgpick">
    <!-- Selected image preview + clear -->
    <div v-if="modelValue" class="orb-imgpick__selected">
      <img
        :src="`${BASE_URL}images/${modelValue}`"
        class="orb-imgpick__thumb"
        :class="selectedIsBuiltinSvg ? 'svg-icon' : ''"
      />
      <span class="orb-imgpick__selected-name">{{ modelValue }}</span>
      <button class="orb-imgpick__clear" type="button" @click="$emit('update:modelValue', '')">
        <svg
          class="orb-imgpick__clear-icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2.5"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Toggle button (hidden once an image is selected — clear via X to pick another) -->
    <button v-if="!modelValue" type="button" class="orb-imgpick__toggle" @click="open = !open">
      <svg
        class="orb-imgpick__toggle-icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
        />
      </svg>
      <span class="orb-imgpick__toggle-label">
        {{ modelValue ? _t('Custom icon') : emptyLabel }}
      </span>
      <svg
        class="orb-imgpick__chevron"
        :class="open ? 'orb-imgpick__chevron--open' : ''"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2.5"
      >
        <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
      </svg>
    </button>

    <!-- Dropdown panel -->
    <Transition
      enter-from-class="orb-imgpick__panel-enter-from"
      enter-active-class="orb-imgpick__panel-enter-active"
      leave-to-class="orb-imgpick__panel-leave-to"
      leave-active-class="orb-imgpick__panel-leave-active"
    >
      <div v-if="open" class="orb-imgpick__panel">
        <!-- Search -->
        <div class="orb-imgpick__search-wrap">
          <input v-model="query" :placeholder="searchLabel" class="orb-field orb-imgpick__search" />
        </div>

        <!-- Loading -->
        <div v-if="loading" class="orb-imgpick__loading">
          <svg class="orb-imgpick__spinner" fill="none" viewBox="0 0 24 24">
            <circle
              class="orb-imgpick__spinner-track"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            />
            <path
              class="orb-imgpick__spinner-head"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          {{ _t('Loading…') }}
        </div>

        <!-- No images at all → upload prompt -->
        <template v-else-if="!images.length">
          <div class="orb-imgpick__empty">
            <svg
              class="orb-imgpick__empty-icon"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="1.5"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
              />
            </svg>
            <p class="orb-imgpick__empty-text">
              {{ _t('No images uploaded yet') }}
            </p>
            <label class="orb-imgpick__upload-btn">
              <svg
                class="orb-imgpick__upload-icon"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2.5"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                />
              </svg>
              {{ uploadLabel }}
              <input
                type="file"
                accept="image/png,image/jpeg,image/svg+xml,image/webp"
                multiple
                class="orb-imgpick__file-input"
                @change="uploadImages"
              />
            </label>
          </div>

          <!-- Upload progress / error -->
          <Transition
            enter-from-class="orb-imgpick__status-enter-from"
            enter-active-class="orb-imgpick__status-enter-active"
            leave-to-class="orb-imgpick__status-leave-to"
            leave-active-class="orb-imgpick__status-leave-active"
          >
            <div v-if="uploading || uploadError" class="orb-imgpick__status">
              <div v-if="uploading" class="orb-imgpick__uploading">
                <svg
                  class="orb-imgpick__spinner orb-imgpick__spinner--sm"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="orb-imgpick__spinner-track"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  />
                  <path
                    class="orb-imgpick__spinner-head"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                {{ _t('Saving…') }}
              </div>
              <div v-else-if="uploadError" class="orb-imgpick__error">
                {{ uploadError }}
              </div>
            </div>
          </Transition>
        </template>

        <!-- No search match -->
        <div v-else-if="!filtered.length" class="orb-imgpick__no-match">
          {{ _t('No boards match "%{q}"', { q: query }) }}
        </div>

        <!-- Image grid + upload button at bottom -->
        <template v-else>
          <div class="orb-imgpick__grid">
            <button
              v-for="image in filtered"
              :key="image.name"
              type="button"
              class="orb-imgpick__tile"
              :class="modelValue === image.name ? 'orb-imgpick__tile--selected' : ''"
              :title="image.name"
              @click="select(image.name)"
            >
              <img
                :src="`${BASE_URL}${image.url}`"
                :alt="image.name"
                class="orb-imgpick__thumb"
                :class="image.builtin && image.name.endsWith('.svg') ? 'svg-icon' : ''"
              />
              <span class="orb-imgpick__tile-name">{{ image.name }}</span>
            </button>
          </div>

          <!-- Upload more -->
          <div class="orb-imgpick__footer">
            <span class="orb-imgpick__count">{{ countLabel }}</span>
            <label class="orb-imgpick__upload-link">
              <svg
                class="orb-imgpick__upload-icon orb-imgpick__upload-icon--sm"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2.5"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                />
              </svg>
              {{ uploadLabel }}
              <input
                type="file"
                accept="image/png,image/jpeg,image/svg+xml,image/webp"
                multiple
                class="orb-imgpick__file-input"
                @change="uploadImages"
              />
            </label>
            <div v-if="uploading" class="orb-imgpick__footer-uploading">
              <svg
                class="orb-imgpick__spinner orb-imgpick__spinner--xs"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="orb-imgpick__spinner-track"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                />
                <path
                  class="orb-imgpick__spinner-head"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            </div>
          </div>
        </template>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { imagesApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { ImageEntry } from '@/types/api'
import usei18n from '@/vendor/cmk/lib/i18n'

const BASE_URL = import.meta.env.BASE_URL

const { _t, _tn } = usei18n()
const auth = useAuthStore()

const props = defineProps<{
  modelValue: string
  /** Override the placeholder label shown when no image is selected. */
  placeholder?: string
  /** 'icon' (default) offers the full library including built-in icons;
   * 'image' hides them — 24px monochrome icons are no slide background. */
  kind?: 'icon' | 'image'
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const emptyLabel = computed(() => props.placeholder ?? _t('Icon filename'))
const isImageKind = computed(() => props.kind === 'image')
const searchLabel = computed(() => (isImageKind.value ? _t('Search images…') : _t('Search icons…')))
const uploadLabel = computed(() => (isImageKind.value ? _t('Upload image') : _t('Upload icon')))
const countLabel = computed(() => {
  const n = images.value.length
  return isImageKind.value
    ? _tn('%{n} image', '%{n} images', n, { n })
    : _tn('%{n} icon', '%{n} icons', n, { n })
})

const open = ref(false)
const query = ref('')
const allImages = ref<ImageEntry[]>([])
const loading = ref(false)
const uploading = ref(false)
const uploadError = ref('')

const images = computed(() =>
  isImageKind.value ? allImages.value.filter((i) => !i.builtin) : allImages.value
)

const filtered = computed(() =>
  query.value
    ? images.value.filter((i) => i.name.toLowerCase().includes(query.value.toLowerCase()))
    : images.value
)

// Only built-in (monochrome) SVG icons get theme-inverted in dark mode;
// uploaded SVGs keep their own colours.
const selectedIsBuiltinSvg = computed(() => {
  if (!props.modelValue?.endsWith('.svg')) return false
  return allImages.value.find((i) => i.name === props.modelValue)?.builtin ?? false
})

async function fetchImages() {
  loading.value = true
  try {
    allImages.value = await imagesApi.list(auth.accessToken!)
  } catch {
    allImages.value = []
  } finally {
    loading.value = false
  }
}

async function uploadImages(event: Event) {
  const files = (event.target as HTMLInputElement).files
  if (!files?.length) return
  uploadError.value = ''
  uploading.value = true
  try {
    for (const file of Array.from(files)) {
      await imagesApi.upload(file, auth.accessToken!)
    }
    await fetchImages()
  } catch (e: unknown) {
    uploadError.value = e instanceof Error ? e.message : 'Upload failed'
  } finally {
    uploading.value = false
    ;(event.target as HTMLInputElement).value = ''
  }
}

function select(name: string) {
  emit('update:modelValue', name)
  open.value = false
  query.value = ''
}

watch(open, (isOpen) => {
  if (isOpen && !images.value.length) fetchImages()
})
</script>

<style scoped>
.orb-imgpick > * + * {
  margin-top: var(--dimension-4);
}

.orb-imgpick__selected {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  padding: var(--dimension-4) var(--dimension-5);
  background: var(--default-form-element-bg-color);
  border-radius: 8px;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 50%, transparent);
}

.orb-imgpick__thumb {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  object-fit: contain;
}

.orb-imgpick__selected-name {
  flex: 1;
  overflow: hidden;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-imgpick__clear {
  color: var(--text-muted);
  transition: color 0.15s;
}

.orb-imgpick__clear:hover {
  color: var(--text);
}

.orb-imgpick__clear-icon {
  width: 14px;
  height: 14px;
}

.orb-imgpick__toggle {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  width: 100%;
  padding: var(--dimension-4) var(--dimension-5);
  font-size: var(--font-size-large);
  line-height: 20px;
  text-align: left;
  background: var(--default-form-element-bg-color);
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--default-form-element-border-color);
  transition: all 0.15s;
}

.orb-imgpick__toggle:focus {
  outline: none;
  box-shadow: 0 0 0 1px var(--color-corporate-green-50);
}

.orb-imgpick__toggle-icon {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  color: var(--text-muted);
}

.orb-imgpick__toggle-label {
  color: var(--text-muted);
}

.orb-imgpick__chevron {
  width: 14px;
  height: 14px;
  margin-left: auto;
  color: var(--text-muted);
  transition: transform 0.15s;
}

.orb-imgpick__chevron--open {
  transform: rotate(180deg);
}

.orb-imgpick__panel {
  overflow: hidden;
  background: var(--bg-surface);
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.orb-imgpick__panel-enter-from,
.orb-imgpick__panel-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.orb-imgpick__panel-enter-active {
  transition: all 0.2s cubic-bezier(0, 0, 0.2, 1);
}

.orb-imgpick__panel-leave-active {
  transition: all 0.15s cubic-bezier(0.4, 0, 1, 1);
}

.orb-imgpick__search-wrap {
  padding: var(--dimension-4);
  border-bottom: 1px solid var(--border);
}

.orb-imgpick__search {
  padding: 6px 10px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  border-radius: 6px;
}

.orb-imgpick__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-4);
  padding: var(--dimension-8) 0;
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text-muted);
}

.orb-imgpick__spinner {
  width: 16px;
  height: 16px;
  color: var(--color-corporate-green-50);
  animation: orb-imgpick-spin 1s linear infinite;
}

.orb-imgpick__spinner--sm {
  width: 14px;
  height: 14px;
}

.orb-imgpick__spinner--xs {
  width: 12px;
  height: 12px;
}

.orb-imgpick__spinner-track {
  opacity: 0.25;
}

.orb-imgpick__spinner-head {
  opacity: 0.75;
}

.orb-imgpick__empty {
  padding: var(--dimension-7) var(--dimension-6) var(--dimension-5);
  text-align: center;
}

.orb-imgpick__empty-icon {
  display: block;
  width: 32px;
  height: 32px;
  margin: 0 auto var(--dimension-4);
  color: var(--text-muted);
}

.orb-imgpick__empty-text {
  margin-bottom: var(--dimension-5);
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text-muted);
}

.orb-imgpick__upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px var(--dimension-5);
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: 600;
  color: var(--button-primary-text-color, #000);
  cursor: pointer;
  background: var(--color-corporate-green-50);
  border-radius: 8px;
  transition: all 0.15s;
}

.orb-imgpick__upload-btn:hover {
  background: var(--color-corporate-green-60);
}

.orb-imgpick__upload-icon {
  width: 14px;
  height: 14px;
}

.orb-imgpick__upload-icon--sm {
  width: 12px;
  height: 12px;
}

.orb-imgpick__file-input {
  display: none;
}

.orb-imgpick__status {
  padding: 0 var(--dimension-5) var(--dimension-5);
}

.orb-imgpick__status-enter-from,
.orb-imgpick__status-leave-to {
  max-height: 0;
  opacity: 0;
}

.orb-imgpick__status-enter-active {
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0, 0, 0.2, 1);
}

.orb-imgpick__status-leave-active {
  overflow: hidden;
  transition: all 0.2s cubic-bezier(0.4, 0, 1, 1);
}

.orb-imgpick__uploading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-4);
  padding: var(--dimension-3) 0;
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text-muted);
}

.orb-imgpick__error {
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--color-light-red-40);
  text-align: center;
}

.orb-imgpick__no-match {
  padding: var(--dimension-7) 0;
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text-muted);
  text-align: center;
}

.orb-imgpick__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--dimension-3);
  max-height: 208px;
  padding: var(--dimension-4);
  overflow-y: auto;
}

.orb-imgpick__tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--dimension-3);
  padding: 6px;
  border-radius: 8px;
  transition: all 0.15s;
}

.orb-imgpick__tile:hover {
  background: var(--bg-hover);
}

.orb-imgpick__tile--selected {
  background: color-mix(in srgb, var(--color-corporate-green-50) 10%, transparent);
  box-shadow: 0 0 0 1px var(--color-corporate-green-50);
}

.orb-imgpick__tile-name {
  width: 100%;
  overflow: hidden;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: 9px;
  line-height: 1.25;
  color: var(--text-muted);
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-imgpick__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--dimension-4);
  border-top: 1px solid var(--border);
}

.orb-imgpick__count {
  font-size: 10px;
  color: var(--text-muted);
}

.orb-imgpick__upload-link {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-3) var(--dimension-4);
  font-size: 10px;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s;
}

.orb-imgpick__upload-link:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.orb-imgpick__footer-uploading {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  font-size: 10px;
  color: var(--text-muted);
}

@keyframes orb-imgpick-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
