<!--
    Livestatus filter for "all hosts" / "all services" radar boards (NagVis
    dynmap_object_filter). Shared by the FormSpec and the legacy settings modal.
-->
<template>
  <div class="radar-filter">
    <CmkLabel
      :help="
        _t(
          'Optional. Narrows the radar to the hosts or services matching these Livestatus lines (Filter:, And:, Or:, Negate:), like a NagVis dynamic map. Leave empty to show everything.'
        )
      "
      >{{ _t('Livestatus filter') }}</CmkLabel
    >
    <textarea
      v-model="model"
      class="orb-field radar-filter__input"
      :class="{ 'radar-filter__input--invalid': invalid }"
      rows="3"
      spellcheck="false"
      :placeholder="placeholder"
      :aria-invalid="invalid"
    />
    <p v-if="invalid" class="radar-filter__error">
      {{ _t("Use one or more 'Filter:', 'And:', 'Or:' or 'Negate:' lines.") }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import CmkLabel from '@/components/cmk/CmkLabel'

import { isValidLqlFilter } from '@/utils/lqlFilter'
import usei18n from '@/vendor/cmk/lib/i18n'

const { _t } = usei18n()

const props = defineProps<{
  objectTypes: 'host' | 'service'
}>()

const model = defineModel<string>({ required: true })

const invalid = computed(() => model.value.trim() !== '' && !isValidLqlFilter(model.value))

const placeholder = computed(() =>
  props.objectTypes === 'service'
    ? 'Filter: description ~ ^Interface\nFilter: state != 0'
    : 'Filter: host_name ~ ^fw-\nFilter: labels = cmk/os_family linux'
)
</script>

<style scoped>
.radar-filter {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.radar-filter__input {
  font-family:
    ui-monospace, sfmono-regular, menlo, monaco, consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: var(--font-size-normal);
  line-height: 16px;
  resize: vertical;
}

.radar-filter__input--invalid {
  box-shadow: 0 0 0 1px var(--form-element-required-color);
}

.radar-filter__error {
  margin: 0;
  font-size: var(--font-size-normal);
  color: var(--form-element-required-color);
}
</style>
