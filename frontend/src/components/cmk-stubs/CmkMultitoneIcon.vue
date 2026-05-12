<!--
OrbVis stub for CmkMultitoneIcon. Loads SVGs statically via import.meta.glob
to avoid the dynamic template-literal import that breaks Vite's asset graph.
Add new icons by dropping the corresponding `icon-<name>.svg` into
`frontend/src/assets/icons/` — they'll be picked up automatically.
-->
<template>
    <!-- eslint-disable-next-line vue/no-v-html -->
    <div v-if="svg" class="cmk-multitone-icon" :title="title" v-html="svg" />
</template>

<script setup lang="ts">
import { computed } from 'vue';

const svgModules = import.meta.glob('@/assets/icons/icon-*.svg', {
    eager: true,
    query: '?raw',
    import: 'default',
}) as Record<string, string>;

interface PrimaryColor {
    custom?: string;
}

const props = defineProps<{
    name?: string;
    size?: string;
    primaryColor?: PrimaryColor | string | null;
    title?: string;
}>();

const svg = computed(() => {
    if (!props.name) return null;
    const key = Object.keys(svgModules).find((k) => k.endsWith(`/icon-${props.name}.svg`));
    return key ? svgModules[key] : null;
});

const customColor = computed(() => {
    if (
        props.primaryColor &&
        typeof props.primaryColor === 'object' &&
        'custom' in props.primaryColor &&
        props.primaryColor.custom
    ) {
        return props.primaryColor.custom;
    }
    return 'currentColor';
});
</script>

<style>
/* Not scoped: v-html injects the SVG outside the scoped-CSS attribute boundary
   so the `svg .icon-primary-color` selector wouldn't match otherwise. */

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-multitone-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;

    --icon-primary-color: v-bind('customColor');
    --icon-secondary-color: v-bind('customColor');
    --icon-tertiary-color: v-bind('customColor');
}

.cmk-multitone-icon svg {
    width: 18px;
    height: 18px;
}

.cmk-multitone-icon svg .icon-primary-color {
    fill: var(--icon-primary-color);
}

.cmk-multitone-icon svg .icon-secondary-color {
    fill: var(--icon-secondary-color);
}

.cmk-multitone-icon svg .icon-tertiary-color {
    fill: var(--icon-tertiary-color);
}
</style>
