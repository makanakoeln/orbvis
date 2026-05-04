<template>
    <Teleport to="body">
        <div class="fixed inset-0 z-50 flex items-center justify-center">
            <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
            <div
                class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl w-[26rem]"
                style="padding: 16px 20px"
            >
                <div class="flex items-center justify-between" style="margin-bottom: 12px">
                    <h3 class="text-base font-bold text-[var(--text)]">
                        {{ t('admin.createBoard') }}
                    </h3>
                    <button
                        class="p-[5px] rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all"
                        @click="$emit('close')"
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
                                d="M6 18L18 6M6 6l12 12"
                            />
                        </svg>
                    </button>
                </div>
                <form class="space-y-[10px]" @submit.prevent="submit">
                    <div class="space-y-[4px]">
                        <label class="text-xs font-medium text-zinc-400">
                            {{ t('admin.boardId') }}
                        </label>
                        <CmkInput
                            :model-value="form.name"
                            placeholder="my-board"
                            field-size="FILL"
                            @update:model-value="
                                (v) =>
                                    onNameInput({
                                        target: { value: String(v ?? '') },
                                    } as unknown as Event)
                            "
                        />
                        <p v-if="nameError" class="text-xs text-red-400">{{ nameError }}</p>
                        <p v-else class="text-xs text-zinc-600">{{ t('admin.boardIdHint') }}</p>
                    </div>
                    <div class="space-y-[4px]">
                        <label class="text-xs font-medium text-zinc-400">{{
                            t('admin.alias')
                        }}</label>
                        <CmkInput
                            v-model="form.alias"
                            placeholder="My Board"
                            field-size="FILL"
                            @update:model-value="
                                () => {
                                    aliasTouched = true;
                                }
                            "
                        />
                    </div>
                    <div class="space-y-[4px]">
                        <label class="text-xs font-medium text-zinc-400">{{
                            t('board.connection')
                        }}</label>
                        <template v-if="connectionsStore.backends.length > 0">
                            <CmkDropdown
                                :selected-option="form.backend_id || null"
                                :options="backendOptions"
                                :width="'fill'"
                                :label="t('board.connection')"
                                @update:selected-option="form.backend_id = $event ?? ''"
                            />
                        </template>
                        <template v-else>
                            <div
                                class="flex items-start gap-2.5 px-3.5 py-3 bg-amber-500/8 ring-1 ring-amber-500/20 rounded-lg"
                            >
                                <svg
                                    class="w-4 h-4 text-amber-400 shrink-0 mt-0.5"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                                    />
                                </svg>
                                <div class="text-xs text-amber-300/90 leading-relaxed">
                                    {{ t('admin.noConnectionsCreate') }}
                                    <router-link
                                        :to="{ name: 'admin-connections' }"
                                        class="block mt-1 font-semibold text-amber-400 hover:text-amber-300 underline underline-offset-2 transition-colors"
                                        @click="$emit('close')"
                                    >
                                        {{ t('admin.createConnectionLink') }}
                                    </router-link>
                                </div>
                            </div>
                        </template>
                    </div>
                    <div class="space-y-[4px]">
                        <label class="text-xs font-medium text-zinc-400">{{
                            t('board.boardType')
                        }}</label>
                        <CmkDropdown
                            :selected-option="form.view_type || null"
                            :options="mapTypeOptions"
                            :width="'fill'"
                            :label="t('board.boardType')"
                            @update:selected-option="form.view_type = $event ?? ''"
                        />
                        <p class="text-xs text-zinc-500">
                            <template v-if="form.view_type === 'static'">{{
                                t('board.boardTypeStaticDesc')
                            }}</template>
                            <template v-else-if="form.view_type === 'worldmap'">{{
                                t('board.boardTypeGeoBoardDesc')
                            }}</template>
                            <template v-else-if="form.view_type === 'flow'">{{
                                t('board.boardTypeFlowBoardDesc')
                            }}</template>
                            <template v-else-if="form.view_type === 'radar'">{{
                                t('board.boardTypeRadarDesc')
                            }}</template>
                        </p>
                    </div>
                    <div
                        class="flex gap-[8px] justify-end border-t border-[var(--border)]"
                        style="padding-top: 10px"
                    >
                        <CmkButton variant="secondary" @click="$emit('close')">{{
                            t('common.cancel')
                        }}</CmkButton>
                        <CmkButton
                            variant="primary"
                            :disabled="!form.name || !!nameError || !form.backend_id"
                            @click="submit"
                        >
                            {{ t('common.create') }}
                        </CmkButton>
                    </div>
                </form>
            </div>
        </div>
    </Teleport>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkDropdown from '@cmk/components/CmkDropdown/CmkDropdown.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { ApiError } from '@/api/client';
import { useBoardsStore } from '@/stores/boards';
import { useConnectionsStore } from '@/stores/connections';
import { useSettingsStore } from '@/stores/settings';
import { boardTypeOptions } from '@/utils/dropdownOptions';
import { sanitizeBoardName, slugToTitleCase } from '@/utils/naming';

const emit = defineEmits<{ close: []; created: [name: string] }>();

const { t } = useI18n();
const boardsStore = useBoardsStore();
const connectionsStore = useConnectionsStore();
const settingsStore = useSettingsStore();

const form = ref({ name: '', alias: '', backend_id: '', view_type: 'static' });
const aliasTouched = ref(false);

const backendOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: connectionsStore.backends.map((b) => ({ name: b.id, title: b.label || b.id })),
}));
const mapTypeOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: boardTypeOptions(t),
}));

const _NAME_RE = /^[a-zA-Z0-9_-]+$/;
const nameError = ref('');

function onNameInput(e: Event) {
    form.value.name = sanitizeBoardName((e.target as HTMLInputElement).value);
    nameError.value = _NAME_RE.test(form.value.name) ? '' : t('admin.boardIdInvalid');
    if (!aliasTouched.value) {
        form.value.alias = slugToTitleCase(form.value.name);
    }
}

function pickBackendId() {
    const ids = connectionsStore.backends.map((b) => b.id);
    const preferred = settingsStore.settings.default_backend_id;
    return (preferred && ids.includes(preferred) ? preferred : ids[0]) ?? '';
}

onMounted(async () => {
    await Promise.all([connectionsStore.fetchBackends(), settingsStore.load()]);
    form.value.backend_id = pickBackendId();
    form.value.view_type = settingsStore.settings.default_map_type || 'static';
});

async function submit() {
    nameError.value = '';
    try {
        await boardsStore.createBoard(
            form.value.name,
            form.value.alias,
            form.value.backend_id,
            form.value.view_type,
            settingsStore.settings.icon_size,
        );
    } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
            nameError.value = t('admin.boardIdTaken');
        }
        return;
    }
    const created = form.value.name;
    form.value = {
        name: '',
        alias: '',
        backend_id: pickBackendId(),
        view_type: settingsStore.settings.default_map_type || 'static',
    };
    emit('created', created);
}
</script>
