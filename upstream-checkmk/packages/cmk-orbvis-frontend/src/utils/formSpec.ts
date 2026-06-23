import type { VueFormspecComponents } from 'cmk-shared-typing/typescript/vue_formspec_components'

// The strict CMK FormSpec component union consumed by <FormEdit :spec>.
export type FormSpecSchema = NonNullable<VueFormspecComponents['components']>

/**
 * Bridge a FormSpec schema served by the backend (typed loosely as
 * `Record<string, unknown>` — the API can't statically prove the CMK
 * discriminated-union shape) to the precise `FormSpecSchema` the vendored CMK
 * `FormEdit` component requires. The runtime value is unchanged; this keeps the
 * unavoidable boundary cast in one documented place instead of scattering
 * `as unknown as Schema` across the FormSpec modals.
 */
export function asFormSpecSchema(raw: Record<string, unknown>): FormSpecSchema {
  return raw as unknown as FormSpecSchema
}
