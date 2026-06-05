/**
 * Empty shim for ``lucide-vue-next``. CMK's FormString.vue imports
 * ``{ X }`` for the autocompleter clear-button — a branch the OrbVis
 * Pilot never enters — so we stub the package out via ``resolve.alias``
 * (see ``frontend/vite.config.ts``) instead of shipping the full
 * dependency.
 */
import { defineComponent, h } from 'vue'

const EmptyIcon = defineComponent({ name: 'LucideStub', render: () => h('span') })

export const X = EmptyIcon
export default EmptyIcon
