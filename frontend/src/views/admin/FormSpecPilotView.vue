<template>
    <div class="max-w-2xl">
        <CmkHeading type="h2">FormSpec Pilot</CmkHeading>
        <CmkParagraph class="admin-subtitle">
            End-to-end test of the FormSpec stack: backend ships the schema, the vendored FormEdit
            dispatcher renders it, save round-trips through the existing settings API. Replaces the
            hand-built GlobalSettings view once the pilot proves out.
        </CmkParagraph>

        <div v-if="loading" class="flex items-center justify-center py-8">
            <CmkLoading />
        </div>

        <div v-else-if="loadError" class="text-sm text-[var(--color-light-red-40)]">
            {{ loadError }}
        </div>

        <template v-else-if="schema">
            <div class="formspec-pilot__form">
                <FormEdit v-model:data="data" :spec="schema" :backend-validation="validation" />
            </div>

            <div
                class="flex items-center justify-end gap-[8px]"
                style="margin-top: var(--dimension-5)"
            >
                <Transition
                    enter-from-class="opacity-0 translate-x-2"
                    enter-active-class="transition-all duration-200"
                    leave-to-class="opacity-0"
                    leave-active-class="transition-opacity duration-300"
                >
                    <span v-if="savedOk" class="text-sm text-[var(--color-corporate-green-50)]">
                        {{ t('common.saved') }}
                    </span>
                </Transition>
                <span v-if="saveError" class="text-sm text-[var(--color-light-red-40)]">{{
                    saveError
                }}</span>
                <CmkButton variant="secondary" @click="resetForm">
                    {{ t('common.cancel') }}
                </CmkButton>
                <CmkButton variant="primary" :disabled="saving" @click="handleSave">
                    {{ saving ? t('common.saving') : t('common.save') }}
                </CmkButton>
            </div>
        </template>
    </div>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkLoading from '@cmk/components/CmkLoading.vue';
import CmkHeading from '@cmk/components/typography/CmkHeading.vue';
import CmkParagraph from '@cmk/components/typography/CmkParagraph.vue';
import FormEdit from '@cmk/form/FormEdit.vue';
import { initializeComponentRegistry } from '@cmk/form/private/FormEditDispatcher/dispatch';
import type { VueFormspecComponents } from 'cmk-shared-typing/typescript/vue_formspec_components';
import { onMounted, onUnmounted, ref } from 'vue';
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
        initialData.value = JSON.parse(JSON.stringify(values));
        data.value = JSON.parse(JSON.stringify(values));
    } catch (e: unknown) {
        loadError.value = e instanceof Error ? e.message : 'Failed to load settings';
    } finally {
        loading.value = false;
    }
}

function resetForm() {
    data.value = JSON.parse(JSON.stringify(initialData.value));
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
        initialData.value = JSON.parse(JSON.stringify(updated));
        data.value = JSON.parse(JSON.stringify(updated));
        savedOk.value = true;
        if (savedOkTimer) clearTimeout(savedOkTimer);
        savedOkTimer = setTimeout(() => {
            savedOk.value = false;
        }, 3000);
    } catch (e: unknown) {
        saveError.value = e instanceof Error ? e.message : 'Save failed';
    } finally {
        saving.value = false;
    }
}

onMounted(load);

onUnmounted(() => {
    if (savedOkTimer) clearTimeout(savedOkTimer);
});
</script>

<style scoped>
.formspec-pilot__form {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: var(--dimension-6);
}
</style>
