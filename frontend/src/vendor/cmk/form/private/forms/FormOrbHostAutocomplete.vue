<!--
OrbVis-only FormSpec component for ``orb_host_autocomplete`` (emitted
by backend ``OrbHostString``). CMK's FormAutocompleter is stubbed in
this build, so the field would otherwise fall back to a plain input.
Pulls suggestions from the connection id the parent modal exposes via
``inject('orbConnectionId')`` and renders them in a CmkDropdown.
-->
<script setup lang="ts">
import type { Ref } from 'vue';
import { computed, inject, onMounted, ref, watch } from 'vue';

import { connectionsApi } from '@/api/client';
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown';
import FormValidation from '@/components/user-input/CmkInlineValidation.vue';
import { useValidation, type ValidationMessages } from '@/form/private/validation';
import { useAuthStore } from '@/stores/auth';

interface OrbHostSpec {
    title?: string;
    label?: string | null;
    field_size: string;
    input_hint?: string | null;
    validators?: unknown[];
}

const props = defineProps<{
    spec: OrbHostSpec;
    backendValidation: ValidationMessages;
}>();

const data = defineModel<string>('data', { required: true });
const [validation, value] = useValidation<string>(
    data,
    (props.spec.validators ?? []) as never[],
    () => props.backendValidation,
);

const auth = useAuthStore();
const connectionId = inject<Ref<string>>('orbConnectionId', ref(''));
const hosts = ref<string[]>([]);

async function loadHosts() {
    const cid = connectionId.value;
    if (!cid) return;
    try {
        hosts.value = await connectionsApi.objects(cid, 'host', auth.accessToken!);
    } catch {
        hosts.value = [];
    }
}

onMounted(loadHosts);
watch(connectionId, () => {
    hosts.value = [];
    loadHosts();
});

const dropdownOptions = computed(() => ({
    type: 'filtered' as const,
    suggestions: hosts.value.map((name) => ({ name, title: name })),
}));

const hostStaleWarning = computed(() =>
    value.value && hosts.value.length && !hosts.value.includes(value.value)
        ? `Host "${value.value}" not in current connection`
        : '',
);

// CmkDropdown emits ``null`` when cleared; the FormSpec data is a
// plain string, so map back and forth at the binding boundary.
const dropdownValue = computed<string | null>({
    get: () => value.value || null,
    set: (v) => {
        value.value = v ?? '';
    },
});
</script>

<template>
    <div class="form-orb-host-autocomplete">
        <CmkDropdown
            v-model:selected-option="dropdownValue"
            :options="dropdownOptions"
            :label="spec.title ?? ''"
            :input-hint="spec.input_hint ?? ''"
            width="fill"
        />
        <p v-if="hostStaleWarning" class="form-orb-host-autocomplete__warning">
            {{ hostStaleWarning }}
        </p>
        <FormValidation :validation="validation" />
    </div>
</template>

<style scoped>
.form-orb-host-autocomplete {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.form-orb-host-autocomplete__warning {
    font-size: 0.75rem;
    color: var(--color-warning);
}
</style>
