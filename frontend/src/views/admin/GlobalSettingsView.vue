<template>
    <div class="settings-page">
        <div class="settings-page__header">
            <CmkHeading type="h2">{{ heading }}</CmkHeading>
            <CmkParagraph v-if="subtitle" class="admin-subtitle">{{ subtitle }}</CmkParagraph>
        </div>

        <div v-if="loading" class="flex items-center justify-center py-16">
            <CmkLoading />
        </div>

        <CmkAlertBox v-else-if="loadError" variant="error">{{ loadError }}</CmkAlertBox>

        <div v-else-if="schema" class="settings-page__layout">
            <nav class="settings-page__sidebar" aria-label="Settings sections">
                <button
                    v-for="g in groups"
                    :key="g.key"
                    type="button"
                    class="settings-page__topic"
                    :class="{ 'settings-page__topic--active': g.key === activeGroup }"
                    @click="activeGroup = g.key"
                >
                    {{ g.title }}
                </button>
            </nav>

            <div class="settings-page__detail" :data-active="activeGroup">
                <FormEdit v-model:data="data" :spec="schema" :backend-validation="validation" />
            </div>
        </div>

        <OrbSaveBar
            v-if="!loading && schema"
            :dirty="dirty"
            :saving="saving"
            :saved-ok="savedOk"
            :error="saveError"
            @save="handleSave"
            @cancel="resetForm"
        />
    </div>
</template>

<script setup lang="ts">
import CmkAlertBox from '@cmk/components/CmkAlertBox.vue';
import CmkLoading from '@cmk/components/CmkLoading.vue';
import CmkHeading from '@cmk/components/typography/CmkHeading.vue';
import CmkParagraph from '@cmk/components/typography/CmkParagraph.vue';
import FormEdit from '@cmk/form/FormEdit.vue';
import type { VueFormspecComponents } from 'cmk-shared-typing/typescript/vue_formspec_components';
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { settingsApi } from '@/api/client';
import OrbSaveBar from '@/components/OrbSaveBar.vue';
import { useFormSpecSchema } from '@/composables/useFormSpecSchema';
import { useAuthStore } from '@/stores/auth';
import type { GlobalSettings } from '@/types/api';

type Validation = NonNullable<VueFormspecComponents['validation_message']>[];

interface SchemaElement {
    name: string;
    group?: { key?: string | null; title?: string | null } | null;
}
interface DictionarySchema {
    elements?: SchemaElement[];
    title?: string;
    help?: string;
}

const { t } = useI18n();
const auth = useAuthStore();

const {
    schema,
    error: schemaError,
    load: loadSchema,
} = useFormSpecSchema('settings', () => settingsApi.getSchema(auth.accessToken ?? ''));

const loading = ref(true);
const loadError = ref('');
const saving = ref(false);
const saveError = ref('');
const savedOk = ref(false);
const data = ref<unknown>({});
const initialData = ref<unknown>({});
const validation = ref<Validation>([]);
const activeGroup = ref<string>('');

let savedOkTimer: ReturnType<typeof setTimeout> | null = null;
let saveErrorTimer: ReturnType<typeof setTimeout> | null = null;

const dirty = computed(() => JSON.stringify(data.value) !== JSON.stringify(initialData.value));

const heading = computed(
    () => (schema.value as DictionarySchema | null)?.title ?? t('settings.title'),
);
const subtitle = computed(
    () => (schema.value as DictionarySchema | null)?.help || t('settings.subtitle'),
);

const groups = computed<{ key: string; title: string }[]>(() => {
    const dict = schema.value as DictionarySchema | null;
    if (!dict?.elements) return [];
    const seen = new Map<string, string>();
    for (const el of dict.elements) {
        const key = el.group?.key ?? '-ungrouped-';
        if (!seen.has(key)) seen.set(key, el.group?.title || key);
    }
    return Array.from(seen.entries()).map(([key, title]) => ({ key, title }));
});

async function load() {
    const token = auth.accessToken;
    if (!token) {
        loadError.value = 'Not authenticated';
        loading.value = false;
        return;
    }
    try {
        const [, values] = await Promise.all([loadSchema(), settingsApi.get(token)]);
        if (schemaError.value) {
            loadError.value = schemaError.value;
            return;
        }
        initialData.value = structuredClone(values);
        data.value = structuredClone(values);
        // pre-select first group so the detail panel is never empty
        activeGroup.value = groups.value[0]?.key ?? '';
    } catch (e: unknown) {
        loadError.value = e instanceof Error ? e.message : 'Failed to load settings';
    } finally {
        loading.value = false;
    }
}

