<template>
    <div class="max-w-2xl">
        <div style="margin-bottom: var(--dimension-6)">
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

        <div v-else>
            <!-- Group: Defaults applied when creating a new board -->
            <h3 class="group-heading">{{ t('settings.groupBoardCreation') }}</h3>
            <div class="space-y-[16px]" style="margin-bottom: var(--dimension-6)">
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
                            :style="{
                                transform: sectionOpen.newBoardDefaults ? 'rotate(180deg)' : '',
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
            </div>

            <!-- Group: Defaults applied to objects rendered on a board -->
            <h3 class="group-heading">{{ t('settings.groupObjectDefaults') }}</h3>
            <div class="space-y-[16px]" style="margin-bottom: var(--dimension-6)">
                <!-- Icon defaults -->
                <section
                    class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden"
                >
                    <button
                        class="w-full flex items-center justify-between text-left"
                        style="padding: 14px 16px"
                        @click="sectionOpen.iconDefaults = !sectionOpen.iconDefaults"
                    >
                        <h3 class="text-base font-semibold text-[var(--text-muted)]">
                            {{ t('settings.iconDefaults') }}
                        </h3>
                        <svg
                            style="
                                width: 14px;
                                height: 14px;
                                flex-shrink: 0;
                                transition: transform 200ms;
                            "
                            :style="{ transform: sectionOpen.iconDefaults ? 'rotate(180deg)' : '' }"
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
                    <CmkCollapsible :open="sectionOpen.iconDefaults">
                        <div
                            class="flex flex-wrap gap-x-[12px] gap-y-[8px] items-start"
                            style="padding: 0 16px 14px"
                        >
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
                                    class="text-sm text-[var(--text-muted)] inline-flex items-center gap-[2px]"
                                    style="margin-bottom: 3px"
                                >
                                    {{ t('boardSettings.z') }}
                                    <CmkHelpText :help="t('settings.zHint')" />
                                </span>
                                <NumberInput v-model="form.z" min="1" max="999" class="w-[80px]" />
                            </label>
                        </div>
                    </CmkCollapsible>
                </section>

                <!-- Line defaults -->
                <section
                    class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden"
                >
                    <button
                        class="w-full flex items-center justify-between text-left"
                        style="padding: 14px 16px"
                        @click="sectionOpen.lineDefaults = !sectionOpen.lineDefaults"
                    >
                        <h3 class="text-base font-semibold text-[var(--text-muted)]">
                            {{ t('settings.lineDefaults') }}
                        </h3>
                        <svg
                            style="
                                width: 14px;
                                height: 14px;
                                flex-shrink: 0;
                                transition: transform 200ms;
                            "
                            :style="{ transform: sectionOpen.lineDefaults ? 'rotate(180deg)' : '' }"
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
                    <CmkCollapsible :open="sectionOpen.lineDefaults">
                        <div
                            class="flex flex-wrap gap-x-[12px] gap-y-[8px] items-start"
                            style="padding: 0 16px 14px"
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
                    </CmkCollapsible>
                </section>

                <!-- Label defaults — Show-label is a master toggle in the card header.
                 Header uses a div+role=button instead of a native <button> so we can
                 nest the CmkSwitch <label> (invalid HTML inside <button>). -->
                <section
                    class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden"
                >
                    <div
                        class="w-full flex items-center justify-between text-left cursor-pointer"
                        style="padding: 14px 16px"
                        role="button"
                        tabindex="0"
                        @click="sectionOpen.labelDefaults = !sectionOpen.labelDefaults"
                        @keydown.enter.prevent="
                            sectionOpen.labelDefaults = !sectionOpen.labelDefaults
                        "
                        @keydown.space.prevent="
                            sectionOpen.labelDefaults = !sectionOpen.labelDefaults
                        "
                    >
                        <h3 class="text-base font-semibold text-[var(--text-muted)]">
                            {{ t('settings.labelDefaults') }}
                        </h3>
                        <div class="flex items-center gap-[12px]" @click.stop>
                            <label
                                class="flex items-center gap-[6px] text-sm text-[var(--text-muted)] cursor-pointer"
                            >
                                <CmkSwitch v-model:data="form.label_show" />
                                <span>{{ t('boardSettings.showLabel') }}</span>
                            </label>
                            <svg
                                style="
                                    width: 14px;
                                    height: 14px;
                                    flex-shrink: 0;
                                    transition: transform 200ms;
                                    cursor: pointer;
                                "
                                :style="{
                                    transform: sectionOpen.labelDefaults ? 'rotate(180deg)' : '',
                                }"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                stroke-width="2"
                                @click="sectionOpen.labelDefaults = !sectionOpen.labelDefaults"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                                />
                            </svg>
                        </div>
                    </div>
                    <CmkCollapsible :open="sectionOpen.labelDefaults">
                        <div class="space-y-[16px]" style="padding: 0 16px 14px">
                            <div
                                :class="[
                                    'space-y-[16px] transition-opacity',
                                    form.label_show ? '' : 'opacity-40 pointer-events-none',
                                ]"
                            >
                                <div class="label-subsection">
                                    <p class="section-title">{{ t('settings.labelAppearance') }}</p>
                                    <div
                                        class="flex flex-wrap gap-x-[12px] gap-y-[8px] items-start"
                                    >
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
                                    </div>
                                </div>

                                <div class="label-subsection">
                                    <p class="section-title">{{ t('boardSettings.background') }}</p>
                                    <ColorInput
                                        v-model="form.label_background"
                                        :enable-label="t('settings.useLabelBackground')"
                                        none-value="transparent"
                                        default-color="#000000"
                                    />
                                </div>
                            </div>
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
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import CmkButton from '@/components/cmk/CmkButton';
import CmkCollapsible from '@/components/cmk/CmkCollapsible/CmkCollapsible';
import CmkColorPicker from '@/components/cmk/CmkColorPicker';
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown';
import CmkHelpText from '@/components/cmk/CmkHelpText';
import CmkLoading from '@/components/cmk/CmkLoading';
import CmkSwitch from '@/components/cmk/CmkSwitch';
import CmkToggleButtonGroup from '@/components/cmk/CmkToggleButtonGroup';
import CmkHeading from '@/components/cmk/typography/CmkHeading';
import CmkParagraph from '@/components/cmk/typography/CmkParagraph';
import CmkInput from '@/components/cmk/user-input/CmkInput';
import ColorInput from '@/components/ColorInput.vue';
import NumberInput from '@/components/NumberInput.vue';
import { useConnectionsStore } from '@/stores/connections';
import { useSettingsStore } from '@/stores/settings';
import type { GlobalSettings, LineStyle } from '@/types/api';
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
    iconDefaults: true,
    lineDefaults: false,
    labelDefaults: false,
    newBoardDefaults: false,
    templates: false,
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

<style scoped>
@reference "tailwindcss";

.section-title {
    @apply text-xs font-semibold text-[var(--text-muted)] tracking-wider uppercase mb-[6px] leading-none;
}

.label-subsection {
    padding-top: var(--dimension-4);
    border-top: 1px solid var(--border);
}

.label-subsection:first-child {
    padding-top: 0;
    border-top: 0;
}

.group-heading {
    @apply text-sm font-semibold text-[var(--text-muted)] tracking-wider uppercase mb-[8px];
}
</style>
