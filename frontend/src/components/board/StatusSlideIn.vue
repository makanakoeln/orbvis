<!--
  OrbVis-native slide-in shell for the board's status drawer.

  Why this exists instead of using the vendored `CmkSlideIn`:
    - Upstream CmkSlideIn is hardcoded `modal=true` (overlay + body inert),
      which kills board interaction while triaging a host. We want the
      operator to keep clicking around the board with the drawer open.
    - Upstream portals to `body` only; we want the drawer to live inside
      the board canvas container so the topbar/sidebar stay free.

  Kept outside `vendor/cmk/` so `npm run drift-check` stays clean —
  see scripts/cmk-vendor-patches.txt header for the shim strategy.
-->
<script setup lang="ts">
import { DialogContent, DialogPortal, DialogRoot } from 'reka-ui';

interface Props {
    open: boolean;
    ariaLabel?: string | undefined;
    portalTo?: string;
}

withDefaults(defineProps<Props>(), { portalTo: 'body', ariaLabel: undefined });
const emit = defineEmits<{ close: [] }>();
</script>

<template>
    <DialogRoot :open="open" :modal="false" @update:open="(v) => !v && emit('close')">
        <DialogPortal :to="portalTo">
            <DialogContent
                class="orb-status-slide-in"
                :aria-describedby="undefined"
                :aria-label="ariaLabel"
                @escape-key-down="emit('close')"
                @open-auto-focus.prevent
                @close-auto-focus.prevent
                @pointer-down-outside.prevent
                @interact-outside.prevent
            >
                <slot />
            </DialogContent>
        </DialogPortal>
    </DialogRoot>
</template>

<style scoped>
.orb-status-slide-in {
    width: 360px;
    max-width: 100vw;
    display: flex;
    flex-direction: column;
    position: absolute;
    z-index: var(--z-index-modal, 30);
    top: 0;
    right: 0;
    bottom: 0;
    background: var(--default-bg-color, var(--ux-theme-2, #20272e));
}

.orb-status-slide-in:focus,
.orb-status-slide-in:focus-visible {
    outline: none;
    box-shadow: none;
}

.orb-status-slide-in[data-state='open'] {
    animation: orb-status-slide-in-show 0.2s ease-in-out;
}

.orb-status-slide-in[data-state='closed'] {
    animation: orb-status-slide-in-hide 0.2s ease-in-out;
}

@media screen and (width <= 480px) {
    .orb-status-slide-in {
        width: 100%;
    }
}

@keyframes orb-status-slide-in-show {
    from {
        opacity: 0;
        transform: translate(50%, 0%);
    }

    to {
        opacity: 1;
        transform: translate(0%, 0%);
    }
}

@keyframes orb-status-slide-in-hide {
    from {
        opacity: 1;
        transform: translate(0%, 0%);
    }

    to {
        opacity: 0;
        transform: translate(50%, 0%);
    }
}
</style>
