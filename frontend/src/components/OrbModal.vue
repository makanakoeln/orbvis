<template>
    <CmkPopup :open="open" @close="$emit('close')">
        <div class="orb-modal__shell">
            <header v-if="$slots.header || title" class="orb-modal__header">
                <DialogTitle as-child>
                    <CmkHeading type="h3" class="orb-modal__title">
                        <slot name="header">{{ title }}</slot>
                    </CmkHeading>
                </DialogTitle>
                <button
                    v-if="closable"
                    type="button"
                    class="orb-modal__close"
                    :aria-label="t('common.close')"
                    @click="$emit('close')"
                >
                    <svg
                        width="14"
                        height="14"
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
            </header>
            <div class="orb-modal__body">
                <slot />
            </div>
            <footer v-if="$slots.footer" class="orb-modal__footer">
                <slot name="footer" />
            </footer>
        </div>
    </CmkPopup>
</template>

<script setup lang="ts">
import { DialogTitle } from 'reka-ui';
import { useI18n } from 'vue-i18n';

import CmkPopup from '@/components/cmk/CmkPopup';
import CmkHeading from '@/components/cmk/typography/CmkHeading';

withDefaults(
    defineProps<{
        open: boolean;
        title?: string;
        closable?: boolean;
    }>(),
    { closable: true, title: '' },
);

defineEmits<{ close: [] }>();

const { t } = useI18n();
</script>

<style scoped>
.orb-modal__shell {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    min-height: 0;
}

.orb-modal__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--dimension-4);
    padding: var(--dimension-5) var(--dimension-6);
    border-bottom: 1px solid var(--border);
}

.orb-modal__title {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.orb-modal__close {
    background: transparent;
    border: 0;
    color: var(--text-muted);
    padding: var(--dimension-2);
    border-radius: var(--dimension-3);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition:
        color 0.15s,
        background-color 0.15s;
}

.orb-modal__close:hover {
    color: var(--text);
    background: var(--bg-hover);
}

.orb-modal__body {
    padding: var(--dimension-6);
    flex: 1;
    min-height: 0;
    overflow: auto;
}

.orb-modal__footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: var(--dimension-3);
    padding: var(--dimension-5) var(--dimension-6);
    border-top: 1px solid var(--border);
}
</style>
