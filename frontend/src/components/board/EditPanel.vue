<template>
  <div class="flex flex-col min-h-0 text-sm">
    <!-- Header -->
    <div
      class="border-b border-white/8 flex items-center gap-[8px] shrink-0"
      style="padding: 10px 16px"
    >
      <svg
        class="text-[var(--color-corporate-green-50)] shrink-0"
        style="width: 14px; height: 14px"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2.5"
      >
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      <div class="flex-1 min-w-0">
        <div class="font-semibold text-[var(--text)] text-sm">
          {{ t('boardSettings.addObject') }}
        </div>
        <div class="text-[10px] mt-[2px]" :class="placing ? 'text-amber-400/70' : 'text-zinc-500'">
          {{ placing ? t('boardSettings.clickToPlace') : t('boardSettings.dragObjects') }}
        </div>
      </div>
    </div>

    <!-- Add Object form -->
    <div class="space-y-[8px]" style="padding: 10px 16px">
      <CmkDropdown
        :selected-option="draft.type"
        :options="objectTypeOptions"
        :width="'fill'"
        :label="t('boardSettings.selectType')"
        @update:selected-option="
          (v) => {
            draft.type = v as ObjectType | '';
            onTypeChange();
          }
        "
      />

      <template v-if="draft.type === 'host'">
        <AutocompleteInput
          v-model="draft.host_name"
          :suggestions="addObjects"
          :loading="loadingAddObjects"
          :placeholder="t('boardSettings.hostname')"
        />
      </template>

      <template v-else-if="draft.type === 'service'">
        <AutocompleteInput
          v-model="draft.host_name"
          :suggestions="addObjects"
          :loading="loadingAddObjects"
          :placeholder="t('boardSettings.hostname')"
          @change="onHostChange"
        />
        <AutocompleteInput
          v-model="draft.service_description"
          :suggestions="addServices"
          :loading="loadingAddServices"
          :placeholder="t('boardSettings.serviceDescription')"
        />
      </template>

      <template v-else-if="draft.type === 'hostgroup' || draft.type === 'servicegroup'">
        <AutocompleteInput
          v-model="draft.group_name"
          :suggestions="addObjects"
          :loading="loadingAddObjects"
          :placeholder="t('boardSettings.groupName')"
        />
      </template>

      <template v-else-if="draft.type === 'map'">
        <AutocompleteInput
          v-model="draft.board_name"
          :suggestions="boardNames"
          :display-labels="boardLabels"
          :loading="boardsStore.loading"
          :placeholder="t('boardSettings.boardName')"
        />
        <input
          v-model="draft.label_text"
          :placeholder="t('boardSettings.labelOptional')"
          class="field"
        />
      </template>

      <template v-else-if="draft.type === 'line'">
        <AutocompleteInput
          v-model="draft.host_name"
          :suggestions="addObjects"
          :loading="loadingAddObjects"
          :placeholder="t('boardSettings.hostname') + ' (optional)'"
          @change="onHostChange"
        />
        <AutocompleteInput
          v-model="draft.service_description"
          :suggestions="addServices"
          :loading="loadingAddServices"
          :placeholder="t('boardSettings.serviceOptional')"
        />
      </template>

      <template v-else-if="draft.type === 'textbox'">
        <input
          v-model="draft.label_text"
          :placeholder="t('boardSettings.textContent')"
          class="field"
        />
      </template>

      <template v-else-if="draft.type === 'image'">
        <ImagePicker v-model="draft.image_src" />
        <input
          v-model="draft.label_text"
          :placeholder="t('boardSettings.labelOptional')"
          class="field"
        />
      </template>

      <template v-else-if="draft.type === 'graph'">
        <AutocompleteInput
          v-model="draft.host_name"
          :suggestions="addObjects"
          :loading="loadingAddObjects"
          :placeholder="t('boardSettings.hostname')"
          @change="onHostChange"
        />
        <AutocompleteInput
          v-model="draft.service_description"
          :suggestions="addServices"
          :loading="loadingAddServices"
          :placeholder="t('boardSettings.serviceOptional')"
        />
        <input
          v-model="draft.graph_url"
          :placeholder="t('boardSettings.graphUrl') + ' (optional)'"
          class="field font-mono text-xs"
        />
      </template>

      <!-- Grid snap -->
      <div class="flex items-center justify-between gap-[8px]">
        <label class="text-xs text-zinc-500 select-none">{{ t('boardSettings.grid') }}</label>
        <CmkDropdown
          class="w-[96px]"
          :selected-option="String(snapGrid)"
          :options="snapGridOptions"
          label=""
          @update:selected-option="(v) => $emit('update:snapGrid', Number(v))"
        />
      </div>

      <CmkButton
        v-if="draft.type"
        :variant="placing ? 'warning' : 'primary'"
        :disabled="!canPlace"
        :class="['w-full', placing ? 'animate-pulse' : '']"
        @click="canPlace && $emit('start-placing')"
      >
        {{ placing ? t('boardSettings.clickToPlace') : t('boardSettings.placeOnBoard') }}
      </CmkButton>
      <p v-if="draft.type && !canPlace && !placing" class="text-xs text-zinc-500 text-center">
        {{ missingFieldHint }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkDropdown from '@cmk/components/CmkDropdown/CmkDropdown.vue';
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { connectionsApi } from '@/api/client';
import type { NewObjectDraft } from '@/composables/useBoardEditor';
import { useAuthStore } from '@/stores/auth';
import { useBoardsStore } from '@/stores/boards';
import type { ObjectType } from '@/types/api';

import AutocompleteInput from './AutocompleteInput.vue';
import ImagePicker from './ImagePicker.vue';

const { t } = useI18n();

const objectTypeOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: '', title: t('boardSettings.selectType') },
    { name: 'host', title: t('boardSettings.typeHost') },
    { name: 'service', title: t('boardSettings.typeService') },
    { name: 'hostgroup', title: t('boardSettings.typeHostgroup') },
    { name: 'servicegroup', title: t('boardSettings.typeServicegroup') },
    { name: 'map', title: t('boardSettings.typeMap') },
    { name: 'line', title: t('boardSettings.typeLine') },
    { name: 'textbox', title: t('boardSettings.typeTextbox') },
    { name: 'image', title: t('boardSettings.typeImage') },
    { name: 'graph', title: `${t('boardSettings.typeGraph')} (experimental)` },
  ],
}));
const snapGridOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: '0', title: t('boardSettings.gridOff') },
    { name: '10', title: '10 px' },
    { name: '20', title: '20 px' },
    { name: '50', title: '50 px' },
  ],
}));

