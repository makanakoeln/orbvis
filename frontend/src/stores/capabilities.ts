/**
 * Backend capability flags consumed at SPA bootstrap.
 *
 * The Standalone (Docker) distribution ships without ``cmk.rulesets.v1`` —
 * the FormSpec admin endpoints are then absent and the views fall back to
 * the legacy plain-Vue forms over flat pydantic CRUD. Built-in / MKP keep
 * the FormSpec experience.
 *
 * Unauthenticated by design — the flags are public so the Login screen
 * itself can branch on them if needed. Fallback: assume FormSpec is
 * available (matches MKP/built-in, the bulk of deployments).
 */
import { defineStore } from 'pinia';

import { capabilitiesApi } from '@/api/client';

interface State {
    formSpecs: boolean;
    loaded: boolean;
}

export const useCapabilitiesStore = defineStore('capabilities', {
    state: (): State => ({
        formSpecs: true,
        loaded: false,
    }),
    actions: {
        async ensureLoaded(): Promise<void> {
            if (this.loaded) return;
            try {
                const data = await capabilitiesApi.get();
                this.formSpecs = data.form_specs;
                this.loaded = true;
            } catch {
                // Best-effort — keep the optimistic default so the MKP/
                // built-in admin UI still works if the endpoint blips.
            }
        },
    },
});
