<!--
OrbVis-native CmkLabel, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone (see vite.config.ts STANDALONE_OVERRIDES).
-->
<script setup lang="ts">
import { computed, useAttrs } from 'vue';

defineOptions({ inheritAttrs: false });

export interface LabelProps {
    for?: string;
    variant?: 'default' | 'title' | 'subtitle';
    dots?: boolean | undefined;
    help?: string | undefined;
    cursor?: 'default' | 'pointer';
}

const props = withDefaults(defineProps<LabelProps>(), {
    variant: 'default',
    cursor: 'default',
});

const attrs = useAttrs();
const delegated = computed(() => {
    const { variant: _v, help: _h, cursor: _c, ...rest } = attrs;
    if (props.for) rest.for = props.for;
    return rest;
});
</script>

<template>
    <div class="orb-label">
        <span class="orb-label__content">
            <label
                v-bind="delegated"
                :class="[
                    `orb-label--variant-${variant}`,
                    { 'orb-label--cursor-pointer': cursor === 'pointer' },
                ]"
                ><slot
            /></label>
            <span v-if="help" class="orb-label__help" :title="help">&nbsp;?</span>
        </span>
        <div v-if="dots" class="orb-label__dots" />
    </div>
</template>

<style scoped>
.orb-label {
    display: inline-flex;
    min-width: 0;
    max-width: 100%;
}

.orb-label__content {
    flex: 0 1 auto;
    min-width: 0;
}

.orb-label--variant-title {
    height: 24px;
    align-content: center;
    font-weight: var(--font-weight-bold, 700);
    font-size: var(--font-size-xlarge, 15px);
}

.orb-label--variant-subtitle {
    font-size: var(--font-size-normal, 13px);
    margin-bottom: var(--spacing, 10px);
}

.orb-label--cursor-pointer {
    cursor: pointer;
}

.orb-label__help {
    color: var(--font-color-dimmed, #9ca3af);
    cursor: help;
    margin-left: 2px;
}

.orb-label__dots {
    flex: 1 0 0;
    margin-left: 5px;
    color: var(--font-color-dimmed, #9ca3af);
    overflow: hidden;
    min-width: 15px;
}

.orb-label__dots::after {
    content: '..............................................................................................................................';
}
</style>
