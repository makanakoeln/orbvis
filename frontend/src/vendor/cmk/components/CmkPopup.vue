<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
Vendored from cmk-frontend-vue.
-->
<script setup lang="ts">
import { DialogContent, DialogOverlay, DialogPortal, DialogRoot } from 'reka-ui';
import { nextTick, ref, watch } from 'vue';

export interface CmkPopupProps {
    open: boolean;
}
const props = defineProps<CmkPopupProps>();

const emit = defineEmits(['close']);
const dialogContentRef = ref<InstanceType<typeof DialogContent>>();

watch(
    () => props.open,
    async (isOpen) => {
        if (isOpen) {
            await nextTick(() => {
                dialogContentRef.value?.$el.focus();
            });
        }
    },
);
</script>

<template>
    <DialogRoot :open="open">
        <DialogPortal>
            <!-- @vue-ignore @click is not a property of DialogOverlay -->
            <DialogOverlay class="cmk-popup__overlay" @click="emit('close')" />
            <!-- @vue-ignore aria-describedby is not a property of DialogContent -->
            <DialogContent
                ref="dialogContentRef"
                class="cmk-popup__container"
                :aria-describedby="undefined"
                @escape-key-down="emit('close')"
                @open-auto-focus.prevent
                @close-auto-focus.prevent
            >
                <slot />
            </DialogContent>
        </DialogPortal>
    </DialogRoot>
</template>

<style scoped>
.cmk-popup__container {
    min-width: 320px;
    display: flex;
    flex-direction: column;
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: var(--z-index-modal);
    box-shadow: 0 20px 60px rgb(0 0 0 / 50%);
    border-radius: var(--dimension-3);
    overflow: hidden;

    &[data-state='open'] {
        animation: cmk-popup__container-show 0.2s ease-in-out;
    }

    &[data-state='closed'] {
        animation: cmk-popup__container-hide 0.2s ease-in-out;
    }
}

@keyframes cmk-popup__container-show {
    from {
        opacity: 0;
        transform: translate(-50%, -48%) scale(0.96);
    }

    to {
        opacity: 1;
        transform: translate(-50%, -50%) scale(1);
    }
}

@keyframes cmk-popup__container-hide {
    from {
        opacity: 1;
    }

    to {
        opacity: 0;
    }
}

.cmk-popup__overlay {
    backdrop-filter: blur(1.5px);
    position: fixed;
    inset: 0;
    animation: cmk-popup__overlay-show 150ms cubic-bezier(0.16, 1, 0.3, 1);
    background: var(--color-popup-backdrop);
    z-index: var(--z-index-modal);
}

@keyframes cmk-popup__overlay-show {
    from {
        opacity: 0;
    }

    to {
        opacity: 1;
    }
}
</style>
