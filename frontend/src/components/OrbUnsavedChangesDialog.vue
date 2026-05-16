<template>
    <CmkPopupDialog :open="open" icon="warning" :title="title" @close="$emit('cancel')">
        <CmkParagraph class="orb-unsaved__message">{{ message }}</CmkParagraph>
        <div class="orb-unsaved__actions">
            <CmkButton ref="stayBtnRef" variant="optional" @click="$emit('cancel')">
                {{ stayLabel }}
            </CmkButton>
            <CmkButton variant="secondary" @click="$emit('confirm')">
                {{ discardLabel }}
            </CmkButton>
        </div>
    </CmkPopupDialog>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkPopupDialog from '@cmk/components/CmkPopupDialog.vue';
import CmkParagraph from '@cmk/components/typography/CmkParagraph.vue';
import { computed, nextTick, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const props = defineProps<{ open: boolean }>();
defineEmits<{ confirm: []; cancel: [] }>();

const title = computed(() => t('common.unsavedConfirmTitle'));
const message = computed(() => t('common.unsavedConfirmMessage'));
const discardLabel = computed(() => t('common.discardChanges'));
const stayLabel = computed(() => t('common.stayOnPage'));

// Pre-select the safe action so Enter dismisses the dialog instead of
// destroying work. CmkPopup disables reka-ui's auto-focus, so the focus
// must be set explicitly after the portal has rendered.
const stayBtnRef = ref<{ $el: HTMLElement } | null>(null);

watch(
    () => props.open,
    async (isOpen) => {
        if (!isOpen) return;
        // CmkPopup focuses its own DialogContent in a `nextTick` after the
        // portal mounts. Wait two ticks so our explicit focus overrides it.
        await nextTick();
        await nextTick();
        stayBtnRef.value?.$el?.focus();
    },
);
</script>

<style scoped>
.orb-unsaved__message {
    margin-bottom: var(--dimension-6);
}

.orb-unsaved__actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--dimension-3);
}
</style>
