<template>
  <div class="orb-images">
    <div class="orb-images__header">
      <div>
        <CmkHeading type="h2">
          {{ _t('Images') }}
        </CmkHeading>
        <CmkParagraph class="admin-subtitle">
          {{ _t('Upload and manage images for board objects') }}
        </CmkParagraph>
      </div>
      <CmkButton variant="primary" @click="fileInputEl?.click()">
        <svg
          style="width: 13px; height: 13px; margin-right: var(--dimension-3)"
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
        {{ _t('Upload Image') }}
      </CmkButton>
      <input
        ref="fileInputEl"
        type="file"
        accept="image/png,image/jpeg,image/svg+xml,image/webp"
        multiple
        class="orb-images__file-input"
        @change="uploadIcons"
      />
    </div>

    <!-- Upload feedback -->
    <CmkAlertBox v-if="uploadError" variant="error">{{ uploadError }}</CmkAlertBox>

    <!-- Image is not in use → simple confirm dialog. -->
    <OrbConfirmDialog
      :open="dialogReady && !!deleteTargetName && !pendingUsage.length"
      :title="
        deleteTargetName ? _t('Delete image &quot;%{name}&quot;?', { name: deleteTargetName }) : ''
      "
      :message="_t('This cannot be undone.')"
      :confirm-label="_t('Delete')"
      @confirm="confirmDeleteIcon"
      @cancel="cancelDelete"
    />

    <!-- Image is referenced by N boards → CMK SlideIn with link cards.
             Mirrors CMK's WATO pattern (see watolib/timeperiods.py +
             CmkSlideInDialog/CmkLinkCard) so a long usage list scrolls
             gracefully and operators can jump to each affected board. -->
    <CmkSlideInDialog
      :open="dialogReady && !!deleteTargetName && pendingUsage.length > 0"
      :header="{
        title: _t('Image is still in use'),
        icon: { name: 'warning', size: 'large' },
        closeButton: true
      }"
      size="medium"
      border-color="warning"
      @close="cancelDelete"
    >
      <div class="image-usage-pane">
        <CmkParagraph class="image-usage-pane__intro">
          {{
            _t(
              'The image "%{name}" is referenced by %{count} board(s). Deleting it will leave those boards without an image. Continue?',
              {
                name: deleteTargetName ?? '',
                count: pendingUsage.length
              }
            )
          }}
        </CmkParagraph>
        <CmkLinkCardContainer>
          <CmkLinkCard
            v-for="entry in pendingUsage"
            :key="entry.board"
            icon-name="dashboard-main"
            :title="entry.alias || entry.board"
            :subtitle="usageSubtitle(entry)"
            :url="boardUrl(entry)"
            :open-in-new-tab="true"
          />
        </CmkLinkCardContainer>
        <div class="image-usage-pane__actions">
          <CmkButton variant="secondary" @click="cancelDelete">
            {{ _t('Cancel') }}
          </CmkButton>
          <CmkButton variant="warning" @click="confirmDeleteIcon">
            {{ _t('Delete') }}
          </CmkButton>
        </div>
      </div>
    </CmkSlideInDialog>

    <div v-if="loading" class="orb-images__loading">
      <CmkLoading />
    </div>

    <template v-else>
      <!-- Search bar (mirrors the ImagePicker search styling so both
                 surfaces feel like the same product). -->
      <div class="image-search" style="margin-bottom: var(--dimension-6)">
        <svg
          class="image-search__icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"
          />
        </svg>
        <input
          v-model="query"
          type="text"
          :placeholder="_t('Search images…')"
          class="image-search__input"
        />
      </div>

      <!-- Custom uploads first — operator's own material is the most
                 actionable bucket on this page. -->
      <section style="margin-bottom: var(--dimension-7)">
        <CmkHeading type="h3" class="section-title">
          {{ _t('Uploaded images') }} ({{ filteredCustom.length }})
        </CmkHeading>
        <div v-if="!customIcons.length" class="orb-images__empty">
          {{ _t('No images uploaded yet — upload to add custom icons') }}
        </div>
        <div v-else-if="!filteredCustom.length" class="orb-images__no-matches">
          {{ _t('No matches for "%{q}"', { q: query }) }}
        </div>
        <div v-else class="orb-images__grid">
          <div v-for="icon in filteredCustom" :key="icon.name" class="orb-images__tile">
            <img
              :src="`${BASE_URL}${icon.url}`"
              :alt="icon.name"
              class="orb-images__img"
              :class="icon.name.endsWith('.svg') ? 'svg-icon' : ''"
            />
            <p class="orb-images__name" :title="icon.name">
              {{ icon.name }}
            </p>
            <button
              class="orb-images__delete"
              :title="_t('Delete')"
              @click="onDeleteClick(icon.name)"
            >
              <svg
                style="width: 12px; height: 12px"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2.5"
              >
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </section>

      <!-- Built-in library — read-only, no per-tile badge needed: the
                 section header already conveys the category. -->
      <section>
        <CmkHeading type="h3" class="section-title">
          {{ _t('Built-in icons') }} ({{ filteredBuiltin.length }})
        </CmkHeading>
        <div v-if="!filteredBuiltin.length" class="orb-images__no-matches">
          {{ _t('No matches for "%{q}"', { q: query }) }}
        </div>
        <div v-else class="orb-images__grid">
          <div v-for="icon in filteredBuiltin" :key="icon.name" class="orb-images__tile">
            <img
              :src="`${BASE_URL}${icon.url}`"
              :alt="icon.name"
              class="orb-images__img"
              :class="icon.name.endsWith('.svg') ? 'svg-icon' : ''"
            />
            <p class="orb-images__name" :title="icon.name">
              {{ icon.name }}
            </p>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import OrbConfirmDialog from '@/components/OrbConfirmDialog.vue'
