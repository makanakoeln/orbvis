<template>
    <Transition name="orb-bulk-bar">
        <div v-if="count > 0" class="orb-bulk-bar" role="region" :aria-label="ariaLabel">
            <span class="orb-bulk-bar__count">{{ t('admin.nSelected', { n: count }) }}</span>
            <label class="orb-bulk-bar__selectall">
                <input
                    type="checkbox"
                    :checked="selectAllChecked"
                    @change="emit('toggle-select-all', ($event.target as HTMLInputElement).checked)"
                />
                <span>{{ selectAllLabel }}</span>
            </label>
            <span class="orb-bulk-bar__spacer" />
            <button
                type="button"
                class="orb-bulk-bar__btn orb-bulk-bar__btn--ghost"
                @click="emit('cancel')"
            >
                {{ t('common.cancel') }}
            </button>
            <button
                type="button"
                class="orb-bulk-bar__btn orb-bulk-bar__btn--danger"
                :disabled="busy"
                @click="emit('delete')"
            >
                {{ t('admin.deleteN', { n: count }) }}
            </button>
        </div>
    </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

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
.orb-bulk-bar {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 50;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 10px 16px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    box-shadow: 0 8px 24px rgb(0 0 0 / 25%);
    min-width: 440px;
    color: var(--text);
}

.orb-bulk-bar__count {
    font-weight: 600;
}

.orb-bulk-bar__selectall {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--text-muted);
    font-size: 0.9em;
    cursor: pointer;
    user-select: none;
}

.orb-bulk-bar__spacer {
    flex: 1;
}

.orb-bulk-bar__btn {
    font: inherit;
    padding: 6px 14px;
    border-radius: 6px;
    cursor: pointer;
    border: 1px solid transparent;
    transition:
        background-color 0.15s,
        border-color 0.15s,
        color 0.15s;
}

.orb-bulk-bar__btn:disabled {
    opacity: 0.55;
    cursor: not-allowed;
}

.orb-bulk-bar__btn--ghost {
    background: transparent;
    color: var(--text);
    border-color: var(--border);
}

.orb-bulk-bar__btn--ghost:hover:not(:disabled) {
    background: var(--bg-hover, rgb(255 255 255 / 6%));
}

.orb-bulk-bar__btn--danger {
    background: var(--color-light-red-50);
    color: var(--color-white-100, white);
    border-color: var(--color-light-red-50);
}

.orb-bulk-bar__btn--danger:hover:not(:disabled) {
    background: var(--color-light-red-60);
    border-color: var(--color-light-red-60);
}

.orb-bulk-bar-enter-active,
.orb-bulk-bar-leave-active {
    transition:
        opacity 0.15s ease,
        transform 0.15s ease;
}

.orb-bulk-bar-enter-from,
.orb-bulk-bar-leave-to {
    opacity: 0;
    transform: translate(-50%, 12px);
}
</style>
