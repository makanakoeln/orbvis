<!--
OrbVis-native CmkPopupDialog, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone. Drops the upstream CmkIcon dependency —
icon slot is replaced by a text glyph that matches the dialog's intent.
-->
<script setup lang="ts">
import { DialogTitle } from 'reka-ui';

import CmkButton from '@/components/cmk/CmkButton';
import CmkPopup from '@/components/cmk/CmkPopup';
import CmkHeading from '@/components/cmk/typography/CmkHeading';
import CmkParagraph from '@/components/cmk/typography/CmkParagraph';

export interface CmkPopupDialogProps {
    open: boolean;
    icon?: string | undefined;
    title: string;
    text?: string;
    okButtonText?: string | undefined;
    stayOpenOverlayClick?: boolean;
}
defineProps<CmkPopupDialogProps>();
const emit = defineEmits(['close']);
</script>

<template>
    <CmkPopup :open="open" @close="!stayOpenOverlayClick && emit('close')">
        <div v-if="icon" class="orb-popup-dialog__icon" aria-hidden="true">ℹ</div>
        <DialogTitle>
            <CmkHeading type="h2" class="orb-popup-dialog__title">{{ title }}</CmkHeading>
        </DialogTitle>
        <slot />
        <CmkParagraph v-if="text" class="orb-popup-dialog__text">{{ text }}</CmkParagraph>
        <CmkButton v-if="okButtonText !== undefined" variant="primary" @click="emit('close')">
            {{ okButtonText }}
        </CmkButton>
    </CmkPopup>
</template>

<style scoped>
.orb-popup-dialog__icon,
.orb-popup-dialog__title,
.orb-popup-dialog__text {
    margin-bottom: 20px;
}

.orb-popup-dialog__icon {
    font-size: 40px;
    color: var(--color-corporate-green-50, #15d1a0);
    text-align: center;
}
</style>
