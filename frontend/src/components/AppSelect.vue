<template>
  <CmkDropdown
    :options="suggestions"
    :selected-option="modelValue || null"
    label=""
    @update:selected-option="emit('update:modelValue', $event ?? '')"
  />
</template>

<script setup lang="ts">
import CmkDropdown from '@cmk/components/CmkDropdown/CmkDropdown.vue';
import { computed } from 'vue';

const props = defineProps<{
  modelValue: string;
  options: { value: string; label: string }[];
}>();

const emit = defineEmits<{ 'update:modelValue': [value: string] }>();

const suggestions = computed(() => ({
  type: 'fixed' as const,
  suggestions: props.options.map((o) => ({ name: o.value, title: o.label })),
}));
</script>