const props = defineProps<{
  draft: NewObjectDraft;
  placing: boolean;
  backendId: string;
  snapGrid: number;
}>();

defineEmits<{
  'start-placing': [];
  'update:snapGrid': [value: number];
  'close-edit-mode': [];
}>();

const auth = useAuthStore();
const boardsStore = useBoardsStore();
const boardNames = computed(() => boardsStore.boards.map((b) => b.name));
const boardLabels = computed(() => boardsStore.boards.map((b) => b.alias || b.name));

const MISSING_FIELD_KEY: Record<string, string> = {
  host: 'boardSettings.hostname',
  hostgroup: 'boardSettings.groupName',
  servicegroup: 'boardSettings.groupName',
  map: 'boardSettings.boardName',
};

const canPlace = computed(() => {
  const d = props.draft;
  switch (d.type) {
    case 'host':
      return !!d.host_name;
    case 'service':
      return !!d.host_name && !!d.service_description;
    case 'hostgroup':
    case 'servicegroup':
      return !!d.group_name;
    case 'map':
      return !!d.board_name;
    case 'line':
    case 'textbox':
    case 'image':
    case 'graph':
      return true;
    default:
      return false;
  }
});

const missingFieldHint = computed(() => {
  if (canPlace.value) return '';
  const d = props.draft;
  if (d.type === 'service')
    return `↑ ${t(d.host_name ? 'boardSettings.serviceDescription' : 'boardSettings.hostname')}`;
  return MISSING_FIELD_KEY[d.type] ? `↑ ${t(MISSING_FIELD_KEY[d.type])}` : '';
});

const addObjects = ref<string[]>([]);
const addServices = ref<string[]>([]);
const loadingAddObjects = ref(false);
const loadingAddServices = ref(false);

async function fetchAddObjects(type: string) {
  if (
    !props.backendId ||
    !type ||
    type === 'line' ||
    type === 'textbox' ||
    type === 'map' ||
    type === 'image'
  ) {
    addObjects.value = [];
    return;
  }
  loadingAddObjects.value = true;
  try {
    addObjects.value = await connectionsApi.objects(props.backendId, type, auth.accessToken!);
  } catch {
    addObjects.value = [];
  } finally {
    loadingAddObjects.value = false;
  }
}

async function fetchAddServices(host: string) {
  if (!host || !props.backendId) {
    addServices.value = [];
    return;
  }
  loadingAddServices.value = true;
  try {
    addServices.value = await connectionsApi.objects(
      props.backendId,
      'service',
      auth.accessToken!,
      host,
    );
  } catch {
    addServices.value = [];
  } finally {
    loadingAddServices.value = false;
  }
}

function onTypeChange() {
  props.draft.host_name = '';
  props.draft.service_description = '';
  props.draft.group_name = '';
  props.draft.board_name = '';
  props.draft.label_text = '';
  props.draft.image_src = '';
  props.draft.graph_url = '';
  addObjects.value = [];
  addServices.value = [];
  if (props.draft.type === 'map') {
    if (boardsStore.boards.length === 0) boardsStore.fetchBoards();
    return;
  }
  const fetchType =
    props.draft.type === 'service' || props.draft.type === 'line' || props.draft.type === 'graph'
      ? 'host'
      : props.draft.type;
  fetchAddObjects(fetchType);
}

function onHostChange() {
  fetchAddServices(props.draft.host_name);
}

watch(
  () => props.draft.host_name,
  (host) => {
    if (props.draft.type === 'service' && host && addObjects.value.includes(host))
      fetchAddServices(host);
  },
);
</script>

<style scoped>
@reference "tailwindcss";

.field {
  @apply w-full bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-[var(--color-corporate-green-50)] transition-all duration-150;

  padding: 5px 10px;
}

/* Panel sits at the bottom of the viewport — force dropdowns to open upward */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(.cmk-suggestions) {
  bottom: 100%;
  top: auto;
}
</style>
