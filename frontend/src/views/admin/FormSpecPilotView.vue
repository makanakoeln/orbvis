<template>
    <div class="max-w-2xl">
        <CmkHeading type="h2">FormSpec Pilot</CmkHeading>
        <CmkParagraph>
            Vendor smoke test — renders a small Dictionary built from backend FormSpec. Replaced by
            the real GlobalSettings view in Phase A.
        </CmkParagraph>
        <div v-if="schema" style="margin-top: var(--dimension-5)">
            <FormApp
                id="orbvis-pilot"
                :spec="schema"
                :data="data"
                :validation="[]"
                display_mode="edit"
            />
        </div>
    </div>
</template>

<script setup lang="ts">
import CmkHeading from '@cmk/components/typography/CmkHeading.vue';
import CmkParagraph from '@cmk/components/typography/CmkParagraph.vue';
import FormApp from '@cmk/form/FormApp.vue';
import { initializeComponentRegistry } from '@cmk/form/private/FormEditDispatcher/dispatch';
import type { Components } from 'cmk-shared-typing/typescript/vue_formspec_components';
import { ref } from 'vue';

initializeComponentRegistry();

const schema = ref<Components | null>(null);
const data = ref<unknown>({});
</script>
