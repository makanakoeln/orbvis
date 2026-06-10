<template>
  <CmkSlideInDialog
    :open="open"
    :header="{ title: _t('Edit %{n} boards', { n: names.length }), closeButton: true }"
    size="small"
    @close="emit('cancel')"
  >
    <div class="bulk-edit__shell">
      <p class="bulk-edit__intro">
        {{
          _t(
            'Tick the fields you want to overwrite on every selected board. Unchecked fields stay untouched.',
            { n: names.length }
          )
        }}
      </p>
      <p v-if="previewAliases" class="bulk-edit__preview">
        {{ previewAliases }}
      </p>
      <div class="bulk-edit__body">
        <FormEdit
          v-if="formSchema"
          v-model:data="formSpecData"
          :spec="formSchema"
          :backend-validation="formBackendValidation"
        />
        <CmkLoading v-else-if="schemaLoading" />
        <p v-else class="bulk-edit__error">
          {{ _t('Could not load the bulk-edit form.') }}
        </p>
      </div>
      <div class="bulk-edit__footer">
        <CmkButton variant="secondary" :disabled="saving" @click="emit('cancel')">
          {{ _t('Cancel') }}
        </CmkButton>
        <CmkButton variant="primary" :disabled="saving || !hasActiveFields" @click="apply">
          {{ _t('Apply to %{n} boards', { n: names.length }) }}
        </CmkButton>
      </div>
    </div>
  </CmkSlideInDialog>
</template>

<script setup lang="ts">
import FormEdit from '@cmk/form/FormEdit.vue'
import { initializeComponentRegistry } from '@cmk/form/private/FormEditDispatcher/dispatch'
import type {
  ValidationMessage,
  VueFormspecComponents
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, onMounted, ref, watch } from 'vue'

import CmkButton from '@/components/cmk/CmkButton'
import CmkLoading from '@/components/cmk/CmkLoading'
import CmkSlideInDialog from '@/components/cmk/CmkSlideInDialog'

import { boardsApiFormSpec } from '@/api/client'
import { orbFormComponents } from '@/composables/orbFormComponents'
import { useAuthStore } from '@/stores/auth'
import { asFormSpecSchema } from '@/utils/formSpec'
import usei18n from '@/vendor/cmk/lib/i18n'

const props = defineProps<{
  open: boolean
  names: string[]
  aliases: string[]
  saving?: boolean
}>()

const emit = defineEmits<{
  cancel: []
  apply: [updates: Record<string, unknown>]
}>()

const { _t } = usei18n()
const auth = useAuthStore()

type Schema = NonNullable<VueFormspecComponents['components']>
initializeComponentRegistry(orbFormComponents)

const formSchema = ref<Schema | null>(null)
const schemaLoading = ref(true)
const formSpecData = ref<Record<string, unknown>>({})
const formBackendValidation = ref<ValidationMessage[]>([])

const previewAliases = computed(() => {
  if (props.aliases.length === 0) return ''
  const head = props.aliases.slice(0, 4).join(', ')
  const rest = props.aliases.length - 4
  return rest > 0 ? _t('%{head}, … and %{n} more', { head, n: rest }) : head
})

const hasActiveFields = computed(() => Object.keys(formSpecData.value).length > 0)

async function loadSchema() {
  schemaLoading.value = true
  try {
    const spec = await boardsApiFormSpec.getBulkMetadataSchema(auth.accessToken ?? '')
    formSchema.value = asFormSpecSchema(spec)
  } catch {
    formSchema.value = null
  } finally {
    schemaLoading.value = false
  }
}

function apply() {
  emit('apply', { ...formSpecData.value })
}

onMounted(loadSchema)

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) {
      formSpecData.value = {}
      formBackendValidation.value = []
    }
  }
)

defineExpose({
  setBackendValidation: (msgs: ValidationMessage[]) => {
    formBackendValidation.value = msgs
  }
})
</script>

<style scoped>
.bulk-edit__shell {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  padding: var(--dimension-5);
  min-width: 480px;
  max-width: 640px;
}

.bulk-edit__intro {
  color: var(--text);
  font-size: var(--font-size-large);
}

.bulk-edit__preview {
  color: var(--text-muted);
  font-size: 0.9em;
  font-style: italic;
}

.bulk-edit__body {
  flex: 1;
  min-height: 200px;
}

.bulk-edit__error {
  color: var(--color-light-red-40);
}

.bulk-edit__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--dimension-3);
  padding-top: var(--dimension-4);
  border-top: 1px solid var(--border);
  margin-top: var(--dimension-4);
}
</style>
