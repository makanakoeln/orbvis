<template>
    <div class="flex gap-2 flex-1 items-center">
        <label class="flex items-center gap-2 text-sm text-[var(--text)] cursor-pointer">
            <CmkSwitch :data="enabled" @update:data="setEnabled" />
            <span>{{ enableLabel }}</span>
        </label>
        <CmkColorPicker
            :data="displayedColor"
            :disabled="!enabled"
            @update:data="enabled && emit('update:modelValue', $event)"
        />
        <CmkInput
            :model-value="enabled ? displayedColor : ''"
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
    if (v == null || v === '') return false;
    return none === null ? true : v !== none;
});

// Swatch and hex-input both bind to this so the operator never sees the
// picker and the textbox showing different colors while picking. Falls back
// to the default tint when nothing is set yet.
const displayedColor = computed(() => {
    const v = props.modelValue;
    return v != null && v !== '' ? v : props.defaultColor;
});

function setEnabled(checked: boolean) {
    emit('update:modelValue', checked ? props.defaultColor : (props.noneValue ?? null));
}
</script>
