<template>
    <div class="flex gap-2 flex-1 items-center">
        <label class="flex items-center gap-2 text-sm text-[var(--text)] cursor-pointer">
            <CmkSwitch :data="enabled" @update:data="setEnabled" />
            <span>{{ enableLabel }}</span>
        </label>
        <CmkColorPicker
            :data="modelValue ?? defaultColor"
            :disabled="!enabled"
            @update:data="enabled && emit('update:modelValue', $event)"
        />
        <CmkInput
            :model-value="enabled ? (modelValue ?? '') : ''"
            :placeholder="defaultColor"
            field-size="FILL"
            class="flex-1"
            :disabled="!enabled"
            @update:model-value="enabled && emit('update:modelValue', $event as string)"
        />
    </div>
</template>

<script setup lang="ts">
import CmkColorPicker from '@cmk/components/CmkColorPicker.vue';
import CmkSwitch from '@cmk/components/CmkSwitch.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { computed } from 'vue';

const props = defineProps<{
    modelValue: string | null | undefined;
    enableLabel: string;
    defaultColor: string;
    /** Sentinel stored when "off" — null (default) or a string like 'transparent'. */
    noneValue?: string | null;
}>();

const emit = defineEmits<{ 'update:modelValue': [string | null] }>();

const enabled = computed(() => {
    const v = props.modelValue;
    const none = props.noneValue ?? null;
    return none === null ? v != null : v != null && v !== none;
});

function setEnabled(checked: boolean) {
    emit('update:modelValue', checked ? props.defaultColor : (props.noneValue ?? null));
}
</script>
