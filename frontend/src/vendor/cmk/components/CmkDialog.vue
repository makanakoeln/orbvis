<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
Vendored from cmk-frontend-vue.

OrbVis patch: removed the `dismissalButton` feature (the "don't show me again"
button). It depends on cmk-shared-typing's UserDismissWarning enum and CMK's
user-config persistence endpoint, neither of which OrbVis ships. The remaining
icon-box + title + message + buttons layout is identical to upstream.
-->
<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority';
import { computed } from 'vue';

import CmkButton, { type ButtonProps } from './CmkButton.vue';
import CmkIcon from './CmkIcon';
import CmkMultitoneIcon from './CmkIcon/CmkMultitoneIcon.vue';
import CmkSpace from './CmkSpace.vue';

type ButtonVariant = NonNullable<ButtonProps['variant']>;

export interface CmkDialogProps {
    title?: string;
    message: string;
    buttons?: { title: string; variant: ButtonVariant; onclick: () => void }[];
    variant?: Variants;
}

const props = defineProps<CmkDialogProps>();

const propsCva = cva('', {
    variants: {
        variant: {
            error: 'cmk-dialog__icon-box--error',
            warning: 'cmk-dialog__icon-box--warning',
            success: 'cmk-dialog__icon-box--success',
            info: 'cmk-dialog__icon-box--info',
            loading: 'cmk-dialog__icon-box--loading',
        },
    },
    defaultVariants: {
        variant: 'info',
    },
});

export type Variants = VariantProps<typeof propsCva>['variant'];

const alertIconName = computed(() => {
    switch (props.variant) {
        case 'success':
            return 'checkmark';
        case 'error':
        case 'warning':
            return props.variant;
        default:
            return 'info';
    }
});

const alertIconColor = computed(() => {
    switch (props.variant) {
        case 'warning':
        case 'success':
            return { custom: 'black' };
        default:
            return { custom: 'white' };
    }
});
</script>

<template>
    <div class="cmk-dialog help">
        <div :class="['cmk-dialog__icon-box', propsCva({ variant: props.variant })]">
            <CmkIcon v-if="variant === 'loading'" name="load-graph" class="cmk-dialog__icon" />
            <CmkMultitoneIcon
                v-else
                :name="alertIconName"
                :primary-color="alertIconColor"
                class="cmk-dialog__icon"
            />
        </div>
        <div class="cmk-dialog__content">
            <span v-if="props.title" class="cmk-dialog__title">{{ props.title }}<br /></span>
            <span>{{ props.message }}</span>
            <div v-if="(props.buttons?.length ?? 0) > 0" class="buttons">
                <CmkSpace direction="vertical" />
                <!-- eslint-disable vue/valid-v-for since no unique identifier is present for key -->
                <template v-for="button in props.buttons">
                    <CmkButton :variant="button.variant" @click="button.onclick">
                        {{ button.title }}
                    </CmkButton>
                    <CmkSpace />
                </template>
                <!-- eslint-enable vue/valid-v-for -->
            </div>
        </div>
    </div>
</template>

<style scoped>
div.cmk-dialog {
    display: flex;

    div.cmk-dialog__content {
        background-color: var(--default-dialog-bg-color);
        color: var(--default-dialog-font-color);
        border-radius: 0 4px 4px 0;
        flex-grow: 1;
        padding: var(--spacing);
        white-space: pre-line;

        & > .cmk-dialog__title {
            font-weight: var(--font-weight-bold);
            margin-bottom: var(--spacing);
            display: block;
        }
    }

    .cmk-dialog__icon-box {
        display: flex;
        align-items: center;
        border-radius: var(--dimension-3) 0 0 var(--dimension-3);
        border: 1px solid transparent;
    }

    .cmk-dialog__icon {
        padding: var(--dimension-2);
    }

    .cmk-dialog__icon-box--info {
        background-color: var(--color-dark-blue-50);
    }

    .cmk-dialog__icon-box--error {
        background-color: var(--color-dark-red-50);
    }

    .cmk-dialog__icon-box--warning {
        background-color: var(--color-warning);
    }

    .cmk-dialog__icon-box--success {
        background-color: var(--color-corporate-green-50);
    }

    .cmk-dialog__icon-box--loading {
        background-color: var(--color-corporate-green-100);
    }
}

body[data-theme='modern-dark'] {
    div.cmk-dialog {
        .cmk-dialog__icon-box--loading {
            border-color: var(--color-corporate-green-70);
        }
    }
}
</style>
