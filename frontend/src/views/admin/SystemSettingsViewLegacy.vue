<!--
    Legacy / non-FormSpec System Settings form.

    Restored from the System section of the pre-FormSpec
    GlobalSettingsView at git rev ``034578c~1`` (the last commit before
    the FormSpec admin views landed). Saves through the flat pydantic
    ``GET/PUT /api/v1/settings/system`` endpoints — those stay registered
    regardless of cmk.rulesets.v1 availability.

    Hidden by the GlobalSettingsView wrapper when ``form_specs`` is true
    (built-in / MKP); served as the active view when Standalone reports
    ``form_specs: false``.
-->
<template>
    <div class="max-w-2xl">
        <div style="margin-bottom: var(--dimension-6)">
            <CmkHeading type="h2">
                {{ t('system.title') }}
            </CmkHeading>
            <CmkParagraph class="admin-subtitle">
                {{ t('system.subtitle') }}
            </CmkParagraph>
        </div>

        <div v-if="store.loading" class="flex items-center justify-center py-8">
            <CmkLoading />
        </div>

        <div v-else>
            <div class="space-y-[16px]" style="margin-bottom: var(--dimension-6)">
                <section
                    class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden"
                >
                    <button
                        class="w-full flex items-center justify-between text-left"
                        style="padding: 14px 16px"
                        @click="sectionOpen.checkmkIntegration = !sectionOpen.checkmkIntegration"
                    >
                        <h3 class="text-base font-semibold text-[var(--text-muted)]">
                            {{ t('settings.checkmkIntegration') }}
                        </h3>
                        <svg
                            style="
                                width: 14px;
                                height: 14px;
                                flex-shrink: 0;
                                transition: transform 200ms;
                            "
                            :style="{
                                transform: sectionOpen.checkmkIntegration ? 'rotate(180deg)' : '',
                            }"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="2"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                            />
                        </svg>
                    </button>
                    <CmkCollapsible :open="sectionOpen.checkmkIntegration">
                        <div style="padding: 0 16px 14px">
                            <p class="text-sm text-[var(--text-muted)]" style="margin-bottom: 10px">
                                {{ t('settings.checkmkIntegrationSubtitle') }}
                            </p>
                            <label class="block">
                                <span
                                    class="text-sm text-[var(--text-muted)] inline-flex items-center gap-[2px]"
                                    style="margin-bottom: 3px"
                                >
                                    {{ t('admin.checkmkUrl') }}
                                    <CmkHelpText :help="t('settings.checkmkUrlHint')" />
                                </span>
                                <CmkInput
                                    v-model="checkmkUrl"
                                    placeholder="https://checkmk.example.com/mysite"
                                    field-size="FILL"
                                />
                            </label>
                        </div>
                    </CmkCollapsible>
                </section>

                <section
                    class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden"
                >
                    <button
                        class="w-full flex items-center justify-between text-left"
                        style="padding: 14px 16px"
                        @click="sectionOpen.logging = !sectionOpen.logging"
                    >
                        <h3 class="text-base font-semibold text-[var(--text-muted)]">
                            {{ t('settings.logging') }}
                        </h3>
                        <svg
                            style="
                                width: 14px;
                                height: 14px;
                                flex-shrink: 0;
                                transition: transform 200ms;
                            "
                            :style="{ transform: sectionOpen.logging ? 'rotate(180deg)' : '' }"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="2"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                            />
                        </svg>
                    </button>
                    <CmkCollapsible :open="sectionOpen.logging">
                        <div style="padding: 0 16px 14px">
                            <label class="block">
                                <span
                                    class="text-sm text-[var(--text-muted)] inline-flex items-center gap-[2px]"
                                    style="margin-bottom: 3px"
                                >
                                    {{ t('settings.logLevel') }}
                                    <CmkHelpText :help="t('settings.logLevelHint')" />
                                </span>
                                <CmkDropdown
                                    class="w-[240px]"
                                    :selected-option="form.log_level ?? null"
                                    :options="logLevelOptions"
                                    label=""
                                    @update:selected-option="
                                        (v) => {
                                            form.log_level = (v as LogLevel) || null;
                                        }
                                    "
                                />
                            </label>
                        </div>
                    </CmkCollapsible>
                </section>
            </div>

            <p v-if="saveError" class="text-sm text-[var(--color-light-red-40)]">{{ saveError }}</p>

            <div class="flex items-center justify-end gap-[8px]">
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
                            stroke-width="2"
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
                <CmkButton variant="secondary" :disabled="!dirty" @click="resetForm">{{
                    t('common.cancel')
                }}</CmkButton>
                <CmkButton variant="primary" :disabled="saving || !dirty" @click="handleSave">
                    {{ saving ? t('common.saving') : t('common.save') }}
                </CmkButton>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkCollapsible from '@cmk/components/CmkCollapsible/CmkCollapsible.vue';
