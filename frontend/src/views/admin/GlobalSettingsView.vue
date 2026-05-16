<template>
    <div class="settings-page">
        <div class="settings-page__header">
            <CmkHeading type="h2">
                {{ heading }}
            </CmkHeading>
            <CmkParagraph v-if="subtitle" class="admin-subtitle">
                {{ subtitle }}
            </CmkParagraph>
        </div>

        <div v-if="loading" class="flex items-center justify-center py-8">
            <CmkLoading />
        </div>

        <CmkAlertBox v-else-if="loadError" variant="error">{{ loadError }}</CmkAlertBox>

        <template v-else-if="schema">
            <div class="settings-page__form">
                <FormEdit v-model:data="data" :spec="schema" :backend-validation="validation" />
            </div>

            <div class="settings-page__savebar">
                <span
                    v-if="dirty"
                    class="settings-page__dirty"
                    :title="t('settings.unsavedChangesHint')"
                >
                    {{ t('settings.unsavedChanges') }}
                </span>
                <Transition
                    enter-from-class="opacity-0 translate-x-2"
                    enter-active-class="transition-all duration-200"
                    leave-to-class="opacity-0"
                    leave-active-class="transition-opacity duration-300"
                >
                    <span
                        v-if="savedOk"
                        class="flex items-center gap-[5px] text-sm text-[var(--color-corporate-green-50)]"
                    >
                        <svg
                            style="width: 14px; height: 14px"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="2.5"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M4.5 12.75l6 6 9-13.5"
                            />
                        </svg>
                        {{ t('common.saved') }}
                    </span>
                </Transition>
                <span v-if="saveError" class="text-sm text-[var(--color-light-red-40)]">{{
                    saveError
                }}</span>
                <CmkButton variant="secondary" :disabled="!dirty" @click="resetForm">{{
                    t('common.cancel')
                }}</CmkButton>
                <CmkButton variant="primary" :disabled="saving || !dirty" @click="handleSave">
                    {{ saving ? t('common.saving') : t('common.save') }}
                </CmkButton>
            </div>
        </template>
    </div>
</template>

<script setup lang="ts">
import CmkAlertBox from '@cmk/components/CmkAlertBox.vue';
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkLoading from '@cmk/components/CmkLoading.vue';
import CmkHeading from '@cmk/components/typography/CmkHeading.vue';
import CmkParagraph from '@cmk/components/typography/CmkParagraph.vue';
import FormEdit from '@cmk/form/FormEdit.vue';
import { initializeComponentRegistry } from '@cmk/form/private/FormEditDispatcher/dispatch';
import type { VueFormspecComponents } from 'cmk-shared-typing/typescript/vue_formspec_components';
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { settingsApi } from '@/api/client';
import { useAuthStore } from '@/stores/auth';
import type { GlobalSettings } from '@/types/api';

type Schema = NonNullable<VueFormspecComponents['components']>;
type Validation = NonNullable<VueFormspecComponents['validation_message']>[];

initializeComponentRegistry();

const { t } = useI18n();
const auth = useAuthStore();

const loading = ref(true);
const loadError = ref('');
const saving = ref(false);
const saveError = ref('');
const savedOk = ref(false);
const schema = ref<Schema | null>(null);
const data = ref<unknown>({});
const initialData = ref<unknown>({});
const validation = ref<Validation>([]);

let savedOkTimer: ReturnType<typeof setTimeout> | null = null;
let saveErrorTimer: ReturnType<typeof setTimeout> | null = null;

const dirty = computed(() => JSON.stringify(data.value) !== JSON.stringify(initialData.value));

const heading = computed(() => {
    const s = schema.value as { title?: string } | null;
    return s?.title ?? t('settings.title');
});
const subtitle = computed(() => {
    const s = schema.value as { help?: string } | null;
    return s?.help || t('settings.subtitle');
});

async function load() {
    const token = auth.accessToken;
    if (!token) {
        loadError.value = 'Not authenticated';
        loading.value = false;
        return;
    }
    try {
        const [spec, values] = await Promise.all([
            settingsApi.getSchema(token),
            settingsApi.get(token),
        ]);
        schema.value = spec as unknown as Schema;
        initialData.value = structuredClone(values);
        data.value = structuredClone(values);
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
/* WATO-style page: header + form share one column, no Card wrapper.
   Wider column (72rem ~= 1152px) so a 1440px viewport doesn't feel half-empty,
   centered so the form lives in the optical centre of the page. */
.settings-page {
    max-width: 72rem;
    margin: 0 auto;
    padding-bottom: 8rem;
}

.settings-page__header {
    margin-bottom: var(--dimension-6);
}

/* WATO-style group dividers: bigger heading + horizontal rule between
   sections so the operator can see at a glance which group they're in. */
.settings-page__form :deep(.form-dictionary__group-title) {
    font-size: var(--font-size-large);
    font-weight: 600;
    margin-top: var(--dimension-6);
    padding-top: var(--dimension-5);
    padding-bottom: var(--dimension-3);
    border-top: 1px solid var(--border);
}

.settings-page__form
    :deep(table.form-dictionary > tbody > tr:first-of-type .form-dictionary__group-title) {
    margin-top: 0;
    padding-top: 0;
    border-top: 0;
}

/* Sticky action bar — WATO-style border-top instead of a floating card.
   Stays within the form column but with enough margin and visible border so
   it doesn't overlap content above. */
.settings-page__savebar {
    position: sticky;
    bottom: 0;
    z-index: 5;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: var(--dimension-4);
    margin-top: var(--dimension-7);
    padding: var(--dimension-4) 0;
    background: var(--bg-surface);
    border-top: 1px solid var(--border);
}

.settings-page__dirty {
    font-size: 0.85rem;
    color: var(--text-muted);
    margin-right: auto;
}
</style>