import CmkAlertBox from '@/components/cmk/CmkAlertBox'
import CmkButton from '@/components/cmk/CmkButton'
import CmkLinkCard from '@/components/cmk/CmkLinkCard/CmkLinkCard'
import CmkLinkCardContainer from '@/components/cmk/CmkLinkCard/CmkLinkCardContainer'
import CmkLoading from '@/components/cmk/CmkLoading'
import CmkSlideInDialog from '@/components/cmk/CmkSlideInDialog'
import CmkHeading from '@/components/cmk/typography/CmkHeading'
import CmkParagraph from '@/components/cmk/typography/CmkParagraph'

import { ApiError, imagesApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { ImageEntry, ImageUsageEntry } from '@/types/api'
import usei18n from '@cmk/lib/i18n'

const BASE_URL = import.meta.env.BASE_URL
const { _t, _tn } = usei18n()
const auth = useAuthStore()

const fileInputEl = ref<HTMLInputElement | null>(null)
const icons = ref<ImageEntry[]>([])
const loading = ref(false)
const uploadError = ref('')
const query = ref('')

const customIcons = computed(() => icons.value.filter((i) => !i.builtin))
const builtinIcons = computed(() => icons.value.filter((i) => i.builtin))

function matchesQuery(name: string): boolean {
  const q = query.value.trim().toLowerCase()
  return q === '' || name.toLowerCase().includes(q)
}

const filteredCustom = computed(() => customIcons.value.filter((i) => matchesQuery(i.name)))
const filteredBuiltin = computed(() => builtinIcons.value.filter((i) => matchesQuery(i.name)))

async function fetchIcons() {
  loading.value = true
  try {
    icons.value = await imagesApi.list(auth.accessToken!)
  } finally {
    loading.value = false
  }
}

async function uploadIcons(event: Event) {
  const files = (event.target as HTMLInputElement).files
  if (!files?.length) return
  uploadError.value = ''
  try {
    const results = await Promise.allSettled(
      Array.from(files).map((file) => imagesApi.upload(file, auth.accessToken!))
    )
    await fetchIcons()
    const failed = results.find((r): r is PromiseRejectedResult => r.status === 'rejected')
    if (failed) {
      uploadError.value = failed.reason instanceof Error ? failed.reason.message : 'Upload failed'
    }
  } catch (e: unknown) {
    uploadError.value = e instanceof Error ? e.message : 'Upload failed'
  }
  ;(event.target as HTMLInputElement).value = ''
}

const deleteTargetName = ref<string | null>(null)
const pendingUsage = ref<ImageUsageEntry[]>([])
// Gate the dialog until the usage check resolves — otherwise the simple
// "delete?" prompt flashes briefly before the in-use warning takes over.
const dialogReady = ref(false)

async function onDeleteClick(name: string) {
  deleteTargetName.value = name
  pendingUsage.value = []
  dialogReady.value = false
  try {
    const usage = await imagesApi.usage(name, auth.accessToken!)
    if (usage.length) pendingUsage.value = usage
  } catch {
    // best-effort: fall through to confirm dialog if usage check fails
  } finally {
    // Only open the dialog after we know whether the image is in use, so
    // we never have to swap the dialog content under the user.
    if (deleteTargetName.value === name) dialogReady.value = true
  }
}

function usageSubtitle(entry: ImageUsageEntry): string {
  const parts: string[] = []
  if (entry.is_background) parts.push(_t('as background'))
  if (entry.object_ids.length)
    parts.push(
      _tn('%{n} object', '%{n} objects', entry.object_ids.length, { n: entry.object_ids.length })
    )
  return parts.join(', ')
}

function boardUrl(entry: ImageUsageEntry): string {
  // Hash router: build a full URL so target=_blank opens the right route in
  // a new tab (a bare "#/boards/..." would resolve against the current
  // location and stay in-tab on some browsers).
  return `${window.location.pathname}#/boards/${entry.board}`
}

function cancelDelete() {
  deleteTargetName.value = null
  pendingUsage.value = []
  dialogReady.value = false
}

async function confirmDeleteIcon() {
  const name = deleteTargetName.value
  if (!name) return
  // Force=true when usage was detected; the user just confirmed via the
  // in-use warning. Without force the backend rejects with 409.
  const force = pendingUsage.value.length > 0
  try {
    await imagesApi.delete(name, auth.accessToken!, force)
    icons.value = icons.value.filter((i) => i.name !== name)
    cancelDelete()
  } catch (e: unknown) {
    if (e instanceof ApiError && e.status === 409) {
      // Server-side double-check picked up usage we didn't see locally.
      const detail = e.detail as { usage?: ImageUsageEntry[] } | null
      if (detail?.usage?.length) {
        pendingUsage.value = detail.usage
        return
      }
    }
    uploadError.value = e instanceof Error ? e.message : 'Delete failed'
    cancelDelete()
  }
}

onMounted(fetchIcons)
</script>

<style scoped>
.orb-images__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--dimension-6);
}

