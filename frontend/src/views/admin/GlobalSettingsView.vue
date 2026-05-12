<template>
    <div class="max-w-2xl">
        <div style="margin-bottom: 16px">
            <CmkHeading type="h2">
                {{ t('settings.title') }}
            </CmkHeading>
            <CmkParagraph class="admin-subtitle">
                {{ t('settings.subtitle') }}
            </CmkParagraph>
        </div>

        <div v-if="store.loading" class="flex items-center justify-center py-8">
            <CmkLoading />
        </div>

        <div v-else class="space-y-[16px]">
            <!-- Object defaults -->
            <section
                class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden"
            >
                <button
                    class="w-full flex items-center justify-between text-left"
                    style="padding: 14px 16px"
                    @click="sectionOpen.objectDefaults = !sectionOpen.objectDefaults"
                >
                    <h3 class="text-base font-semibold text-[var(--text-muted)]">
                        {{ t('settings.objectDefaults') }}
                    </h3>
                    <svg
                        style="
                            width: 14px;
                            height: 14px;
                            flex-shrink: 0;
                            transition: transform 200ms;
                        "
                        :style="{ transform: sectionOpen.objectDefaults ? 'rotate(180deg)' : '' }"
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
                <CmkCollapsible :open="sectionOpen.objectDefaults">
                    <div class="space-y-[12px]" style="padding: 0 16px 14px">
                        <div class="flex flex-wrap gap-x-[12px] gap-y-[8px] items-start">
                            <label class="block">
                                <span
                                    class="text-sm text-[var(--text-muted)] block"
                                    style="margin-bottom: 3px"
                                    >{{ t('board.iconSize') }}</span
                                >
                                <NumberInput
                                    v-model="form.icon_size"
                                    min="8"
                                    max="256"
                                    class="w-[80px]"
                                />
                            </label>

                            <label class="block">
                                <span
                                    class="text-sm text-[var(--text-muted)] block"
                                    style="margin-bottom: 3px"
                                    >{{ t('boardSettings.viewType') }}</span
                                >
                                <CmkToggleButtonGroup
                                    v-model="form.view_type"
                                    :options="[
                                        { value: 'icon', label: t('boardSettings.viewTypeIcon') },
                                        { value: 'text', label: t('boardSettings.viewTypeText') },
                                        {
                                            value: 'gadget',
                                            label: t('boardSettings.viewTypeGadget'),
                                        },
                                    ]"
                                />
                            </label>

                            <label class="block">
                                <span
                                    class="text-sm text-[var(--text-muted)] block"
                                    style="margin-bottom: 3px"
                                    >{{ t('boardSettings.z') }}</span
                                >
                                <NumberInput v-model="form.z" min="1" max="999" class="w-[80px]" />
                                <p class="text-sm text-[var(--text-muted)]" style="margin-top: 4px">
                                    {{ t('settings.zHint') }}
                                </p>
                            </label>
                        </div>

                        <div
                            class="border-t border-[var(--border)] pt-[12px] flex flex-wrap gap-x-[12px] gap-y-[8px] items-start"
                        >
                            <label class="block">
                                <span
                                    class="text-sm text-[var(--text-muted)] block"
                                    style="margin-bottom: 3px"
                                    >{{ t('boardSettings.lineStyle') }}</span
                                >
                                <CmkDropdown
                                    class="w-[176px]"
                                    :selected-option="form.line_style ?? null"
                                    :options="lineStyleOpts"
                                    label=""
                                    @update:selected-option="
                                        (v) => {
                                            form.line_style = (v as LineStyle) || null;
                                        }
                                    "
                                />
                            </label>

                            <label class="block">
                                <span
                                    class="text-sm text-[var(--text-muted)] block"
                                    style="margin-bottom: 3px"
                                    >{{ t('boardSettings.target') }}</span
                                >
                                <CmkToggleButtonGroup
                                    v-model="form.url_target"
                                    :options="[
                                        { value: '_blank', label: t('boardSettings.targetNewTab') },
                                        { value: '_self', label: t('boardSettings.targetSameTab') },
                                        { value: '_top', label: t('boardSettings.targetTopFrame') },
                                    ]"
                                />
                            </label>
                        </div>
                    </div>
                </CmkCollapsible>
            </section>

            <!-- Label defaults -->
            <section
                class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden"
            >
                <button
                    class="w-full flex items-center justify-between text-left"
                    style="padding: 14px 16px"
                    @click="sectionOpen.labelDefaults = !sectionOpen.labelDefaults"
                >
                    <h3 class="text-base font-semibold text-[var(--text-muted)]">
                        {{ t('settings.labelDefaults') }}
                    </h3>
                    <svg
                        style="
                            width: 14px;
                            height: 14px;
                            flex-shrink: 0;
                            transition: transform 200ms;
                        "
                        :style="{ transform: sectionOpen.labelDefaults ? 'rotate(180deg)' : '' }"
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
                <CmkCollapsible :open="sectionOpen.labelDefaults">
                    <div class="space-y-[12px]" style="padding: 0 16px 14px">
                        <CmkCheckbox
                            v-model="form.label_show"
                            :label="t('boardSettings.showLabel')"
                        />
                        <div
                            :class="[
                                'space-y-[12px] transition-opacity',
                                form.label_show ? '' : 'opacity-40 pointer-events-none',
                            ]"
                        >
                            <div class="flex flex-wrap gap-x-[12px] gap-y-[8px] items-start">
                                <label class="block">
                                    <span
                                        class="text-sm text-[var(--text-muted)] block"
                                        style="margin-bottom: 3px"
                                        >{{ t('boardSettings.size') }} (px)</span
                                    >
                                    <NumberInput
                                        v-model="form.label_size"
                                        min="6"
                                        max="72"
                                        class="w-[80px]"
                                    />
                                </label>

                                <label class="block">
                                    <span
                                        class="text-sm text-[var(--text-muted)] block"
                                        style="margin-bottom: 3px"
                                        >{{ t('boardSettings.color') }}</span
                                    >
                                    <div class="flex gap-[8px]">
                                        <CmkColorPicker
                                            :data="form.label_color"
                                            @update:data="form.label_color = $event"
                                        />
                                        <CmkInput
                                            v-model="form.label_color"
                                            placeholder="#ffffff"
                                            field-size="SMALL"
                                        />
                                    </div>
                                </label>

                                <label class="block">
                                    <span
                                        class="text-sm text-[var(--text-muted)] block"
                                        style="margin-bottom: 3px"
                                        >{{ t('boardSettings.background') }}</span
                                    >
                                    <div class="flex gap-[8px]">
                                        <CmkColorPicker
                                            :data="
                                                form.label_background === 'transparent'
                                                    ? '#000000'
                                                    : form.label_background
                                            "
                                            @update:data="form.label_background = $event"
                                        />
                                        <CmkInput
                                            v-model="form.label_background"
                                            placeholder="transparent"
                                            field-size="MEDIUM"
                                        />
                                    </div>
                                </label>
                            </div>

                            <div
                                class="border-t border-[var(--border)] pt-[12px] flex gap-[12px] items-start"
                            >
                                <label class="block">
                                    <span
                                        class="text-sm text-[var(--text-muted)] block"
                                        style="margin-bottom: 3px"
                                        >{{ t('boardSettings.offsetX') }}</span
                                    >
                                    <NumberInput v-model="form.label_x" class="w-[80px]" />
                                </label>
                                <label class="block">
                                    <span
                                        class="text-sm text-[var(--text-muted)] block"
                                        style="margin-bottom: 3px"
                                        >{{ t('boardSettings.offsetY') }}</span
                                    >
                                    <NumberInput v-model="form.label_y" class="w-[80px]" />
                                </label>
                            </div>
                        </div>
                    </div>
                </CmkCollapsible>
            </section>

            <!-- New board defaults -->
            <section
                class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden"
            >
                <button
                    class="w-full flex items-center justify-between text-left"
                    style="padding: 14px 16px"
                    @click="sectionOpen.newBoardDefaults = !sectionOpen.newBoardDefaults"
                >
                    <h3 class="text-base font-semibold text-[var(--text-muted)]">
                        {{ t('settings.newBoardDefaults') }}
                    </h3>
                    <svg
                        style="
                            width: 14px;
                            height: 14px;
                            flex-shrink: 0;
                            transition: transform 200ms;
                        "
                        :style="{ transform: sectionOpen.newBoardDefaults ? 'rotate(180deg)' : '' }"
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
                <CmkCollapsible :open="sectionOpen.newBoardDefaults">
                    <div
                        class="flex flex-wrap gap-x-[12px] gap-y-[8px] items-start"
                        style="padding: 0 16px 14px"
                    >
                        <label class="block">
                            <span
                                class="text-sm text-[var(--text-muted)] block"
                                style="margin-bottom: 3px"
                                >{{ t('board.connection') }}</span
                            >
                            <CmkDropdown
                                class="w-[192px]"
                                :selected-option="form.default_backend_id || null"
                                :options="connectionOptions"
                                label=""
                                @update:selected-option="form.default_backend_id = $event ?? ''"
                            />
                        </label>

                        <label class="block">
                            <span
                                class="text-sm text-[var(--text-muted)] block"
                                style="margin-bottom: 3px"
                                >{{ t('board.boardType') }}</span
                            >
                            <CmkDropdown
                                class="w-[176px]"
                                :selected-option="form.default_map_type || null"
                                :options="mapTypeOptions"
                                label=""
                                @update:selected-option="form.default_map_type = $event ?? ''"
                            />
                        </label>
                    </div>
                </CmkCollapsible>
            </section>

            <!-- Templates -->
            <section
                class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden"
            >
                <button
                    class="w-full flex items-center justify-between text-left"
                    style="padding: 14px 16px"
                    @click="sectionOpen.templates = !sectionOpen.templates"
                >
                    <h3 class="text-base font-semibold text-[var(--text-muted)]">
                        {{ t('settings.templates') }}
                    </h3>
                    <svg
                        style="
                            width: 14px;
                            height: 14px;
                            flex-shrink: 0;
                            transition: transform 200ms;
                        "
                        :style="{ transform: sectionOpen.templates ? 'rotate(180deg)' : '' }"
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
                <CmkCollapsible :open="sectionOpen.templates">
                    <div class="space-y-[10px]" style="padding: 0 16px 14px">
                        <p class="text-sm text-[var(--text-muted)]">
                            {{ t('settings.templatesSubtitle') }}
                        </p>
                        <label class="block">
                            <span
                                class="text-sm text-[var(--text-muted)] block"
                                style="margin-bottom: 3px"
                                >{{ t('settings.hoverTemplate') }}</span
                            >
                            <CmkInput
                                v-model="form.hover_template"
                                :placeholder="t('board.templatePlaceholder')"
                                field-size="FILL"
                            />
                        </label>

                        <label class="block">
                            <span
                                class="text-sm text-[var(--text-muted)] block"
                                style="margin-bottom: 3px"
                                >{{ t('settings.contextTemplate') }}</span
                            >
                            <CmkInput
                                v-model="form.context_template"
                                :placeholder="t('board.templatePlaceholder')"
                                field-size="FILL"
                            />
                        </label>
                    </div>
                </CmkCollapsible>
            </section>

            <!-- Checkmk integration -->
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
                                class="text-sm text-[var(--text-muted)] block"
                                style="margin-bottom: 3px"
                                >{{ t('admin.checkmkUrl') }}</span
                            >
                            <CmkInput
                                v-model="form.checkmk_url"
                                placeholder="https://checkmk.example.com/mysite"
                                field-size="FILL"
                            />
                            <p class="text-sm text-[var(--text-muted)]" style="margin-top: 6px">
                                {{ t('settings.checkmkUrlHint') }}
                            </p>
                        </label>
                    </div>
                </CmkCollapsible>
            </section>

            <!-- Logging -->
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
                                class="text-sm text-[var(--text-muted)] block"
                                style="margin-bottom: 3px"
                                >{{ t('settings.logLevel') }}</span
                            >
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
                            <p class="text-sm text-[var(--text-muted)]" style="margin-top: 6px">
                                {{ t('settings.logLevelHint') }}
                            </p>
                        </label>
                    </div>
                </CmkCollapsible>
            </section>

            <p v-if="saveError" class="text-sm text-red-400">{{ saveError }}</p>

            <div class="flex items-center justify-end gap-[8px]">
                <Transition
                    enter-from-class="opacity-0 translate-x-2"
                    enter-active-class="transition-all duration-200"
                    leave-to-class="opacity-0"
                    leave-active-class="transition-opacity duration-300"
                >
                    <span v-if="savedOk" class="flex items-center gap-[5px] text-sm text-green-400">
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
import CmkColorPicker from '@cmk/components/CmkColorPicker.vue';
import CmkDropdown from '@cmk/components/CmkDropdown/CmkDropdown.vue';
import CmkLoading from '@cmk/components/CmkLoading.vue';
import CmkToggleButtonGroup from '@cmk/components/CmkToggleButtonGroup.vue';
import CmkCheckbox from '@cmk/components/user-input/CmkCheckbox.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import NumberInput from '@/components/NumberInput.vue';
import { useConnectionsStore } from '@/stores/connections';
import { useSettingsStore } from '@/stores/settings';
import type { GlobalSettings, LineStyle, LogLevel } from '@/types/api';
import { boardTypeOptions, lineStyleOptions } from '@/utils/dropdownOptions';

