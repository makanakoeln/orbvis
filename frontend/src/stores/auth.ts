import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import type { RouteLocationRaw } from 'vue-router';

import { authApi } from '@/api/client';
import { i18n } from '@/i18n';
import router from '@/router';
import { useSettingsStore } from '@/stores/settings';
import type { UserRead } from '@/types/api';

const ACCESS_TOKEN_KEY = 'orbvis_access_token';
const REFRESH_TOKEN_KEY = 'orbvis_refresh_token';
const SSO_ACTIVE_KEY = 'orbvis_sso';

// Derive Checkmk logout URL from current path: /heute/orbvis/... → /heute/check_mk/logout.py
function _checkmkLogoutUrl(): string | null {
    const m = window.location.pathname.match(/^(\/[^/]+)\/orbvis/);
    return m ? `${m[1]}/check_mk/logout.py` : null;
}

export const useAuthStore = defineStore('auth', () => {
    const accessToken = ref<string | null>(null);
    const refreshToken = ref<string | null>(null);
    const user = ref<UserRead | null>(null);
    const loading = ref(false);
    const error = ref<string | null>(null);
    // true when logged in via Checkmk SSO
    const ssoActive = ref(false);

    // true when OrbVis is served inside a Checkmk/OMD installation (path: /{site}/orbvis/…)
    // Used to suppress the OrbVis sidebar even when SSO is temporarily unavailable.
    const isCheckmkDeployment = computed(() => /^\/[^/]+\/orbvis/.test(window.location.pathname));

    const isAuthenticated = computed(() => !!accessToken.value && !!user.value);
    const isAdmin = computed(() => user.value?.is_admin ?? false);

    // Ensures initialization runs exactly once per SPA session and is awaitable
    let _initPromise: Promise<void> | null = null;

    function init(): Promise<void> {
        if (!_initPromise) {
            _initPromise = _doInit();
        }
        return _initPromise;
    }

    async function _doInit(): Promise<void> {
        // Try Checkmk SSO via session cookie (auth_<site>); only works when served through OMD Apache.
        // Retry once on network errors (server may still be starting up), but not on HTTP 401.
        let ssoTokens = null;
        for (let attempt = 0; attempt < 2; attempt++) {
            try {
                ssoTokens = await authApi.sso();
                break;
            } catch (e: unknown) {
                if (e instanceof TypeError && attempt === 0) {
                    // Network-level failure (server not ready yet) — wait briefly and retry
                    await new Promise((r) => setTimeout(r, 600));
                } else {
                    console.warn('[OrbVis] SSO failed:', e);
                    break; // HTTP 401 or second failure: SSO not available
                }
            }
        }
        if (ssoTokens) {
            accessToken.value = ssoTokens.access_token;
            refreshToken.value = ssoTokens.refresh_token;
            sessionStorage.setItem(ACCESS_TOKEN_KEY, ssoTokens.access_token);
            sessionStorage.setItem(REFRESH_TOKEN_KEY, ssoTokens.refresh_token);
            sessionStorage.setItem(SSO_ACTIVE_KEY, '1');
            ssoActive.value = true;
            await fetchCurrentUser();
            return;
        }

        ssoActive.value = false;
        sessionStorage.removeItem(SSO_ACTIVE_KEY);
        accessToken.value = sessionStorage.getItem(ACCESS_TOKEN_KEY);
        refreshToken.value = sessionStorage.getItem(REFRESH_TOKEN_KEY);
        if (accessToken.value) {
            await fetchCurrentUser();
        } else if (refreshToken.value) {
            // No access token but refresh token present — silently renew
            const ok = await refreshAccessToken();
            if (ok) await fetchCurrentUser();
        }
    }

    async function fetchCurrentUser() {
        if (!accessToken.value) return;
        try {
            user.value = await authApi.me(accessToken.value);
            const lang =
                ssoActive.value && user.value.cmk_language
                    ? user.value.cmk_language
                    : (user.value.language ?? 'en');
            i18n.global.locale.value = lang as 'en' | 'de';
            // Load global settings so they're available for new map/object creation
            useSettingsStore()
                .load()
                .catch((e) => console.warn('[OrbVis] Failed to load settings:', e));
        } catch {
            // Access token may be expired — try refresh before giving up
            if (refreshToken.value) {
                const ok = await refreshAccessToken();
                if (ok && accessToken.value) {
                    try {
                        user.value = await authApi.me(accessToken.value);
                        const lang2 =
                            ssoActive.value && user.value.cmk_language
                                ? user.value.cmk_language
                                : (user.value.language ?? 'en');
                        i18n.global.locale.value = lang2 as 'en' | 'de';
                        useSettingsStore()
                            .load()
                            .catch((e) => console.warn('[OrbVis] Failed to load settings:', e));
                        return;
                    } catch {
                        /* fall through to clearAuth */
                    }
                }
            }
            clearAuth();
        }
    }

    async function login(username: string, password: string) {
        loading.value = true;
        error.value = null;
        try {
            const tokens = await authApi.login(username, password);
            accessToken.value = tokens.access_token;
            refreshToken.value = tokens.refresh_token;
            sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
            sessionStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
            await fetchCurrentUser();
            const redirect = router.currentRoute.value.query.redirect as string | undefined;
            const target: RouteLocationRaw = redirect ? { path: redirect } : { name: 'home' };
            router.push(target);
        } catch (e: unknown) {
            error.value = e instanceof Error ? e.message : 'Login failed';
            throw e;
        } finally {
            loading.value = false;
        }
    }

    async function logout() {
        if (accessToken.value) {
            await authApi
                .logout(accessToken.value)
                .catch((e) => console.warn('[OrbVis] Logout failed:', e));
        }
        clearAuth();
        if (ssoActive.value) {
            // In Checkmk SSO mode, log out of Checkmk itself
            const url = _checkmkLogoutUrl();
            if (url) {
                window.location.href = url;
                return;
            }
        }
        router.push('/login');
    }

    async function refreshAccessToken(): Promise<boolean> {
        if (!refreshToken.value) return false;
        try {
            const tokens = await authApi.refresh(refreshToken.value);
            accessToken.value = tokens.access_token;
            sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
            return true;
        } catch {
            clearAuth();
            return false;
        }
    }

    function clearAuth() {
        accessToken.value = null;
        refreshToken.value = null;
        user.value = null;
        ssoActive.value = false;
        _initPromise = null; // allow re-init after logout
        sessionStorage.removeItem(ACCESS_TOKEN_KEY);
        sessionStorage.removeItem(REFRESH_TOKEN_KEY);
        sessionStorage.removeItem(SSO_ACTIVE_KEY);
    }

    return {
        accessToken,
        refreshToken,
        user,
        loading,
        error,
        isAuthenticated,
        isAdmin,
        ssoActive,
        isCheckmkDeployment,
        init,
        login,
        logout,
        refreshAccessToken,
        fetchCurrentUser,
    };
});
