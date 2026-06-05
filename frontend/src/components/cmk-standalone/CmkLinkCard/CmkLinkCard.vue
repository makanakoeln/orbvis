<!--
OrbVis-native CmkLinkCard, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone. Drops the upstream CmkIcon dependency
because the standalone icon set is intentionally minimal; the icon prop
remains for API compatibility but is currently unrendered.
-->
<script setup lang="ts">
interface CmkLinkCardProps {
  iconName?: string | undefined
  title: string
  subtitle?: string
  url?: string | undefined
  callback?: () => void
  openInNewTab: boolean
  disabled?: boolean
  borders?: 'standard' | 'borderless'
  contrast?: 'standard' | 'high'
}
const props = withDefaults(defineProps<CmkLinkCardProps>(), {
  borders: 'standard',
  contrast: 'standard'
})
</script>

<template>
  <a
    :href="url || 'javascript:void(0)'"
    :target="openInNewTab ? '_blank' : ''"
    class="orb-link-card"
    :class="[
      `orb-link-card--${borders}`,
      `orb-link-card--contrast-${contrast}`,
      { 'orb-link-card--disabled': disabled }
    ]"
    @click="() => props.callback?.()"
  >
    <div class="orb-link-card__text">
      <h4 class="orb-link-card__heading">{{ title }}</h4>
      <p v-if="subtitle" class="orb-link-card__subtitle">{{ subtitle }}</p>
    </div>
    <span v-if="openInNewTab" class="orb-link-card__external" aria-hidden="true">↗</span>
  </a>
</template>

<style scoped>
.orb-link-card {
  display: flex;
  align-items: center;
  text-decoration: none;
  border-radius: 4px;
  padding: 8px 12px;
  color: var(--font-color, #f4f4f5);
  transition: background-color 120ms ease;
}

.orb-link-card--standard {
  border: 1px solid var(--ux-theme-6, #252c36);
  background-color: var(--ux-theme-1, #1c2228);
}

.orb-link-card--standard.orb-link-card--contrast-high {
  border-color: var(--ux-theme-8, #536279);
  background-color: var(--ux-theme-3, #262e36);
}

.orb-link-card--borderless {
  border: 1px solid transparent;
  background-color: var(--ux-theme-2, #20272e);
}

.orb-link-card--borderless.orb-link-card--contrast-high {
  background-color: var(--ux-theme-3, #262e36);
}

.orb-link-card:hover {
  background-color: var(--bg-hover, rgb(255 255 255 / 6%));
}

.orb-link-card:focus,
.orb-link-card:focus-visible {
  outline: 1px solid var(--color-corporate-green-50, #15d1a0);
}

.orb-link-card--disabled {
  opacity: 0.5;
  pointer-events: none;
  cursor: default;
}

.orb-link-card__heading {
  font-size: 13px;
  font-weight: 700;
  margin: 0;
}

.orb-link-card__subtitle {
  color: var(--font-color-dimmed, #9ca3af);
  margin: 2px 0 0;
  font-size: 12px;
}

.orb-link-card__external {
  margin-left: auto;
  color: var(--font-color-dimmed, #9ca3af);
}
</style>
