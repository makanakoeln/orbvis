<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkIcon from '@cmk/components/CmkIcon';
import CmkPopup from '@cmk/components/CmkPopup.vue';
import CmkHeading from '@cmk/components/typography/CmkHeading.vue';
import CmkParagraph from '@cmk/components/typography/CmkParagraph.vue';
import { DialogTitle } from 'reka-ui';

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
        <CmkIcon
            v-if="icon !== undefined"
            class="cmk-popup-dialog__icon"
            :name="icon ?? 'info-circle'"
            size="xxxlarge"
        />
        <DialogTitle>
            <CmkHeading type="h2" class="cmk-popup-dialog__title">{{ title }}</CmkHeading>
        </DialogTitle>
        <slot></slot>
        <CmkParagraph v-if="text" class="cmk-popup-dialog__text">{{ text }}</CmkParagraph>

        <CmkButton v-if="okButtonText !== undefined" variant="primary" @click="emit('close')">
            {{ okButtonText }}
        </CmkButton>
    </CmkPopup>
</template>

<style scoped>
.cmk-popup-dialog__icon,
.cmk-popup-dialog__title,
.cmk-popup-dialog__text {
    margin-bottom: var(--dimension-8);
}
</style>
