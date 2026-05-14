<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
Vendored from cmk-frontend-vue.

OrbVis patches:
- CMK's `usei18n` is not vendored; replaced with vue-i18n's `useI18n` and a
  `t('common.close')` fallback for the close button label.
- Imports rewritten to OrbVis path aliases (@cmk/...).
-->
<script setup lang="ts">
import CmkIcon, { type CmkIconProps } from '@cmk/components/CmkIcon';
import CmkScrollContainer from '@cmk/components/CmkScrollContainer.vue';
import CmkSlideIn, { type SlideInVariants } from '@cmk/components/CmkSlideIn';
import CmkHeading from '@cmk/components/typography/CmkHeading.vue';
import { DialogClose, DialogTitle } from 'reka-ui';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const scrollContainerRef = ref<InstanceType<typeof CmkScrollContainer>>();
const scrollContainerEl = computed(() => {
    const el = scrollContainerRef.value?.$el;
    return el instanceof HTMLElement ? el : undefined;
});

export interface CmkSlideInDialogProps {
    open: boolean;
    size?: SlideInVariants['size'];
    isIndexPage?: boolean | undefined;
    stackPriority?: number | undefined;
    header?: {
        title: string;
        icon?: CmkIconProps | undefined;
        closeButton: boolean;
    };
    borderColor?: SlideInVariants['borderColor'];
}
defineProps<CmkSlideInDialogProps>();
const emit = defineEmits(['close']);
</script>

<template>
    <CmkSlideIn
        :aria-label="header?.title"
        :open="open"
        :is-index-page="isIndexPage"
        :size="size"
        :stack-priority="stackPriority"
        :border-color="borderColor"
        :initial-focus-target="scrollContainerEl"
        @close="emit('close')"
    >
        <DialogTitle v-if="header" class="cmk-slide-in-dialog__title">
            <CmkHeading type="h1" class="cmk-slide-in-dialog__title-header">
                <CmkIcon v-if="header.icon" v-bind="header.icon" />
                {{ header.title }}
            </CmkHeading>
            <!-- @vue-ignore @click is not a property of DialogClose -->
            <DialogClose
                v-if="header.closeButton"
                class="cmk-slide-in-dialog__close"
                @click="emit('close')"
            >
                <CmkIcon :aria-label="t('common.close')" name="close" size="xsmall" />
            </DialogClose>
        </DialogTitle>

        <CmkScrollContainer
            ref="scrollContainerRef"
            type="outer"
            class="cmk-slide-in-dialog__content"
            tabindex="0"
            role="region"
            :aria-label="header?.title ?? t('common.close')"
        >
            <slot />
        </CmkScrollContainer>
    </CmkSlideIn>
</template>

<style scoped>
.cmk-slide-in-dialog__title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 20px;

    .cmk-slide-in-dialog__title-header {
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: var(--dimension-5);
    }

    label {
        margin-right: 10px;
    }
}

.cmk-slide-in-dialog__content {
    padding: 0 20px;
}

.cmk-slide-in-dialog__close {
    background: none;
    border: none;
    margin: 0;
    padding: 0;
}

button {
    margin: 0 10px 0 0;
}
</style>
