<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.

Vendored from cmk-frontend-vue (2.6 master) with OrbVis-specific patches:
  - Added size variant `narrow` (width 360px) for triage drawers.
  - Added `modal` prop (default true). When false, the overlay/backdrop is
    skipped and the underlying page stays interactive — the operator triages
    one host without losing access to the surrounding board.
  - Body overflow lock only applies in modal mode.
  - Added `portalTo` prop (CSS selector); when set, overrides the default
    body / #content_area target so the slide-in can live inside a specific
    container (e.g. the board canvas) instead of the page body.
-->
<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority';
import { DialogContent, DialogOverlay, DialogPortal, DialogRoot } from 'reka-ui';
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';

import { useSlideInStack } from './useSlideInStack';

const slideInVariants = cva('', {
    variants: {
        size: {
            medium: 'cmk-slide-in--size-medium',
            small: 'cmk-slide-in--size-small',
            narrow: 'cmk-slide-in--size-narrow',
        },
        borderColor: {
            default: 'cmk-slide-in--border-green',
            purple: 'cmk-slide-in--border-purple',
            none: 'cmk-slide-in--border-none',
        },
    },
    defaultVariants: {
        size: 'medium',
        borderColor: 'default',
    },
});

export type SlideInVariants = VariantProps<typeof slideInVariants>;

export interface CmkSlideInProps {
    open: boolean;
    size?: SlideInVariants['size'];
    isIndexPage?: boolean | undefined;
    ariaLabel?: string | undefined;
    stackPriority?: number | undefined;
    borderColor?: SlideInVariants['borderColor'];
    initialFocusTarget?: HTMLElement | undefined;
    modal?: boolean;
    portalTo?: string;
}

const props = withDefaults(defineProps<CmkSlideInProps>(), { modal: true });
const emit = defineEmits(['close']);
const dialogContentRef = ref<InstanceType<typeof DialogContent>>();

const { isTopMost, register, unregister } = useSlideInStack(props.stackPriority ?? null);
const effectiveOpen = computed(() => props.open && isTopMost.value);

watch(
    () => props.open,
    (isOpen) => {
        if (isOpen) {
            register();
        } else {
            unregister();
        }
    },
    { immediate: true },
);

watch(
    () => effectiveOpen.value,
    async (isOpen) => {
        if (isOpen) {
            await nextTick(() => {
                const target = props.initialFocusTarget ?? dialogContentRef.value?.$el;
                if (!(target instanceof HTMLElement)) {
                    return;
                }
                target.focus();
            });
        }
    },
);

onBeforeUnmount(() => {
    unregister();
});
</script>

<template>
    <DialogRoot v-if="open" :open="effectiveOpen" :modal="modal && !isIndexPage">
        <DialogPortal :to="portalTo ?? (isIndexPage ? '#content_area' : 'body')">
            <DialogOverlay
                v-if="modal && !isIndexPage && effectiveOpen"
                class="cmk-slide-in__overlay"
                @click="emit('close')"
            />
            <div
                v-if="modal && effectiveOpen"
                class="cmk-slide-in__overlay"
                @click="emit('close')"
            />
            <DialogContent
                ref="dialogContentRef"
                class="cmk-vue-app cmk-slide-in__container"
                :class="slideInVariants({ size: size, borderColor: borderColor })"
                :aria-describedby="undefined"
                :aria-label="props.ariaLabel"
                @escape-key-down="emit('close')"
                @open-auto-focus.prevent
                @close-auto-focus.prevent
                @pointer-down-outside="modal ? null : $event.preventDefault()"
                @interact-outside="modal ? null : $event.preventDefault()"
            >
                <slot />
            </DialogContent>
        </DialogPortal>
    </DialogRoot>
</template>

<style>
/* Body lock only applies when running in modal mode. */
body:has(.cmk-slide-in__container[data-modal='true']) {
    overflow: hidden;
}
</style>

<style scoped>
.cmk-slide-in__container {
    width: 80%;
    max-width: 1024px;
    display: flex;
    flex-direction: column;
    position: absolute;
    z-index: var(--z-index-modal, 30);
    top: 0;
    right: 0;
    bottom: 0;
    border-left: 4px solid var(--default-border-color-green);
    background: var(--default-bg-color, var(--bg-surface));

    &:focus,
    &:focus-visible {
        outline: none;
        box-shadow: none;
    }

    &.cmk-slide-in--size-small {
        max-width: 768px;
    }

    &.cmk-slide-in--size-narrow {
        width: 360px;
        max-width: 100vw;
    }

    &.cmk-slide-in--border-green {
        border-left-color: var(--default-border-color-green);
    }

    &.cmk-slide-in--border-purple {
        border-left-color: var(--border-color-purple);
    }

    &.cmk-slide-in--border-none {
        border-left: none;
    }

    &[data-state='open'] {
        animation: cmk-slide-in__container-show 0.2s ease-in-out;
    }

    &[data-state='closed'] {
        animation: cmk-slide-in__container-hide 0.2s ease-in-out;
    }
}

@media screen and (width <= 1024px) {
    .cmk-slide-in--size-medium {
        width: 100%;
        max-width: 100%;
    }
}

@media screen and (width <= 768px) {
    .cmk-slide-in--size-small {
        width: 100%;
        max-width: 100%;
    }
}

@keyframes cmk-slide-in__container-show {
    from {
        opacity: 0;
        transform: translate(50%, 0%);
    }

    to {
        opacity: 1;
        transform: translate(0%, 0%);
    }
}

@keyframes cmk-slide-in__container-hide {
    from {
        opacity: 1;
        transform: translate(0%, 0%);
    }

    to {
        opacity: 0;
        transform: translate(50%, 0%);
    }
}

.cmk-slide-in__overlay {
    backdrop-filter: blur(1.5px);
    position: absolute;
    inset: 0;
    animation: cmk-slide-in__overlay-show 150ms cubic-bezier(0.16, 1, 0.3, 1);
    z-index: var(--z-index-modal-overlay-offset, 29);
}

@keyframes cmk-slide-in__overlay-show {
    from {
        opacity: 0;
    }

    to {
        opacity: 1;
    }
}
</style>
