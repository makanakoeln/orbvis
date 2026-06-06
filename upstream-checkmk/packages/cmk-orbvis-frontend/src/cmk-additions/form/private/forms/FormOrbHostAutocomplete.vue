<!--
OrbVis-only FormSpec component for ``orb_host_autocomplete`` (emitted by backend
``OrbHostString``). CMK's native FormAutocompleter is stubbed in this build, so
this wires the vendored CmkDropdown's server-side ``callback-filtered`` mode to
OrbVis' own ``/objects?search=`` endpoint — the typed substring is filtered +
capped server-side (like cmk.gui's monitored_hostname_autocompleter), so it
scales to multi-million-host sites instead of streaming every name to the client.
The connection id comes from the parent modal via ``inject('orbConnectionId')``.
-->
<script setup lang="ts">
import type { Ref } from 'vue';
import { computed, inject, ref } from 'vue';

import { connectionsApi } from '@/api/client';
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown';
import { ErrorResponse, Response, type Suggestion } from '@cmk/components/CmkSuggestions';
import FormValidation from '@cmk/components/user-input/CmkInlineValidation.vue';
import { useValidation, type ValidationMessages } from '@cmk/form/private/validation';
import { untranslated } from '@cmk/lib/i18n';
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

// Server-side autocompleter: the typed query is filtered + limited at the
// source. CmkDropdown calls this on each keystroke and to resolve the label of
// an already-selected value.
async function querySuggestions(query: string): Promise<Response | ErrorResponse> {
    const cid = connectionId.value;
    if (!cid || !auth.accessToken) return new Response([]);
    try {
        const hosts = await connectionsApi.objects(cid, 'host', auth.accessToken, undefined, query);
        const choices: Suggestion[] = hosts.map((name) => ({ name, title: untranslated(name) }));
        return new Response(choices);
    } catch {
        return new ErrorResponse('Could not load hosts');
    }
}

const dropdownOptions = computed(() => ({
    type: 'callback-filtered' as const,
    querySuggestions,
}));

// CmkDropdown emits ``null`` when cleared; the FormSpec data is a plain string,
// so map back and forth at the binding boundary.
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
        <FormValidation :validation="validation" />
    </div>
</template>

<style scoped>
.form-orb-host-autocomplete {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
</style>
