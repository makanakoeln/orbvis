<!--
OrbVis-native CmkIcon, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone. Renders a Unicode glyph for common icon
names so standalone deployments don't depend on the
``/<site>/check_mk/themes/...`` icon tree. Unknown names fall back to a
small dot glyph so the layout stays stable.
-->
<script setup lang="ts">
import { computed } from 'vue'

interface CmkIconProps {
  name: string
  variant?: string
  size?: 'xxsmall' | 'xsmall' | 'small' | 'medium' | 'large' | 'xlarge' | 'xxlarge' | 'xxxlarge'
  colored?: boolean | string
  rotate?: number
  title?: string
}

const props = defineProps<CmkIconProps>()

const GLYPHS: Record<string, string> = {
  add: '+',
  'add-graph': '+',
  'add-host': '+',
  'add-rule': '+',
  close: '×',
  'close-only': '×',
  delete: '🗑',
  edit: '✎',
  info: 'ℹ',
  'info-circle': 'ℹ',
  help: '?',
  'help-activated': '?',
  error: '⚠',
  warning: '⚠',
  success: '✓',
  checkmark: '✓',
  save: '💾',
  cancel: '×',
  abort: '×',
  'load-graph': '↺',
  'export-link': '↗',
  'dashboard-main': '⊞',
  'main-setup': '⚙',
  settings: '⚙',
  completion: '✓',
  main: '⊞',
  arrow: '→',
  'arrow-down': '▾',
  'arrow-right': '▸',
  'arrow-left': '◂',
  'arrow-up': '▴',
  user: '👤',
  search: '🔍',
  refresh: '↻',
  download: '⬇',
  upload: '⬆'
}

const glyph = computed(() => GLYPHS[props.name] ?? '·')
const rotationStyle = computed(() => ({ transform: `rotate(${props.rotate || 0}deg)` }))
</script>

<template>
  <span
    class="orb-icon"
    :class="`orb-icon--${size || 'medium'}`"
    :style="rotationStyle"
    :title="title || undefined"
    :aria-label="title || undefined"
    role="img"
  >
    {{ glyph }}
  </span>
</template>

<style scoped>
.orb-icon {
  display: inline-block;
  line-height: 1;
  vertical-align: baseline;
  font-style: normal;
  text-align: center;
}

.orb-icon--xxsmall {
  font-size: 8px;
}

.orb-icon--xsmall {
  font-size: 10px;
}

.orb-icon--small {
  font-size: 12px;
}

.orb-icon--medium {
  font-size: 15px;
}

.orb-icon--large {
  font-size: 18px;
}

.orb-icon--xlarge {
  font-size: 20px;
}

.orb-icon--xxlarge {
  font-size: 32px;
}

.orb-icon--xxxlarge {
  font-size: 77px;
}
</style>
