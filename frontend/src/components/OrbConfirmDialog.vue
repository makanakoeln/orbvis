<template>
    <CmkPopup :open="open" @close="$emit('cancel')">
        <div class="orb-confirm-dialog">
            <CmkDialog
                v-if="open"
                :variant="variant"
                :title="title"
                :message="message"
                :buttons="dialogButtons"
            />
        </div>
    </CmkPopup>
</template>

<script setup lang="ts">
import CmkDialog from '@cmk/components/CmkDialog.vue';
import CmkPopup from '@cmk/components/CmkPopup.vue';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

type DialogVariant = 'error' | 'warning' | 'success' | 'info';
type ButtonVariant =
    | 'primary'
    | 'secondary'
    | 'optional'
    | 'success'
    | 'warning'
    | 'danger'
    | 'info';

interface ExtraButton {
    title: string;
    variant?: ButtonVariant;
    onclick: () => void;
}

const props = withDefaults(
    defineProps<{
        open: boolean;
        title: string;
        message?: string;
        confirmLabel?: string;
        cancelLabel?: string;
        confirmVariant?: ButtonVariant;
        variant?: DialogVariant;
        // Additional buttons rendered before the confirm/cancel pair. Use this
        // for in-dialog actions like "Open referenced board X" — mirrors the
        // CMK pattern (e.g. NotificationFallbackWarning) of attaching links
        // as buttons rather than embedding <a> in the message.
        extraButtons?: ExtraButton[];
    }>(),
    {
        message: '',
        confirmLabel: '',
        cancelLabel: '',
        confirmVariant: 'warning',
        variant: 'warning',
        extraButtons: () => [],
    },
);

const emit = defineEmits<{ confirm: []; cancel: [] }>();
const { t } = useI18n();

const dialogButtons = computed(() => [
    ...props.extraButtons.map((b) => ({
        title: b.title,
        variant: (b.variant ?? 'info') as ButtonVariant,
        onclick: b.onclick,
    })),
    {
        title: props.confirmLabel || t('common.confirm'),
        variant: props.confirmVariant,
        onclick: () => emit('confirm'),
    },
    {
        title: props.cancelLabel || t('common.cancel'),
        variant: 'secondary' as ButtonVariant,
        onclick: () => emit('cancel'),
    },
]);
</script>

<style scoped>
.orb-confirm-dialog {
    width: 420px;
    max-width: 90vw;
}

/* !important: CmkDialog scoped CSS hat höhere Specificity als :deep(). */
.orb-confirm-dialog :deep(.cmk-dialog__content) {
    padding: var(--dimension-7) var(--dimension-8) !important;
    line-height: 1.45;
}

.orb-confirm-dialog :deep(.cmk-dialog__title) {
    font-size: var(--font-size-large) !important;
    margin-bottom: var(--dimension-2) !important;
    line-height: 1.4 !important;
}

.orb-confirm-dialog :deep(.cmk-dialog__icon-box) {
    padding: 0 var(--dimension-5) !important;
    align-self: stretch;
    justify-content: center;
}

.orb-confirm-dialog :deep(.cmk-dialog__icon) {
    padding: var(--dimension-1) !important;
}

.orb-confirm-dialog :deep(.buttons) {
    margin-top: var(--dimension-6) !important;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
}
</style>