.orb-images__file-input {
  display: none;
}

.orb-images__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 0;
}

.orb-images__empty {
  padding: 28px 0;
  font-size: var(--font-size-large);
  line-height: 20px;
  text-align: center;
  color: var(--text-muted);
}

.orb-images__no-matches {
  padding: var(--dimension-5) 0;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-images__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: var(--dimension-4);
}

.orb-images__tile {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: var(--dimension-4);
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 0 0 1px var(--border);
  transition: all 0.15s;
}

.orb-images__tile:hover {
  box-shadow: 0 0 0 1px var(--default-form-element-border-color);
}

.orb-images__img {
  width: 40px;
  height: 40px;
  object-fit: contain;
}

.orb-images__name {
  width: 100%;
  overflow: hidden;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: 10px;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-muted);
}

.orb-images__delete {
  position: absolute;
  top: 4px;
  right: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  color: var(--text-muted);
  background: transparent;
  border-radius: 4px;
  opacity: 0;
  transition: all 0.15s;
}

.orb-images__delete:hover {
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 20%, transparent);
}

.orb-images__tile:hover .orb-images__delete {
  opacity: 1;
}

.image-usage-pane {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  padding-bottom: var(--dimension-6);
}

.image-usage-pane__intro {
  line-height: 1.5;
}

.image-usage-pane__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--dimension-3);
  padding-top: var(--dimension-4);
  border-top: 1px solid var(--border);
  position: sticky;
  bottom: 0;
  background: var(--bg-surface);
}

.section-title {
  font-size: var(--font-size-normal);
  color: var(--text-muted);
  margin-bottom: var(--dimension-4);
}

.image-search {
  position: relative;
  max-width: 320px;
}

.image-search__icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 14px;
  height: 14px;
  color: var(--text-muted);
  pointer-events: none;
}

.image-search__input {
  width: 100%;
  padding: 6px 12px 6px 30px;
  background: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-border-color);
  border-radius: var(--border-radius);
  color: var(--text);
  font-size: var(--font-size-small);
  transition: border-color 0.15s;
}

.image-search__input::placeholder {
  color: var(--default-form-element-placeholder-color);
}

.image-search__input:focus {
  outline: none;
  border-color: var(--color-corporate-green-50);
}
</style>
