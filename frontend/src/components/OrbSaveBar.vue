<template>
    <div class="orb-save-bar">
        <span v-if="dirty" class="orb-save-bar__dirty" :title="t('common.unsavedChangesHint')">
            {{ t('common.unsavedChanges') }}
        </span>
        <Transition
            enter-from-class="opacity-0 translate-x-2"
            enter-active-class="transition-all duration-200"
            leave-to-class="opacity-0"
            leave-active-class="transition-opacity duration-300"
        >
            <span v-if="savedOk" class="orb-save-bar__saved-msg">
                <svg viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" fill="none">
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M4.5 12.75l6 6 9-13.5"
                    />
                </svg>
                {{ t('common.saved') }}
            </span>
        </Transition>
        <span v-if="error" class="orb-save-bar__error-msg">{{ error }}</span>
        <slot name="extra" />
        <CmkButton variant="secondary" :disabled="!dirty || saving" @click="$emit('cancel')">
            {{ t('common.cancel') }}
        </CmkButton>
        <CmkButton variant="primary" :disabled="saving || !dirty" @click="$emit('save')">
            {{ saving ? t('common.saving') : t('common.save') }}
        </CmkButton>
    </div>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

defineProps<{
    dirty: boolean;
    saving?: boolean;
    savedOk?: boolean;
    error?: string;
}>();

defineEmits<{ save: []; cancel: [] }>();
</script>

<style scoped>
/* Full-width sticky action bar at the bottom of the viewport. Border-top
   instead of a floating card with shadow — matches Checkmk WATO style. */
.orb-save-bar {
    position: sticky;
    bottom: 0;
    z-index: 5;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: var(--dimension-4);
    padding: var(--dimension-4) var(--dimension-8);
    background: var(--bg-surface);
    border-top: 1px solid var(--border);
}

.orb-save-bar__dirty {
    font-size: 13px;
    color: var(--text-muted);
    margin-right: auto;
}

.orb-save-bar__saved-msg {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 13px;
    color: var(--color-corporate-green-50);
}

.orb-save-bar__saved-msg svg {
    width: 14px;
    height: 14px;
}

.orb-save-bar__error-msg {
    font-size: 13px;
    color: var(--color-light-red-40);
}
</style>
