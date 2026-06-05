<!--
OrbVis-native CmkInput, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone (see vite.config.ts STANDALONE_OVERRIDES).
-->
<script
  setup
  lang="ts"
  generic="T extends 'text' | 'number' | 'date' | 'time' | 'password' = 'text'"
>
import { computed, ref, watch } from 'vue'

defineOptions({ inheritAttrs: false })

type InputType = 'text' | 'number' | 'date' | 'time' | 'password'
type InputDataType<TT extends InputType> = TT extends 'number' ? number | undefined : string

// Field sizes mirror @cmk/components/user-input/sizes.ts so callers can
// pass the same SMALL/MEDIUM/LARGE/FILL tokens without code changes.
const FIELD_WIDTHS: Record<string, string> = {
  SMALL: '64px',
  MEDIUM: '184px',
  LARGE: '432px',
  FILL: '100%'
}

const {
  type = 'text' as T,
  fieldSize = 'SMALL',
  unit,
  externalErrors,
  validators,
  inline = false
} = defineProps<{
  type?: T
  fieldSize?: keyof typeof FIELD_WIDTHS
  unit?: string
  externalErrors?: string[]
  validators?: ((value: InputDataType<T>) => string[])[]
  inline?: boolean
}>()

const data = defineModel<InputDataType<T>>()
const validation = ref<string[]>([])
const width = computed(() => FIELD_WIDTHS[fieldSize] ?? FIELD_WIDTHS.SMALL)

const inputRef = ref<HTMLInputElement | null>(null)

defineExpose({
  focus: () => inputRef.value?.focus()
})

watch(data, (newData) => {
  if (newData !== undefined && validators && validators.length > 0) {
    validation.value = validators.flatMap((v) => v(newData))
  }
})

watch(
  () => externalErrors,
  (newErrors) => {
    validation.value = newErrors ?? []
  },
  { immediate: true }
)
</script>

<template>
  <div class="orb-input" :class="{ 'orb-input--inline': inline }">
    <ul v-if="validation.length > 0" class="orb-input__errors">
      <li v-for="(msg, idx) in validation" :key="idx">{{ msg }}</li>
    </ul>
    <div
      class="orb-input__field-row"
      :class="{ 'orb-input__field-row--fill': fieldSize === 'FILL' }"
    >
      <input
        ref="inputRef"
        v-model="data"
        v-bind="$attrs"
        class="orb-input__field"
        :class="{ 'orb-input__field--error': validation.length > 0 }"
        :style="{ width }"
        :type="type"
        step="any"
      />
      <span v-if="unit" class="orb-input__unit">{{ unit }}</span>
    </div>
  </div>
</template>

<style scoped>
.orb-input {
  display: block;
}

.orb-input--inline {
  display: inline-block;
}

.orb-input__field-row {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.orb-input__field-row--fill {
  display: flex;
}

.orb-input__field {
  background: var(--default-form-element-bg-color, #27272a);
  color: var(--font-color, #f4f4f5);
  border: 1px solid var(--default-form-element-border-color, #71717a);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 13px;
  font-family: inherit;
  box-sizing: border-box;
}

.orb-input__field:focus {
  outline: none;
  border-color: var(--color-corporate-green-50, #15d1a0);
  box-shadow: 0 0 0 2px
    color-mix(in srgb, var(--color-corporate-green-50, #15d1a0) 30%, transparent);
}

.orb-input__field--error {
  border-color: var(--inline-error-border-color, #ef4444);
}

.orb-input__field::placeholder {
  color: var(--font-color-dimmed, #9ca3af);
}

.orb-input__field:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.orb-input__unit {
  color: var(--text-muted, #9ca3af);
  font-size: 13px;
}

.orb-input__errors {
  color: var(--inline-error-text-color, #ef4444);
  font-size: 12px;
  margin: 0 0 4px;
  padding-left: 18px;
  list-style: disc;
}
</style>
