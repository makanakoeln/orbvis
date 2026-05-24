<template>
    <Transition name="board-bulk-bar">
        <div v-if="count > 0" class="board-bulk-bar" role="region" :aria-label="ariaLabel">
            <span class="board-bulk-bar__count">{{ t('admin.nSelected', { n: count }) }}</span>
            <label class="board-bulk-bar__selectall">
                <CmkCheckbox
                    :model-value="selectAllChecked"
                    @update:model-value="emit('toggle-select-all', $event)"
                />
                <span>{{ selectAllLabel }}</span>
            </label>
            <span class="board-bulk-bar__spacer" />
            <CmkButton variant="secondary" @click="emit('cancel')">
                {{ t('common.cancel') }}
            </CmkButton>
            <CmkButton variant="danger" :disabled="busy" @click="emit('delete')">
                {{ t('admin.deleteN', { n: count }) }}
            </CmkButton>
        </div>
    </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import CmkButton from '@/components/cmk/CmkButton';
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox';

const props = defineProps<{
    count: number;
    busy?: boolean;
    selectAllChecked: boolean;
    selectAllLabel: string;
}>();
const emit = defineEmits<{
    cancel: [];
    delete: [];
    'toggle-select-all': [checked: boolean];
}>();

const { t } = useI18n();
const ariaLabel = computed(() => t('admin.nSelected', { n: props.count }));
</script>

<style scoped>
.board-bulk-bar {
    position: fixed;
    bottom: var(--dimension-6);
    left: 50%;
    transform: translateX(-50%);
    z-index: 50;
    display: flex;
    align-items: center;
    gap: var(--dimension-5);
    padding: var(--dimension-3) var(--dimension-5);
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--dimension-3);
    box-shadow: 0 8px 24px rgb(0 0 0 / 25%);
    min-width: 440px;
}

.board-bulk-bar__count {
    font-weight: 600;
}

.board-bulk-bar__selectall {
    display: inline-flex;
    align-items: center;
    gap: var(--dimension-2);
    color: var(--text-muted);
    font-size: 0.9em;
    cursor: pointer;
    user-select: none;
}

.board-bulk-bar__spacer {
    flex: 1;
}

.board-bulk-bar-enter-active,
.board-bulk-bar-leave-active {
    transition:
        opacity 0.15s ease,
        transform 0.15s ease;
}

.board-bulk-bar-enter-from,
.board-bulk-bar-leave-to {
    opacity: 0;
    transform: translate(-50%, 12px);
}
</style>