function resetForm() {
    data.value = structuredClone(initialData.value);
    savedOk.value = false;
    saveError.value = '';
}

async function handleSave() {
    const token = auth.accessToken;
    if (!token) return;
    saving.value = true;
    saveError.value = '';
    savedOk.value = false;
    try {
        const updated = await settingsApi.update(data.value as GlobalSettings, token);
        initialData.value = structuredClone(updated);
        data.value = structuredClone(updated);
        savedOk.value = true;
        if (savedOkTimer) clearTimeout(savedOkTimer);
        savedOkTimer = setTimeout(() => {
            savedOk.value = false;
        }, 3000);
    } catch (e: unknown) {
        saveError.value = e instanceof Error ? e.message : t('admin.saveFailed');
        if (saveErrorTimer) clearTimeout(saveErrorTimer);
        saveErrorTimer = setTimeout(() => {
            saveError.value = '';
        }, 5000);
    } finally {
        saving.value = false;
    }
}

onMounted(load);
onUnmounted(() => {
    if (savedOkTimer) clearTimeout(savedOkTimer);
    if (saveErrorTimer) clearTimeout(saveErrorTimer);
});
</script>

<style scoped>
.settings-page {
    display: flex;
    flex-direction: column;
    min-height: 100%;
}

.settings-page__header {
    padding: 0 var(--dimension-8) var(--dimension-6);
}

.settings-page__layout {
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: var(--dimension-7);
    padding: 0 var(--dimension-8);
    flex: 1;
    align-items: start;
    min-height: 0;
}

/* Topic sidebar — WATO-style vertical nav with active-state highlight. */
.settings-page__sidebar {
    display: flex;
    flex-direction: column;
    gap: 2px;
    position: sticky;
    top: 0;
    align-self: start;
}

.settings-page__topic {
    text-align: left;
    background: none;
    border: 0;
    border-left: 3px solid transparent;
    padding: var(--dimension-3) var(--dimension-5);
    font-size: 14px;
    color: var(--text-muted);
    cursor: pointer;
    transition:
        background-color 120ms,
        color 120ms,
        border-color 120ms;
}

.settings-page__topic:hover {
    background: var(--bg-hover, rgb(255 255 255 / 4%));
    color: var(--text);
}

.settings-page__topic--active {
    border-left-color: var(--color-corporate-green-50);
    background: rgb(21 209 160 / 12%);
    color: var(--text);
    font-weight: 600;
}

/* Hide every group <tr> by default, then re-show the active one. Vue's
   :deep() weakens specificity, so we hoist this rule with !important — the
   alternative (v-show inside the vendored FormDictionary) would require a
   bigger vendor patch. */
.settings-page__detail :deep(tr[data-group]) {
    display: none !important;
}

.settings-page__detail[data-active='board_defaults'] :deep(tr[data-group='board_defaults']),
.settings-page__detail[data-active='system'] :deep(tr[data-group='system']),
.settings-page__detail[data-active='defaults'] :deep(tr[data-group='defaults']),
.settings-page__detail[data-active='labels'] :deep(tr[data-group='labels']),
.settings-page__detail[data-active='templates'] :deep(tr[data-group='templates']) {
    display: table-row !important;
}

/* Bigger group title (h3-ish) and visible help line under it, since the
   sidebar already establishes the section context. */
.settings-page__detail :deep(.form-dictionary__group-title) {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: var(--dimension-2);
    padding: 0;
    border: 0;
}

.settings-page__detail :deep(.form-help) {
    color: var(--text-muted);
    margin-bottom: var(--dimension-6);
}

/* Consistent input width — kills the "60px Integer next to 432px String" mix. */
.settings-page__detail :deep(.cmk-input--text),
.settings-page__detail :deep(.cmk-dropdown__choice-button),
.settings-page__detail :deep(input[type='text']) {
    min-width: 320px;
    max-width: 100%;
}

.settings-page__error-msg {
    font-size: 13px;
    color: var(--color-light-red-40);
}
</style>
