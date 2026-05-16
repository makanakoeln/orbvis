<!--
OrbVis-only FormSpec component. The CMK FormSpec stack ships no color
picker (verified against cmk-frontend-vue 2.5 — only the 10 form types
in vendor/cmk/form/private/forms/ are exposed), so the Global Settings
"Label color" / "Label background" fields used to fall back to a plain
hex text input. This component is registered against the dispatcher
under the type tag ``orb_color`` (emitted by backend OrbColorString) and
provides three coordinated controls:

- a native ``<input type="color">`` swatch (single source of truth for
  the picker UX, plus mobile keyboard support),
- a free text field that accepts the hex code *or* the literal
  ``transparent`` (the only non-hex value the server-side regex allows),
- a ``Transparent`` chip that flips between the previously-picked hex
  and the literal — picker stays grayed-out while transparent is active
  so the operator never wonders why dragging the picker does nothing.
-->
<script setup lang="ts">
import { computed } from 'vue';

// Lives alongside the other vendored form components so the `@/...`
// vendor-relative import scheme just works and tsconfig's vendor-exclude
// keeps cmk-frontend-vue type errors out of the OrbVis build.
import CmkColorPicker from '@/components/CmkColorPicker.vue';
import FormValidation from '@/components/user-input/CmkInlineValidation.vue';
import CmkInput from '@/components/user-input/CmkInput.vue';
import FormLabel from '@/form/private/FormLabel.vue';
import { useValidation, type ValidationMessages } from '@/form/private/validation';
import { untranslated } from '@/lib/i18n';
import useId from '@/lib/useId';

// The serialised spec is a String + type "orb_color". We don't import
// the generated Components union here because "orb_color" isn't part of
// it; the dispatcher passes the spec through and we only read fields
// that both String and our serialiser provide.
interface OrbColorSpec {
    title?: string;
    label?: string | null;
    field_size: string;
    input_hint?: string | null;
    validators?: unknown[];
}

const props = defineProps<{
    spec: OrbColorSpec;
    backendValidation: ValidationMessages;
}>();

const data = defineModel<string>('data', { required: true });
const [validation, value] = useValidation<string>(
    data,
    (props.spec.validators ?? []) as never[],
    () => props.backendValidation,
);

const componentId = useId();

const isTransparent = computed(() => value.value === 'transparent');

// HTML5 type=color only understands 7-char hex. When the value is
// "transparent" (or an invalid intermediate state) the picker would
// silently snap to its own default and overwrite the operator's input.
// Hold a "last valid hex" so toggling Transparent off restores it.
const HEX_RE = /^#[0-9a-fA-F]{6}$/;
const fallbackHex = computed(() => (HEX_RE.test(value.value) ? value.value : '#ffffff'));

const swatchValue = computed<string>({
    get: () => (HEX_RE.test(value.value) ? value.value : fallbackHex.value),
    set: (v) => {
        value.value = v;
    },
});

function toggleTransparent() {
    if (isTransparent.value) {
        value.value = fallbackHex.value;
    } else {
        value.value = 'transparent';
    }
}
</script>

<template>
    <div class="form-orb-color">
        <template v-if="spec.label">
            <FormLabel :for="componentId">{{ spec.label }}</FormLabel>
        </template>

        <div class="form-orb-color__row">
            <CmkColorPicker
                v-model:data="swatchValue"
                :disabled="isTransparent"
                class="form-orb-color__swatch"
                :aria-label="untranslated((spec.label || spec.title || '') + ' picker')"
            />

            <CmkInput
                :id="componentId"
                v-model="value"
                type="text"
                :placeholder="untranslated(spec.input_hint || '#rrggbb')"
                :aria-label="untranslated(spec.label || spec.title || '')"
                :external-errors="validation"
                class="form-orb-color__hex"
            />

            <button
                type="button"
                class="form-orb-color__transparent"
                :class="{ 'form-orb-color__transparent--active': isTransparent }"
                :aria-pressed="isTransparent"
                @click="toggleTransparent"
            >
                Transparent
            </button>
        </div>

        <FormValidation :validation="validation" />
    </div>
</template>

<style scoped>
.form-orb-color {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.form-orb-color__row {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 8px;
}

/* The vendor CmkColorPicker is built for a wide WATO row; tighten it
   here so the swatch + hex + transparent chip read as one input
   group rather than three loose elements. */
.form-orb-color__swatch :deep(input) {
    width: 32px;
    height: 28px;
    border-radius: 4px;
    border: 1px solid var(--ux-theme-3, #555);
    margin-right: 0;
    cursor: pointer;
}

.form-orb-color__swatch :deep(input:disabled) {
    opacity: 0.4;
    cursor: not-allowed;
}

.form-orb-color__hex {
    flex: 0 0 auto;
    min-width: 180px;
}

.form-orb-color__transparent {
    background: transparent;
    color: var(--text-muted, #aaa);
    border: 1px dashed var(--ux-theme-3, #555);
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 12px;
    cursor: pointer;
    transition:
        background 120ms,
        color 120ms,
        border-color 120ms;
    /* Subtle checker pattern hints at "no fill" semantics without
       needing an image asset. */
    background-image: repeating-conic-gradient(rgb(255 255 255 / 8%) 0 25%, transparent 0 50%);
    background-size: 12px 12px;
}

.form-orb-color__transparent:hover {
    color: var(--text, #fff);
    border-color: var(--color-corporate-green-50, #15d1a0);
}

.form-orb-color__transparent--active {
    color: var(--bg-surface, #000);
    background-color: var(--color-corporate-green-50, #15d1a0);
    background-image: none;
    border-color: var(--color-corporate-green-50, #15d1a0);
    border-style: solid;
}
</style>
