<template>
  <div class="flex gap-2 flex-1 items-center">
    <label class="flex items-center gap-1.5 text-xs text-zinc-400 cursor-pointer shrink-0">
      <input type="checkbox" :checked="isNone" class="accent-indigo-500" @change="toggle" />
      {{ noneLabel }}
    </label>
    <template v-if="!isNone">
      <input
        type="color"
        :value="modelValue ?? defaultColor"
        class="w-9 h-9 rounded-lg border-0 bg-transparent cursor-pointer p-0.5 shrink-0"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
      <input
        :value="modelValue ?? ''"
        class="field flex-1"
        :placeholder="defaultColor"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
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

function toggle(e: Event) {
  const checked = (e.target as HTMLInputElement).checked;
  emit('update:modelValue', checked ? (props.noneValue ?? null) : props.defaultColor);
}
</script>
