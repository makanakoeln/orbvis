<template>
  <div class="orb-bgupload">
    <!-- Preview when a background is set or staged -->
    <div v-if="hasImage" class="orb-bgupload__preview">
      <img
        v-if="!previewFailed && displayUrl"
        :src="displayUrl"
        class="orb-bgupload__thumb"
        @error="previewFailed = true"
      />
      <div v-else-if="previewFailed" class="orb-bgupload__thumb-fallback">?</div>
      <span class="orb-bgupload__name">
        {{ displayName }}
        <span v-if="pendingFile" class="orb-bgupload__unsaved">
          · {{ t('board.backgroundUnsaved') }}
        </span>
      </span>
      <label class="orb-bgupload__replace">
        {{ t('board.replaceBackground') }}
        <input
          type="file"
          :accept="ACCEPT_TYPES"
          class="orb-bgupload__file-input"
          @change="onFileChange"
        />
      </label>
      <button
        type="button"
        class="orb-bgupload__remove"
        :title="pendingFile ? t('common.cancel') : t('board.deleteBackground')"
        @click="removeOrCancel"
      >
        <svg
          class="orb-bgupload__remove-icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2.5"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Upload button when empty (or pending removal) -->
    <label v-else class="orb-bgupload__upload">
      <svg
        class="orb-bgupload__upload-icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
        />
      </svg>
      {{ t('board.uploadBackground') }}
      <input
        type="file"
        :accept="ACCEPT_TYPES"
        class="orb-bgupload__file-input"
        @change="onFileChange"
      />
    </label>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const ACCEPT_TYPES = 'image/png,image/jpeg,image/svg+xml,image/webp,image/gif'

const { t } = useI18n()

const props = defineProps<{
  // Filename of the background already persisted on the server (display base).
  modelValue: string
  // Staged selection: uploaded/deleted only when the parent saves the board.
  pendingFile: File | null
  pendingRemove: boolean
  // data: URL of the staged file, provided by the parent. A data: URL (not a
  // blob:) is required because Checkmk's CSP allows ``img-src ... data:`` but
  // not blob:, so a blob: thumbnail would be silently blocked on OMD sites.
  pendingPreviewUrl?: string | null
}>()
const emit = defineEmits<{
  'update:pendingFile': [value: File | null]
  'update:pendingRemove': [value: boolean]
}>()

const BASE_URL = import.meta.env.BASE_URL
const cacheBust = ref(Date.now())
const previewFailed = ref(false)

watch(
  () => props.pendingFile,
  () => {
    previewFailed.value = false
  }
)
watch(
  () => props.modelValue,
  () => {
    previewFailed.value = false
    cacheBust.value = Date.now()
  }
)

const hasImage = computed(() =>
  props.pendingFile ? true : props.pendingRemove ? false : !!props.modelValue
)
const displayUrl = computed(() =>
  props.pendingFile
    ? (props.pendingPreviewUrl ?? '')
    : `${BASE_URL}boards/backgrounds/${props.modelValue}?v=${cacheBust.value}`
)
const displayName = computed(() => props.pendingFile?.name ?? props.modelValue)

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  emit('update:pendingRemove', false)
  emit('update:pendingFile', file)
}

function removeOrCancel() {
  if (props.pendingFile) {
    // Undo the staged pick, falling back to the persisted image.
    emit('update:pendingFile', null)
    return
  }
  emit('update:pendingRemove', true)
}
</script>

<style scoped>
.orb-bgupload > * + * {
  margin-top: var(--dimension-4);
}

.orb-bgupload__preview {
  display: flex;
  align-items: center;
  gap: var(--dimension-5);
  padding: var(--dimension-4) var(--dimension-5);
  background: var(--default-form-element-bg-color);
  border-radius: 8px;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 50%, transparent);
}

.orb-bgupload__thumb {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 4px;
}

.orb-bgupload__thumb-fallback {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  font-size: 10px;
  color: var(--text-muted);
  background: var(--bg-hover);
  border-radius: 4px;
}

.orb-bgupload__name {
  flex: 1;
  min-width: 0;
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

.orb-bgupload__unsaved {
  color: var(--text-muted);
}

.orb-bgupload__replace {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-3) var(--dimension-4);
  font-size: 11px;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 6px;
  transition:
    color 0.15s,
    background-color 0.15s;
}

.orb-bgupload__replace:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.orb-bgupload__file-input {
  display: none;
}

.orb-bgupload__remove {
  color: var(--text-muted);
  transition: color 0.15s;
}

.orb-bgupload__remove:hover {
  color: var(--color-light-red-40);
}

.orb-bgupload__remove-icon {
  width: 14px;
  height: 14px;
}

.orb-bgupload__upload {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-4);
  width: 100%;
  padding: var(--dimension-4) var(--dimension-5);
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
  cursor: pointer;
  background: var(--default-form-element-bg-color);
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--default-form-element-border-color);
  transition: all 0.15s;
}

.orb-bgupload__upload:hover {
  color: var(--text);
  box-shadow: 0 0 0 1px var(--color-corporate-green-50);
}

.orb-bgupload__upload:focus-within {
  box-shadow: 0 0 0 1px var(--color-corporate-green-50);
}

.orb-bgupload__upload-icon {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
}
</style>