import CmkDropdown from '@cmk/components/CmkDropdown/CmkDropdown.vue';
import CmkHelpText from '@cmk/components/CmkHelpText.vue';
import CmkLoading from '@cmk/components/CmkLoading.vue';
import CmkHeading from '@cmk/components/typography/CmkHeading.vue';
import CmkParagraph from '@cmk/components/typography/CmkParagraph.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { useSettingsStore } from '@/stores/settings';
import type { LogLevel, SystemSettings } from '@/types/api';

const { t } = useI18n();
const store = useSettingsStore();

// CmkInput's v-model is non-null string; SystemSettings.checkmk_url is
// ``string | null | undefined``. Bridge with a computed setter so empty
// input clears back to ``null`` on save.
const form = reactive<SystemSettings>({ ...store.system });
const checkmkUrl = computed({
    get: () => form.checkmk_url ?? '',
    set: (v: string) => {
        form.checkmk_url = v || null;
    },
});

const saving = ref(false);
const saveError = ref('');
const savedOk = ref(false);
let savedOkTimer: ReturnType<typeof setTimeout> | null = null;
let saveErrorTimer: ReturnType<typeof setTimeout> | null = null;

const sectionOpen = reactive({
    checkmkIntegration: true,
    logging: false,
});

const logLevelOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: [
        { name: 'DEBUG', title: 'DEBUG' },
        { name: 'INFO', title: 'INFO' },
        { name: 'WARNING', title: 'WARNING' },
        { name: 'ERROR', title: 'ERROR' },
        { name: 'CRITICAL', title: 'CRITICAL' },
    ],
}));

const dirty = computed(() => JSON.stringify(form) !== JSON.stringify(store.system));

watch(
    () => store.system,
    (val) => Object.assign(form, val),
    { deep: true },
);

function resetForm() {
    Object.assign(form, store.system);
    savedOk.value = false;
    saveError.value = '';
}

async function handleSave() {
    saving.value = true;
    saveError.value = '';
    savedOk.value = false;
    try {
        await store.saveSystem({ ...form });
        savedOk.value = true;
        if (savedOkTimer) clearTimeout(savedOkTimer);
        savedOkTimer = setTimeout(() => {
            savedOk.value = false;
        }, 3000);
    } catch {
        saveError.value = t('admin.saveFailed');
        if (saveErrorTimer) clearTimeout(saveErrorTimer);
        saveErrorTimer = setTimeout(() => {
            saveError.value = '';
        }, 5000);
    } finally {
        saving.value = false;
    }
}

onUnmounted(() => {
    if (savedOkTimer) clearTimeout(savedOkTimer);
    if (saveErrorTimer) clearTimeout(saveErrorTimer);
});

onMounted(async () => {
    await store.load();
    Object.assign(form, store.system);
});
</script>

<style scoped>
@reference "tailwindcss";

.group-heading {
    @apply text-sm font-semibold text-[var(--text-muted)] tracking-wider uppercase mb-[8px];
}
</style>
