<template>
    <OrbModal :open="true" :title="t('admin.createBoard')" closable @close="$emit('close')">
        <form class="create-board__form" @submit.prevent="submit">
            <div class="create-board__field">
                <label class="create-board__label">{{ t('admin.boardId') }}</label>
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
                <p v-if="nameError" class="create-board__error">{{ nameError }}</p>
                <p v-else class="create-board__hint">{{ t('admin.boardIdHint') }}</p>
            </div>
            <div class="create-board__field">
                <label class="create-board__label">{{ t('admin.alias') }}</label>
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
            <div class="create-board__field">
                <label class="create-board__label">{{ t('board.connection') }}</label>
                <template v-if="connectionsStore.connections.length > 0">
                    <CmkDropdown
                        :selected-option="form.connection_id || null"
                        :options="connectionOptions"
                        :width="'fill'"
                        :label="t('board.connection')"
                        @update:selected-option="form.connection_id = $event ?? ''"
                    />
                </template>
                <template v-else>
                    <CmkAlertBox variant="warning" size="small">
                        {{ t('admin.noConnectionsCreate') }}
                        <router-link
                            :to="{ name: 'admin-connections' }"
                            class="create-board__link"
                            @click="$emit('close')"
                        >
                            {{ t('admin.createConnectionLink') }}
                        </router-link>
                    </CmkAlertBox>
                </template>
            </div>
            <div class="create-board__field">
                <label class="create-board__label">{{ t('board.boardType') }}</label>
                <CmkDropdown
                    :selected-option="form.view_type || null"
                    :options="mapTypeOptions"
                    :width="'fill'"
                    :label="t('board.boardType')"
                    @update:selected-option="form.view_type = $event ?? ''"
                />
                <p class="create-board__hint">
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
        </form>

        <template #footer>
            <CmkButton variant="secondary" @click="$emit('close')">
                {{ t('common.cancel') }}
            </CmkButton>
            <CmkButton
                variant="primary"
                :disabled="!form.name || !!nameError || !form.connection_id"
                @click="submit"
            >
                {{ t('common.create') }}
            </CmkButton>
        </template>
    </OrbModal>
</template>

<script setup lang="ts">
import CmkAlertBox from '@cmk/components/CmkAlertBox.vue';
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkDropdown from '@cmk/components/CmkDropdown/CmkDropdown.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { ApiError } from '@/api/client';
import OrbModal from '@/components/OrbModal.vue';
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

const form = ref({ name: '', alias: '', connection_id: '', view_type: 'static' });
const aliasTouched = ref(false);

const connectionOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: connectionsStore.connections.map((b) => ({ name: b.id, title: b.label || b.id })),
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
    const ids = connectionsStore.connections.map((b) => b.id);
    const preferred = settingsStore.settings.default_backend_id;
    return (preferred && ids.includes(preferred) ? preferred : ids[0]) ?? '';
}

onMounted(async () => {
    await Promise.all([connectionsStore.fetchConnections(), settingsStore.load()]);
    form.value.connection_id = pickBackendId();
    form.value.view_type = settingsStore.settings.default_map_type || 'static';
});

async function submit() {
    nameError.value = '';
    try {
        await boardsStore.createBoard(
            form.value.name,
            form.value.alias,
            form.value.connection_id,
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
        connection_id: pickBackendId(),
        view_type: settingsStore.settings.default_map_type || 'static',
    };
    emit('created', created);
}
</script>

<style scoped>
.create-board__form {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-5);
    min-width: 380px;
}

.create-board__field {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-3);
}

.create-board__label {
    font-size: var(--font-size-normal);
    font-weight: 500;
    color: var(--text-muted);
}

.create-board__error {
    font-size: var(--font-size-normal);
    color: var(--color-light-red-40);
}

.create-board__hint {
    font-size: var(--font-size-normal);
    color: var(--text-muted);
}

.create-board__link {
    display: block;
    margin-top: var(--dimension-3);
    color: var(--color-yellow-50);
    font-weight: 600;
    text-decoration: underline;
}
</style>
