/**
 * Shared FormSpec-schema loader for OrbVis surfaces.
 *
 * Three views (Settings, Connections, Board-Settings) used to duplicate the
 * same load+cache+initialise-registry boilerplate. This composable owns:
 *   - lazy ``initializeComponentRegistry()`` (only once per page lifetime)
 *   - module-scope cache so a re-mount doesn't re-fetch the same schema
 *   - typed ref shape so the caller can ``v-if="schema"`` the FormEdit
 */
import { initializeComponentRegistry } from '@cmk/form/private/FormEditDispatcher/dispatch'
import type { VueFormspecComponents } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { type Ref, ref } from 'vue'

import { orbFormComponents } from '@/composables/orbFormComponents'

export type FormSpecSchema = NonNullable<VueFormspecComponents['components']>

const cache = new Map<string, FormSpecSchema>()
let registryInitialised = false

function ensureRegistry(): void {
  if (registryInitialised) return
  initializeComponentRegistry(orbFormComponents)
  registryInitialised = true
}

interface UseFormSpecSchemaResult {
  schema: Ref<FormSpecSchema | null>
  loading: Ref<boolean>
  error: Ref<string>
  load: () => Promise<FormSpecSchema | null>
}

/**
 * @param cacheKey  shared key — typically the schema endpoint path
 * @param fetcher   () => Promise<schema-json>; runs once per cacheKey
 */
export function useFormSpecSchema(
  cacheKey: string,
  fetcher: () => Promise<unknown>
): UseFormSpecSchemaResult {
  ensureRegistry()
  const schema = ref<FormSpecSchema | null>(cache.get(cacheKey) ?? null)
  const loading = ref(false)
  const error = ref('')

  async function load(): Promise<FormSpecSchema | null> {
    if (schema.value) return schema.value
    const cached = cache.get(cacheKey)
    if (cached) {
      schema.value = cached
      return cached
    }
    loading.value = true
    error.value = ''
    try {
      const spec = (await fetcher()) as FormSpecSchema
      cache.set(cacheKey, spec)
      schema.value = spec
      return spec
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Schema load failed'
      return null
    } finally {
      loading.value = false
    }
  }

  return { schema, loading, error, load }
}
