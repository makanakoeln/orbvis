<!--
OrbVis-only FormSpec component. CMK's FormAutocompleter is stubbed in
this build (no axios-backed suggestion loader is wired up), so the
"Root host" field on flow boards used to be a free-text input.

Registered against the dispatcher under the type tag
``orb_host_autocomplete`` (emitted by backend OrbHostString). The
parent board-settings modal provides the currently-selected
``connection_id`` via Vue ``inject``; on focus we lazily fetch the
matching host list from ``GET /connections/{id}/objects?type=host`` and
hand it to the existing AutocompleteInput so the operator gets the
same picker as the EditPanel.
-->
<script setup lang="ts">
import type { Ref } from 'vue';
import { inject, onMounted, ref, watch } from 'vue';

import { connectionsApi } from '@/api/client';
import AutocompleteInput from '@/components/board/AutocompleteInput.vue';
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
// Parent modal exposes the currently-selected connection so the host
// picker always queries against the right backend.
const connectionId = inject<Ref<string>>('orbConnectionId', ref(''));
const hosts = ref<string[]>([]);
const loading = ref(false);

async function loadHosts() {
    const cid = connectionId.value;
    if (!cid || loading.value) return;
    loading.value = true;
    try {
        hosts.value = await connectionsApi.objects(cid, 'host', auth.accessToken!);
    } catch {
        hosts.value = [];
    } finally {
        loading.value = false;
    }
}

// Load on mount + whenever the operator switches the board's connection,
// so the dropdown has fresh suggestions ready by the time it opens.
onMounted(loadHosts);
watch(connectionId, () => {
    hosts.value = [];
    loadHosts();
});
</script>

<template>
    <div class="form-orb-host-autocomplete">
        <AutocompleteInput
            v-model="value"
            :suggestions="hosts"
            :loading="loading"
            :placeholder="spec.input_hint ?? ''"
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
