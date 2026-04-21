<template>
  <div class="flex gap-2 flex-1 items-center">
    <CmkCheckbox :model-value="isNone" :label="noneLabel" @update:model-value="toggleFromBool" />
    <template v-if="!isNone">
      <CmkColorPicker
        :data="modelValue ?? defaultColor"
        @update:data="emit('update:modelValue', $event)"
      />
      <CmkInput
        :model-value="modelValue ?? ''"
        :placeholder="defaultColor"
        field-size="FILL"
        class="flex-1"
        @update:model-value="emit('update:modelValue', $event as string)"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import CmkColorPicker from '@cmk/components/CmkColorPicker.vue';
import CmkCheckbox from '@cmk/components/user-input/CmkCheckbox.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { computed } from 'vue';

const props = defineProps<{
  modelValue: string | null | undefined;
  noneLabel: string;
  defaultColor: string;
  /** Sentinel stored when "none" — null (default) or a string like 'transparent'. */
  noneValue?: string | null;
}>();

const emit = defineEmits<{ 'update:modelValue': [string | null] }>();

const isNone = computed(() => {
  const v = props.modelValue;
  const none = props.noneValue ?? null;
  return none === null ? v == null : v == null || v === none;
});

function toggleFromBool(checked: boolean) {
  emit('update:modelValue', checked ? (props.noneValue ?? null) : props.defaultColor);
}
</script>
