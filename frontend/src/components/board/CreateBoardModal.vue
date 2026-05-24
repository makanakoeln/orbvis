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
                <p v-else-if="nameWarning" class="create-board__warning">{{ nameWarning }}</p>
                <p v-else class="create-board__hint">{{ t('admin.boardIdHint') }}</p>
            </div>
            <div class="create-board__field">
                <label class="create-board__label">{{ t('admin.alias') }}</label>
                <CmkInput
                    v-model="form.alias"
                    placeholder="My Board"
                    field-size="FILL"
                    @update:model-value="onAliasInput"
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
                <div
                    class="create-board__type-grid"
                    role="radiogroup"
                    :aria-label="t('board.boardType')"
                >
                    <button
                        v-for="opt in boardTypeCards"
                        :key="opt.name"
                        type="button"
                        role="radio"
                        :aria-checked="form.view_type === opt.name"
                        class="create-board__type-card"
                        :class="{
                            'create-board__type-card--selected': form.view_type === opt.name,
                        }"
                        @click="form.view_type = opt.name"
                    >
                        <span class="create-board__type-card-title">{{ opt.title }}</span>
                        <span class="create-board__type-card-desc">{{ opt.desc }}</span>
                    </button>
                </div>
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
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { ApiError } from '@/api/client';
import CmkAlertBox from '@/components/cmk/CmkAlertBox';
import CmkButton from '@/components/cmk/CmkButton';
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown';
import CmkInput from '@/components/cmk/user-input/CmkInput';
import OrbModal from '@/components/OrbModal.vue';
import { useBoardsStore } from '@/stores/boards';
import { useConnectionsStore } from '@/stores/connections';
import { useSettingsStore } from '@/stores/settings';
import { boardTypeOptions } from '@/utils/dropdownOptions';
import { sanitizeBoardName, sanitizeStrippedChars, slugToTitleCase } from '@/utils/naming';

const emit = defineEmits<{ close: []; created: [name: string] }>();

const { t } = useI18n();
const boardsStore = useBoardsStore();
const connectionsStore = useConnectionsStore();
const settingsStore = useSettingsStore();

const form = ref({ name: '', alias: '', connection_id: '', view_type: 'static' });
const aliasTouched = ref(false);
const nameTouched = ref(false);

const connectionOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: connectionsStore.connections.map((b) => ({ name: b.id, title: b.label || b.id })),
}));
const boardTypeCards = computed(() =>
    boardTypeOptions(t).map((o) => ({
        ...o,
        desc:
            o.name === 'static'
                ? t('board.boardTypeStaticDesc')
                : o.name === 'worldmap'
                  ? t('board.boardTypeGeoBoardDesc')
                  : o.name === 'flow'
                    ? t('board.boardTypeFlowBoardDesc')
                    : t('board.boardTypeRadarDesc'),
    })),
);

const _NAME_RE = /^[a-zA-Z0-9_-]+$/;
const _MAX_NAME_LEN = 64;
const nameError = ref('');
const nameWarning = ref('');

function onNameInput(e: Event) {
    nameTouched.value = true;
    const raw = (e.target as HTMLInputElement).value;
    const stripped = sanitizeStrippedChars(raw);
    form.value.name = sanitizeBoardName(raw);
    if (form.value.name.length > _MAX_NAME_LEN) {
        nameError.value = t('admin.boardIdTooLong', { max: _MAX_NAME_LEN });
    } else if (form.value.name && !_NAME_RE.test(form.value.name)) {
        nameError.value = t('admin.boardIdInvalid');
    } else {
        nameError.value = '';
    }
    nameWarning.value = stripped ? t('admin.boardIdStripped') : '';
    if (!aliasTouched.value) {
        form.value.alias = slugToTitleCase(form.value.name);
    }
}

function onAliasInput() {
    aliasTouched.value = true;
    if (!nameTouched.value) {
        form.value.name = sanitizeBoardName(form.value.alias).toLowerCase();
        nameError.value =
            form.value.name && !_NAME_RE.test(form.value.name) ? t('admin.boardIdInvalid') : '';
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
            null,
        );
    } catch (err) {
        if (err instanceof ApiError) {
            if (err.status === 409) {
                nameError.value = t('admin.boardIdTaken');
            } else if (err.status === 422) {
                nameError.value = err.message || t('admin.boardIdInvalid');
            } else {
                nameError.value = err.message || `HTTP ${err.status}`;
            }
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

.create-board__warning {
    font-size: var(--font-size-normal);
    color: var(--color-yellow-50);
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

.create-board__type-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--dimension-3);
}

.create-board__type-card {
    text-align: left;
    padding: var(--dimension-4) var(--dimension-5);
    background: var(--default-form-element-bg-color);
    border: 1px solid var(--default-form-element-border-color);
    border-radius: var(--border-radius);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: 2px;
    transition:
        border-color 120ms,
        background-color 120ms;
}

.create-board__type-card:hover {
    border-color: var(--color-corporate-green-50);
}

.create-board__type-card--selected {
    border-color: var(--color-corporate-green-50);
    background: color-mix(
        in srgb,
        var(--color-corporate-green-50) 10%,
        var(--default-form-element-bg-color)
    );
}

.create-board__type-card-title {
    font-size: var(--font-size-normal);
    font-weight: 600;
    color: var(--text);
}

.create-board__type-card-desc {
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.35;
}
</style>
