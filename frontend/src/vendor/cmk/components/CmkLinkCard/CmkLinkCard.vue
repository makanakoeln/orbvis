<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
Vendored from cmk-frontend-vue.

OrbVis patch: replaced TranslatedString with plain string (OrbVis i18n
returns strings directly via vue-i18n).
-->
<script setup lang="ts">
import type { SimpleIcons } from '@cmk/components/CmkIcon';
import CmkIcon from '@cmk/components/CmkIcon';
import CmkHeading from '@cmk/components/typography/CmkHeading.vue';
import CmkParagraph from '@cmk/components/typography/CmkParagraph.vue';
import { cva, type VariantProps } from 'class-variance-authority';
import { computed } from 'vue';

const cmkLinkCardVariants = cva('', {
    variants: {
        borders: {
            standard: 'cmk-link-card--standard',
            borderless: 'cmk-link-card--borderless',
        },
        contrast: {
            standard: 'cmk-link-card--standard-contrast',
            high: 'cmk-link-card--high-contrast',
        },
    },
    defaultVariants: {
        borders: 'standard',
        contrast: 'standard',
    },
});

export type CmkLinkCardBorders = VariantProps<typeof cmkLinkCardVariants>['borders'];
export type CmkLinkCardContrast = VariantProps<typeof cmkLinkCardVariants>['contrast'];

interface CmkLinkCardProps {
    iconName?: SimpleIcons | undefined;
    title: string;
    subtitle?: string;
    url?: string | undefined;
    callback?: () => void;
    openInNewTab: boolean;
    disabled?: boolean;
    borders?: CmkLinkCardBorders;
    contrast?: CmkLinkCardContrast;
}
const props = defineProps<CmkLinkCardProps>();
const classes = computed(() => [
    cmkLinkCardVariants({ borders: props.borders, contrast: props.contrast }),
    { disabled: props.disabled },
]);
</script>

<template>
    <a
        :href="url || 'javascript:void(0)'"
        :target="openInNewTab ? '_blank' : ''"
        class="cmk-link-card"
        :class="classes"
        @click="
            () => {
                if (props.callback) {
                    props.callback();
                }
            }
        "
    >
        <CmkIcon v-if="iconName" :name="iconName" size="xxlarge" class="cmk-link-card__icon" />
        <div class="cmk-link-card__text-area">
            <CmkHeading type="h4" class="cmk-link-card__heading">{{ title }}</CmkHeading>
            <CmkParagraph v-if="subtitle" class="cmk-link-card__subtitle">{{
                subtitle
            }}</CmkParagraph>
        </div>
        <CmkIcon v-if="openInNewTab" name="export-link" class="cmk-link-card__export-icon" />
    </a>
</template>

<style scoped>
.cmk-link-card--standard {
    border: var(--dimension-1) solid var(--ux-theme-6);

    --background-color: var(--ux-theme-1);

    &.cmk-link-card--high-contrast {
        --background-color: var(--ux-theme-3);

        border: var(--dimension-1) solid var(--ux-theme-8);
    }
}

.cmk-link-card--borderless {
    border: var(--dimension-1) solid transparent;

    --background-color: var(--ux-theme-2);

    &.cmk-link-card--high-contrast {
        --background-color: var(--ux-theme-3);
    }
}

.cmk-link-card {
    display: flex;
    align-items: center;
    text-decoration: none;
    border-radius: 4px;
    background-color: var(--background-color);
    padding: var(--dimension-4) var(--dimension-5);

    &:hover {
        background-color: color-mix(
            in srgb,
            var(--background-color),
            var(--background-hover-color) 10%
        );
    }

    &:focus,
    &:focus-visible {
        outline: var(--default-border-color-green) auto 1px;
    }

    &.disabled {
        opacity: 0.5;
        pointer-events: none;
        cursor: default;
    }
}

body[data-theme='facelift'] {
    .cmk-link-card {
        --background-hover-color: var(--black);
    }
}

body[data-theme='modern-dark'] {
    .cmk-link-card {
        --background-hover-color: var(--white);
    }
}

.cmk-link-card__icon {
    margin-right: var(--dimension-7);
}

.cmk-link-card__subtitle {
    color: var(--font-color-dimmed);
}

.cmk-link-card__export-icon {
    margin-left: auto;
}
</style>
