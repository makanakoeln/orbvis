<!--
OrbVis-native CmkCollapsible, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone. Plain Vue <Transition> with CSS keyframes;
no scss dependency.
-->
<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';

interface CmkCollapsibleProps {
    open: boolean;
    contentId?: string | undefined;
}
const props = defineProps<CmkCollapsibleProps>();

const contentRef = ref<HTMLElement | null>(null);
const heightCSS = ref<string>('auto');

watch(
    () => [props.open, contentRef.value],
    async () => {
        await nextTick();
        if (!contentRef.value) return;
        const prevTransition = contentRef.value.style.transitionDuration;
        const prevAnimation = contentRef.value.style.animationName;
        contentRef.value.style.transitionDuration = '0ms';
        contentRef.value.style.animationName = 'none';
        heightCSS.value = `${contentRef.value.getBoundingClientRect().height}px`;
        contentRef.value.style.transitionDuration = prevTransition;
        contentRef.value.style.animationName = prevAnimation;
    },
    { immediate: true },
);
</script>

<template>
    <Transition name="orb-collapsible-content">
        <div
            v-show="open"
            :id="contentId"
            ref="contentRef"
            :style="{ '--orb-target-h': heightCSS }"
        >
            <slot />
        </div>
    </Transition>
</template>

<style scoped>
.orb-collapsible-content-enter-active {
    animation: orb-slide-down 300ms ease-out;
    overflow: hidden;
}

.orb-collapsible-content-leave-active {
    animation: orb-slide-up 300ms ease-out;
    overflow: hidden;
}

@keyframes orb-slide-down {
    from {
        height: 0;
        opacity: 0;
    }

    to {
        height: var(--orb-target-h);
        opacity: 1;
    }
}

@keyframes orb-slide-up {
    from {
        height: var(--orb-target-h);
        opacity: 1;
    }

    to {
        height: 0;
        opacity: 0;
    }
}
</style>
