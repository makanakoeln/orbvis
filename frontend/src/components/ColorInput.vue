<template>
    <div class="orb-color-input">
        <label v-if="enableLabel !== undefined" class="orb-color-input__toggle">
            <CmkSwitch :data="enabled" @update:data="setEnabled" />
            <span>{{ enableLabel }}</span>
        </label>
        <div
            class="orb-color-input__swatch"
            :class="{ 'orb-color-input__swatch--disabled': !enabled }"
        >
            <CmkColorPicker
                :data="displayedColor"
                :disabled="!enabled"
                @update:data="enabled && emit('update:modelValue', $event)"
            />
        </div>
        <CmkInput
            :model-value="enabled ? displayedColor : ''"
            :placeholder="defaultColor"
            field-size="FILL"
            class="orb-color-input__field"
            :disabled="!enabled"
            :validators="hexValidators"
            @update:model-value="enabled && emit('update:modelValue', $event as string)"
        />
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import CmkColorPicker from '@/components/cmk/CmkColorPicker';
import CmkSwitch from '@/components/cmk/CmkSwitch';
import CmkInput from '@/components/cmk/user-input/CmkInput';

const props = defineProps<{
    modelValue: string | null | undefined;
    /** When set, renders a toggle that lets the operator switch the colour
        on/off (storing ``noneValue`` when off). When undefined, the picker
        is always active. */
    enableLabel?: string;
    defaultColor: string;
    /** Sentinel stored when "off" — null (default) or a string like 'transparent'. */
    noneValue?: string | null;
}>();

const emit = defineEmits<{ 'update:modelValue': [string | null] }>();

const { t } = useI18n();

const enabled = computed(() => {
    if (props.enableLabel === undefined) return true;
    const v = props.modelValue;
    const none = props.noneValue ?? null;
    if (v == null || v === '') return false;
    return none === null ? true : v !== none;
});

const displayedColor = computed(() => {
    const v = props.modelValue;
    return v != null && v !== '' ? v : props.defaultColor;
});

const HEX_RE = /^#[0-9a-fA-F]{6}$/;

const hexValidators = computed(() =>
    enabled.value
        ? [
              (value: string) => {
                  const v = (value ?? '').trim();
                  if (!v) return [];
                  if (v === (props.noneValue ?? '')) return [];
                  return HEX_RE.test(v) ? [] : [t('common.invalidHex')];
              },
          ]
        : [],
);

function setEnabled(checked: boolean) {
    emit('update:modelValue', checked ? props.defaultColor : (props.noneValue ?? null));
}
</script>

<style scoped>
.orb-color-input {
    display: flex;
    flex: 1;
    align-items: center;
    gap: 8px;
}

.orb-color-input__toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    font-size: 0.875rem;
    color: var(--text);
}

.orb-color-input__field {
    flex: 1;
}

/* Larger, square color swatch. Overrides the vendored CmkColorPicker's
   26x30 + margin-right via :deep so the swatch lines up flush with the
   adjacent hex input instead of floating with a doubled gap. */
.orb-color-input__swatch {
    display: inline-flex;
    align-items: stretch;
}

.orb-color-input__swatch :deep(.cmk-color-picker),
.orb-color-input__swatch :deep(.orb-color-picker) {
    margin: 0;
    width: 32px;
    height: 32px;
    border-radius: 6px;
    overflow: hidden;
    cursor: pointer;
}

.orb-color-input__swatch--disabled :deep(.cmk-color-picker),
.orb-color-input__swatch--disabled :deep(.orb-color-picker) {
    opacity: 0.4;
    cursor: not-allowed;
}
</style>
