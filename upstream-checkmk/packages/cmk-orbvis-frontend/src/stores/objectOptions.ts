/**
 * Object-option registry — backend is the single source of truth for the
 * names of line styles (and, later, map types / gadget kinds / etc.).
 *
 * Loaded once after login and exposed as a plain reactive cache the
 * synchronous dropdown helpers in ``utils/dropdownOptions.ts`` can read
 * without awaiting anything. Display titles come from the frontend's
 * i18n catalogue keyed by the backend-supplied ``name`` — that way the
 * registry stays language-neutral and we don't need a separate
 * translation handshake.
 *
 * If the fetch hasn't completed yet (rare, only the first paint right
 * after login), the helpers fall back to a small hard-coded list so the
 * UI never shows an empty dropdown. The fallback intentionally only
 * includes the historical defaults — anything the backend adds later
 * is invisible until the registry loads.
 */
import { defineStore } from 'pinia'

import { type ObjectOption, objectOptionsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

interface State {
  lineStyles: ObjectOption[]
  loaded: boolean
}

export const useObjectOptionsStore = defineStore('objectOptions', {
  state: (): State => ({
    lineStyles: [],
    loaded: false
  }),
  actions: {
    async ensureLoaded(): Promise<void> {
      if (this.loaded) return
      const auth = useAuthStore()
      if (!auth.accessToken) return
      try {
        const data = await objectOptionsApi.get(auth.accessToken)
        this.lineStyles = data.line_styles
        this.loaded = true
      } catch {
        // Swallow — synchronous dropdown helpers will use the
        // hard-coded fallback. The error already surfaces in
        // the network panel and devtools if anyone needs it.
      }
    }
  }
})
