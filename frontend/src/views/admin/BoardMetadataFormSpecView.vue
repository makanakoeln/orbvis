<template>
    <div class="max-w-2xl">
        <CmkHeading type="h2">{{ t('board.settingsTitle') }}</CmkHeading>
        <CmkParagraph class="admin-subtitle">
            FormSpec-driven metadata editor for board
            <code>{{ boardName }}</code
            >. Type-specific view geometry (worldmap, flow, radar) and the background image stay in
            the existing custom editor.
        </CmkParagraph>

        <div v-if="loading" class="flex items-center justify-center py-8">
            <CmkLoading />
        </div>

        <div v-else-if="loadError" class="text-sm text-[var(--color-light-red-40)]">
            {{ loadError }}
        </div>

        <template v-else-if="schema">
            <div class="board-form__form">
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
                <CmkButton variant="secondary" @click="cancel">
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
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';

import { boardsApiFormSpec } from '@/api/client';
import { useAuthStore } from '@/stores/auth';

type Schema = NonNullable<VueFormspecComponents['components']>;
type Validation = NonNullable<VueFormspecComponents['validation_message']>[];

initializeComponentRegistry();

const { t } = useI18n();
const auth = useAuthStore();
const route = useRoute();
const router = useRouter();

const boardName = ref(String(route.params.name ?? ''));
const loading = ref(true);
const loadError = ref('');
const saving = ref(false);
const saveError = ref('');
const savedOk = ref(false);
const schema = ref<Schema | null>(null);
const data = ref<Record<string, unknown>>({});
const initialData = ref<Record<string, unknown>>({});
const validation = ref<Validation>([]);

let savedOkTimer: ReturnType<typeof setTimeout> | null = null;

async function load() {
    const token = auth.accessToken;
    if (!token) {
        loadError.value = 'Not authenticated';
        loading.value = false;
        return;
    }
    loading.value = true;
    loadError.value = '';
    try {
        const [spec, values] = await Promise.all([
            boardsApiFormSpec.getMetadataSchema(token),
            boardsApiFormSpec.getMetadata(boardName.value, token),
        ]);
        schema.value = spec as unknown as Schema;
        initialData.value = JSON.parse(JSON.stringify(values));
        data.value = JSON.parse(JSON.stringify(values));
    } catch (e: unknown) {
        loadError.value = e instanceof Error ? e.message : 'Failed to load board';
    } finally {
        loading.value = false;
    }
}

async function handleSave() {
    const token = auth.accessToken;
    if (!token) return;
    saving.value = true;
    saveError.value = '';
    savedOk.value = false;
    try {
        await boardsApiFormSpec.updateMetadata(boardName.value, data.value, token);
        initialData.value = JSON.parse(JSON.stringify(data.value));
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

function cancel() {
    router.push({ name: 'home' });
}

watch(
    () => route.params.name,
    (n) => {
        boardName.value = String(n ?? '');
        load();
    },
);

onMounted(load);

onUnmounted(() => {
    if (savedOkTimer) clearTimeout(savedOkTimer);
});
</script>

<style scoped>
.board-form__form {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: var(--dimension-6);
}
</style>
