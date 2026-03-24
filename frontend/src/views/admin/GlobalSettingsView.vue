<template>
  <div class="max-w-2xl">
    <div class="mb-8">
      <h2 class="text-xl font-bold text-[var(--text)] tracking-tight">{{ t('settings.title') }}</h2>
      <p class="text-sm text-zinc-500 mt-1">{{ t('settings.subtitle') }}</p>
    </div>

    <div
      v-if="store.loading"
      class="flex items-center gap-2 text-zinc-500 text-sm py-8 justify-center"
    >
      <svg class="animate-spin w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      {{ t('common.loading') }}
    </div>

    <div v-else class="space-y-6">
      <!-- Object defaults -->
      <section class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl p-6">
        <h3 class="text-sm font-semibold text-zinc-400 mb-5">
          {{ t('settings.objectDefaults') }}
        </h3>

        <div class="space-y-5">
          <!-- Appearance -->
          <div class="flex flex-wrap gap-x-4 gap-y-3 items-start">
            <label class="block">
              <span class="text-xs text-zinc-400 mb-1 block">{{ t('board.iconSize') }}</span>
              <NumberInput v-model="form.icon_size" min="8" max="256" class="w-20" />
            </label>

            <label class="block">
              <span class="text-xs text-zinc-400 mb-1 block">{{
                t('boardSettings.viewType')
              }}</span>
              <select v-model="form.view_type" class="select w-40">
                <option value="icon">{{ t('boardSettings.viewTypeIcon') }}</option>
                <option value="text">{{ t('boardSettings.viewTypeText') }}</option>
                <option value="gadget">{{ t('boardSettings.viewTypeGadget') }}</option>
              </select>
            </label>

            <label class="block">
              <span class="text-xs text-zinc-400 mb-1 block">{{ t('boardSettings.z') }}</span>
              <NumberInput v-model="form.z" min="1" max="999" class="w-20" />
              <p class="text-xs text-zinc-600 mt-1">{{ t('settings.zHint') }}</p>
            </label>
          </div>

          <!-- Line + Link -->
          <div
            class="border-t border-[var(--border)] pt-4 flex flex-wrap gap-x-4 gap-y-3 items-start"
          >
            <label class="block">
              <span class="text-xs text-zinc-400 mb-1 block">{{
                t('boardSettings.lineStyle')
              }}</span>
              <select v-model="form.line_style" class="select w-44">
                <option :value="null">{{ t('boardSettings.lineDefault') }}</option>
                <option value="plain">{{ t('boardSettings.lineSimple') }}</option>
                <option value="arrow_end">{{ t('boardSettings.lineArrowRight') }}</option>
                <option value="arrow_start">{{ t('boardSettings.lineArrowLeft') }}</option>
                <option value="arrow_both">{{ t('boardSettings.lineDoubleArrow') }}</option>
                <option value="dashed">{{ t('boardSettings.lineDashed') }}</option>
                <option value="weathermap">{{ t('boardSettings.lineWeathermap') }}</option>
              </select>
            </label>

            <label class="block">
              <span class="text-xs text-zinc-400 mb-1 block">{{ t('boardSettings.target') }}</span>
              <select v-model="form.url_target" class="select w-40">
                <option value="_blank">{{ t('boardSettings.targetNewTab') }}</option>
                <option value="_self">{{ t('boardSettings.targetSameTab') }}</option>
                <option value="_top">{{ t('boardSettings.targetTopFrame') }}</option>
              </select>
            </label>
          </div>
        </div>
      </section>

      <!-- Label defaults -->
      <section class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl p-6">
        <h3 class="text-sm font-semibold text-zinc-400 mb-5">
          {{ t('settings.labelDefaults') }}
        </h3>

        <div class="space-y-5">
          <!-- Show label -->
          <label class="flex items-center gap-3 cursor-pointer">
            <input
              v-model="form.label_show"
              type="checkbox"
              class="w-4 h-4 rounded accent-indigo-500"
            />
            <span class="text-sm text-[var(--text)]">{{ t('boardSettings.showLabel') }}</span>
          </label>

          <!-- Appearance + Position (grayed out when label hidden) -->
          <div
            :class="[
              'space-y-5 transition-opacity',
              form.label_show ? '' : 'opacity-40 pointer-events-none',
            ]"
          >
            <div class="flex flex-wrap gap-x-4 gap-y-3 items-start">
              <label class="block">
                <span class="text-xs text-zinc-400 mb-1 block"
                  >{{ t('boardSettings.size') }} (px)</span
                >
                <NumberInput v-model="form.label_size" min="6" max="72" class="w-20" />
              </label>

              <label class="block">
                <span class="text-xs text-zinc-400 mb-1 block">{{ t('boardSettings.color') }}</span>
                <div class="flex gap-2">
                  <input
                    v-model="form.label_color"
                    type="color"
                    class="w-10 h-9 rounded cursor-pointer bg-[var(--bg)] border border-[var(--border)]"
                  />
                  <input
                    v-model="form.label_color"
                    type="text"
                    placeholder="#ffffff"
                    class="w-28 bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </label>

              <label class="block">
                <span class="text-xs text-zinc-400 mb-1 block">{{
                  t('boardSettings.background')
                }}</span>
                <div class="flex gap-2">
                  <input
                    type="color"
                    :value="
                      form.label_background === 'transparent' ? '#000000' : form.label_background
                    "
                    :disabled="form.label_background === 'transparent'"
                    class="w-10 h-9 rounded cursor-pointer bg-[var(--bg)] border border-[var(--border)] disabled:opacity-40"
                    @input="form.label_background = ($event.target as HTMLInputElement).value"
                  />
                  <input
                    v-model="form.label_background"
                    type="text"
                    placeholder="transparent"
                    class="w-32 bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </label>
            </div>

            <div class="border-t border-[var(--border)] pt-4 flex gap-4 items-start">
              <label class="block">
                <span class="text-xs text-zinc-400 mb-1 block">{{
                  t('boardSettings.offsetX')
                }}</span>
                <NumberInput v-model="form.label_x" class="w-20" />
              </label>
              <label class="block">
                <span class="text-xs text-zinc-400 mb-1 block">{{
                  t('boardSettings.offsetY')
                }}</span>
                <NumberInput v-model="form.label_y" class="w-20" />
              </label>
            </div>
          </div>
        </div>
      </section>

      <!-- New board defaults -->
      <section class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl p-6">
        <h3 class="text-sm font-semibold text-zinc-400 mb-5">
          {{ t('settings.newBoardDefaults') }}
        </h3>

        <div class="flex flex-wrap gap-x-6 gap-y-4 items-start">
          <!-- Default backend -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('board.connection') }}</span>
            <select v-model="form.default_backend_id" class="select w-48">
              <option v-for="b in connectionsStore.backends" :key="b.id" :value="b.id">
                {{ b.label || b.id }}
              </option>
              <option v-if="connectionsStore.backends.length === 0" value="live_1">live_1</option>
            </select>
          </label>

          <!-- Default board type -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('board.boardType') }}</span>
            <select v-model="form.default_map_type" class="select w-44">
              <option value="static">{{ t('board.boardTypeStatic') }}</option>
              <option value="worldmap">{{ t('board.boardTypeGeoBoard') }}</option>
              <option value="automap">{{ t('board.boardTypeFlowBoard') }}</option>
              <option value="radar">{{ t('board.boardTypeRadar') }}</option>
            </select>
          </label>
        </div>
      </section>

      <!-- Templates -->
      <section class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl p-6">
        <h3 class="text-sm font-semibold text-zinc-400 mb-1">
          {{ t('settings.templates') }}
        </h3>
        <p class="text-xs text-zinc-600 mb-5">{{ t('settings.templatesSubtitle') }}</p>

        <div class="space-y-4">
          <!-- Hover template -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('settings.hoverTemplate') }}</span>
            <input
              v-model="form.hover_template"
              type="text"
              :placeholder="t('board.templatePlaceholder')"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] font-mono placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </label>

          <!-- Context template -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{
              t('settings.contextTemplate')
            }}</span>
            <input
              v-model="form.context_template"
              type="text"
              :placeholder="t('board.templatePlaceholder')"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] font-mono placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </label>
        </div>
      </section>

      <p v-if="saveError" class="text-sm text-red-400">{{ saveError }}</p>

      <div class="flex items-center justify-end gap-3">
        <Transition
          enter-from-class="opacity-0 translate-x-2"
          enter-active-class="transition-all duration-200"
          leave-to-class="opacity-0"
          leave-active-class="transition-opacity duration-300"
        >
          <span v-if="savedOk" class="flex items-center gap-1.5 text-sm text-green-400">
            <svg
              class="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2.5"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
            {{ t('common.saved') }}
          </span>
        </Transition>
        <button
          class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all"
          @click="resetForm"
        >
          {{ t('common.cancel') }}
        </button>
        <button
          :disabled="saving"
          class="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-all duration-150 shadow-lg shadow-indigo-900/20"
          @click="handleSave"
        >
          {{ saving ? t('common.saving') : t('common.save') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import NumberInput from '@/components/NumberInput.vue'
import { useConnectionsStore } from '@/stores/connections'
import { useSettingsStore } from '@/stores/settings'
import type { GlobalSettings } from '@/types/api'

const { t } = useI18n()
const store = useSettingsStore()
const connectionsStore = useConnectionsStore()

const form = reactive<GlobalSettings>({ ...store.settings })
const saving = ref(false)
const saveError = ref('')
const savedOk = ref(false)
let savedOkTimer: ReturnType<typeof setTimeout> | null = null

// Sync form when store finishes loading
watch(
  () => store.settings,
  (val) => Object.assign(form, val),
  { deep: true },
)

function resetForm() {
  Object.assign(form, store.settings)
  savedOk.value = false
  saveError.value = ''
}

async function handleSave() {
  saving.value = true
  saveError.value = ''
  savedOk.value = false
  try {
    await store.save({ ...form })
    savedOk.value = true
    if (savedOkTimer) clearTimeout(savedOkTimer)
    savedOkTimer = setTimeout(() => {
      savedOk.value = false
    }, 3000)
  } catch {
    saveError.value = t('admin.saveFailed')
  } finally {
    saving.value = false
  }
}

onUnmounted(() => {
  if (savedOkTimer) clearTimeout(savedOkTimer)
})

onMounted(async () => {
  await Promise.all([store.load(), connectionsStore.fetchBackends()])
  Object.assign(form, store.settings)
  // Force the connection <select> to pick up the value after options are rendered
  await nextTick()
  const saved = form.default_backend_id
  form.default_backend_id = ''
  await nextTick()
  form.default_backend_id = saved
})
</script>

<style scoped>
.select {
  @apply bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500;
}
</style>
