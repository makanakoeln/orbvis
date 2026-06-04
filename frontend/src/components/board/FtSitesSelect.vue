<!--
Multi-site picker for foldertree board settings: a CmkDropdown adds one site at a
time, selected sites show as removable chips. Mirrors FormOrbHostAutocomplete's
reuse of CmkDropdown rather than vendoring CMK's (stubbed) multi-choice form.
-->
<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown';

const props = defineProps<{
    modelValue: string[];
    options: { id: string; alias: string }[];
}>();
const emit = defineEmits<{ 'update:modelValue': [string[]] }>();

const { t } = useI18n();

const aliasOf = (id: string) => props.options.find((o) => o.id === id)?.alias ?? id;

// Only sites not already picked are offered; an empty list collapses the
// dropdown to its "no elements" state.
const available = computed(() => ({
    type: 'filtered' as const,
    suggestions: props.options
        .filter((o) => !props.modelValue.includes(o.id))
        .map((o) => ({ name: o.id, title: o.alias })),
}));

function add(id: string | null) {
    if (id && !props.modelValue.includes(id)) {
        emit('update:modelValue', [...props.modelValue, id]);
    }
}
function remove(id: string) {
    emit(
        'update:modelValue',
        props.modelValue.filter((s) => s !== id),
    );
}
</script>

<template>
    <div class="ft-sites">
        <div v-if="modelValue.length" class="ft-sites__chips">
            <span v-for="id in modelValue" :key="id" class="ft-sites__chip">
                {{ aliasOf(id) }}
                <button
                    type="button"
                    class="ft-sites__remove"
                    :aria-label="t('board.ftSitesRemove', { site: aliasOf(id) })"
                    @click="remove(id)"
                >
                    ×
                </button>
            </span>
        </div>
        <CmkDropdown
            :selected-option="null"
            :options="available"
            width="fill"
            :label="t('board.ftSites')"
            :input-hint="t('board.ftSitesPlaceholder')"
            @update:selected-option="add"
        />
    </div>
</template>

<style scoped>
.ft-sites {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-2);
}

.ft-sites__chips {
    display: flex;
    flex-wrap: wrap;
    gap: var(--dimension-2);
}

.ft-sites__chip {
    display: inline-flex;
    align-items: center;
    gap: var(--dimension-2);
    padding: 2px var(--dimension-3);
    border-radius: var(--dimension-2);
    background: var(--bg-hover);
    border: 1px solid var(--border);
    font-size: var(--font-size-small, 0.8125rem);
    color: var(--text);
}

.ft-sites__remove {
    border: 0;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 1rem;
    line-height: 1;
    padding: 0;
}

.ft-sites__remove:hover {
    color: var(--text);
}
</style>
