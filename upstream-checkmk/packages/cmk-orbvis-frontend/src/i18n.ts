import usei18n from '@cmk/lib/i18n'

// Signature of the `_t` translate function in setup context — used by helper
// modules that receive the translator as a parameter (gettext extraction only
// sees literal `_t('…')` callsites, so helpers must be called with `_t` from
// a component rather than translating dynamic keys themselves).
export type TranslateFn = (msg: string, interpolation?: Record<string, string | number>) => string

export async function setLanguage(lang: string): Promise<void> {
  const { switchLanguage } = usei18n()
  await switchLanguage(lang)
}