const { t } = useI18n();
const store = useSettingsStore();
const connectionsStore = useConnectionsStore();

const form = reactive<GlobalSettings>({ ...store.settings });
const saving = ref(false);
const saveError = ref('');
const savedOk = ref(false);
let savedOkTimer: ReturnType<typeof setTimeout> | null = null;
let saveErrorTimer: ReturnType<typeof setTimeout> | null = null;

// Open the first section by default — operators arriving on the page see
// what's configurable instead of an opaque list of collapsed headers.
const sectionOpen = reactive({
    objectDefaults: true,
    labelDefaults: false,
    newBoardDefaults: false,
    templates: false,
    checkmkIntegration: false,
    logging: false,
});

const connectionOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: connectionsStore.connections.length
        ? connectionsStore.connections.map((b) => ({ name: b.id, title: b.label || b.id }))
        : [{ name: 'live_1', title: 'live_1' }],
}));
const mapTypeOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: boardTypeOptions(t),
}));
const lineStyleOpts = computed(() => ({
    type: 'fixed' as const,
    suggestions: lineStyleOptions(t),
}));
const dirty = computed(() => JSON.stringify(form) !== JSON.stringify(store.settings));
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

// Sync form when store finishes loading
watch(
    () => store.settings,
    (val) => Object.assign(form, val),
    { deep: true },
);

function resetForm() {
    Object.assign(form, store.settings);
    savedOk.value = false;
    saveError.value = '';
}

async function handleSave() {
    saving.value = true;
    saveError.value = '';
    savedOk.value = false;
    try {
        await store.save({ ...form });
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
    await Promise.all([store.load(), connectionsStore.fetchConnections()]);
    Object.assign(form, store.settings);
});
</script>
