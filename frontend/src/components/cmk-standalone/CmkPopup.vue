<!--
OrbVis-native CmkPopup, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone. Same reka-ui Dialog stack as upstream;
only the class names and theme tokens are OrbVis-local.
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
            await nextTick(() => dialogContentRef.value?.$el.focus());
        }
    },
);
</script>

<template>
    <DialogRoot :open="open">
        <DialogPortal>
            <!-- @vue-ignore @click is not a property of DialogOverlay -->
            <DialogOverlay class="orb-popup__overlay" @click="emit('close')" />
            <!-- @vue-ignore aria-describedby it not a property of DialogContent -->
            <DialogContent
                ref="dialogContentRef"
                class="orb-popup__container"
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
.orb-popup__container {
    min-width: 450px;
    display: flex;
    flex-direction: column;
    position: fixed;
    align-items: center;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 1000;
    background: var(--default-bg-color, var(--ux-theme-2, #20272e));
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 8px 24px rgb(0 0 0 / 40%);
}

.orb-popup__container[data-state='open'] {
    animation: orb-popup-show 0.2s ease-in-out;
}

.orb-popup__container[data-state='closed'] {
    animation: orb-popup-hide 0.15s ease-in-out;
}

.orb-popup__overlay {
    backdrop-filter: blur(1.5px);
    position: fixed;
    inset: 0;
    background: rgb(0 0 0 / 50%);
    z-index: 999;
    animation: orb-popup-overlay-show 150ms cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes orb-popup-show {
    from {
        opacity: 0;
        transform: translate(-50%, -48%) scale(0.96);
    }

    to {
        opacity: 1;
        transform: translate(-50%, -50%) scale(1);
    }
}

@keyframes orb-popup-hide {
    from {
        opacity: 1;
    }

    to {
        opacity: 0;
    }
}

@keyframes orb-popup-overlay-show {
    from {
        opacity: 0;
    }

    to {
        opacity: 1;
    }
}
</style>
