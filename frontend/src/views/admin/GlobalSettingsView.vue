<template>
  <div>
    <div class="flex justify-between items-center mb-8">
      <div>
        <h2 class="text-xl font-bold text-[var(--text)] tracking-tight">{{ t('settings.title') }}</h2>
        <p class="text-sm text-zinc-500 mt-1">{{ t('settings.subtitle') }}</p>
      </div>
      <button @click="handleSave" :disabled="saving"
        class="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-all duration-150 shadow-lg shadow-indigo-900/20">
        {{ saving ? t('common.saving') : t('common.save') }}
      </button>
    </div>

    <div v-if="store.loading" class="flex items-center gap-2 text-zinc-500 text-sm py-8 justify-center">
      <svg class="animate-spin w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      {{ t('common.loading') }}
    </div>

    <div v-else class="space-y-6">

      <!-- Object defaults -->
      <section class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl p-6">
        <h3 class="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-5">
          {{ t('settings.objectDefaults') }}
        </h3>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">

          <!-- Icon size -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('map.iconSize') }}</span>
            <NumberInput v-model="form.icon_size" min="8" max="256" class="w-24" />
          </label>

          <!-- View type -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('mapSettings.viewType') }}</span>
            <select v-model="form.view_type"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500">
              <option value="icon">{{ t('mapSettings.viewTypeIcon') }}</option>
              <option value="text">{{ t('mapSettings.viewTypeText') }}</option>
              <option value="gadget">{{ t('mapSettings.viewTypeGadget') }}</option>
            </select>
          </label>

          <!-- Line type -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('mapSettings.lineStyle') }}</span>
            <select v-model="form.line_type"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500">
              <option :value="null">{{ t('mapSettings.lineDefault') }}</option>
              <option :value="10">{{ t('mapSettings.lineSimple') }}</option>
              <option :value="11">{{ t('mapSettings.lineArrowRight') }}</option>
              <option :value="12">{{ t('mapSettings.lineArrowLeft') }}</option>
              <option :value="13">{{ t('mapSettings.lineDoubleArrow') }}</option>
              <option :value="14">{{ t('mapSettings.lineDashed') }}</option>
              <option :value="15">{{ t('mapSettings.lineWeathermap') }}</option>
            </select>
          </label>

          <!-- URL target -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('mapSettings.target') }}</span>
            <select v-model="form.url_target"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500">
              <option value="_blank">{{ t('mapSettings.targetNewTab') }}</option>
              <option value="_self">{{ t('mapSettings.targetSameTab') }}</option>
              <option value="_top">{{ t('mapSettings.targetTopFrame') }}</option>
            </select>
          </label>

          <!-- Z-index -->
          <div class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('mapSettings.z') }}</span>
            <NumberInput v-model="form.z" min="1" max="999" class="w-20" />
            <p class="text-xs text-zinc-600 mt-1">{{ t('settings.zHint') }}</p>
          </div>

          <!-- Show label -->
          <label class="flex items-center gap-3 cursor-pointer pt-4">
            <input v-model="form.label_show" type="checkbox"
              class="w-4 h-4 rounded accent-indigo-500" />
            <span class="text-sm text-[var(--text)]">{{ t('mapSettings.showLabel') }}</span>
          </label>
        </div>
      </section>

      <!-- Label defaults -->
      <section class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl p-6">
        <h3 class="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-5">
          {{ t('settings.labelDefaults') }}
        </h3>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">

          <!-- Label size -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('mapSettings.size') }} (px)</span>
            <NumberInput v-model="form.label_size" min="6" max="72" class="w-24" />
          </label>

          <!-- Label color -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('mapSettings.color') }}</span>
            <div class="flex gap-2">
              <input v-model="form.label_color" type="color"
                class="w-10 h-9 rounded cursor-pointer bg-[var(--bg)] border border-[var(--border)]" />
              <input v-model="form.label_color" type="text"
                class="flex-1 bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500" />
            </div>
          </label>

          <!-- Label background -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('mapSettings.background') }}</span>
            <div class="flex gap-2">
              <input v-model="form.label_background" type="color"
                :disabled="form.label_background === 'transparent'"
                class="w-10 h-9 rounded cursor-pointer bg-[var(--bg)] border border-[var(--border)] disabled:opacity-40" />
              <input v-model="form.label_background" type="text"
                placeholder="transparent"
                class="flex-1 bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500" />
            </div>
          </label>

          <!-- Label offset X/Y -->
          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="text-xs text-zinc-400 mb-1 block">{{ t('mapSettings.offsetX') }}</span>
              <NumberInput v-model="form.label_x" class="w-24" />
            </label>
            <label class="block">
              <span class="text-xs text-zinc-400 mb-1 block">{{ t('mapSettings.offsetY') }}</span>
              <NumberInput v-model="form.label_y" class="w-24" />
            </label>
          </div>
        </div>
      </section>

      <!-- New map defaults -->
      <section class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl p-6">
        <h3 class="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-5">
          {{ t('settings.newMapDefaults') }}
        </h3>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">

          <!-- Default backend -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('map.backend') }}</span>
            <select v-model="form.default_backend_id"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500">
                      <option v-for="b in backendsStore.backends" :key="b.id" :value="b.id">
                {{ b.label || b.id }}
              </option>
              <option v-if="backendsStore.backends.length === 0" value="live_1">live_1</option>
            </select>
          </label>

          <!-- Default map type -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('map.mapType') }}</span>
            <select v-model="form.default_map_type"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500">
              <option value="static">{{ t('map.mapTypeStatic') }}</option>
              <option value="worldmap">{{ t('map.mapTypeWorldmap') }}</option>
              <option value="automap">{{ t('map.mapTypeAutomap') }}</option>
              <option value="radar">{{ t('map.mapTypeRadar') }}</option>
            </select>
          </label>

          <!-- Hover template -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('settings.hoverTemplate') }}</span>
            <input v-model="form.hover_template" type="text" :placeholder="t('common.noData')"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500" />
          </label>

          <!-- Context template -->
          <label class="block">
            <span class="text-xs text-zinc-400 mb-1 block">{{ t('settings.contextTemplate') }}</span>
            <input v-model="form.context_template" type="text" :placeholder="t('common.noData')"
              class="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-indigo-500" />
          </label>
        </div>
      </section>

      <p v-if="saveError" class="text-sm text-red-400">{{ saveError }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import NumberInput from '@/components/NumberInput.vue'
import { useSettingsStore } from '@/stores/settings'
import { useBackendsStore } from '@/stores/backends'
import type { GlobalSettings } from '@/types/api'

const { t } = useI18n()
const store = useSettingsStore()
const backendsStore = useBackendsStore()

const form = reactive<GlobalSettings>({ ...store.settings })
const saving = ref(false)
const saveError = ref('')

// Sync form when store finishes loading
watch(
  () => store.settings,
  (val) => Object.assign(form, val),
  { deep: true },
)

async function handleSave() {
  saving.value = true
  saveError.value = ''
  try {
    await store.save({ ...form })
  } catch {
    saveError.value = t('admin.saveFailed')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all([store.load(), backendsStore.fetchBackends()])
  Object.assign(form, store.settings)
})
</script>
