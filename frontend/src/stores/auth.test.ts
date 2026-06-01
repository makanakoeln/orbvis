import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { TokenResponse, UserRead } from '@/types/api';

const { mockPush, mockAuthApi } = vi.hoisted(() => ({
    mockPush: vi.fn(),
    mockAuthApi: {
        login: vi.fn(),
        logout: vi.fn(),
        refresh: vi.fn(),
        me: vi.fn(),
        sso: vi.fn().mockRejectedValue(new Error('no sso')),
    },
}));

vi.mock('@/api/client', () => ({
    authApi: mockAuthApi,
    settingsApi: { get: vi.fn().mockResolvedValue({}), update: vi.fn() },
    boardsApi: { list: vi.fn(), get: vi.fn(), create: vi.fn(), delete: vi.fn() },
    connectionsApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/router', () => ({
    default: {
        push: mockPush,
        currentRoute: { value: { query: {} } },
    },
}));

vi.mock('@/i18n', () => ({
    i18n: { global: { locale: { value: 'en' } } },
}));

const sampleUser: UserRead = {
    user_id: 1,
    name: 'testuser',
    is_active: true,
    is_admin: false,
    must_change_password: false,
    theme: 'system',
    language: 'en',
    cmk_theme: null,
    cmk_language: null,
    cmk_inline_help: false,
    can_configure: false,
    can_create_boards: false,
    roles: [],
    permissions: [],
};

const adminUser: UserRead = { ...sampleUser, is_admin: true };

const sampleTokens: TokenResponse = {
    access_token: 'access-abc',
    refresh_token: 'refresh-xyz',
    token_type: 'bearer',
};

beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    sessionStorage.clear();
    mockAuthApi.sso.mockRejectedValue(new Error('no sso'));
});

describe('useAuthStore', () => {
    it('starts unauthenticated', async () => {
        const { useAuthStore } = await import('./auth');
        const store = useAuthStore();
        expect(store.isAuthenticated).toBe(false);
        expect(store.accessToken).toBeNull();
        expect(store.user).toBeNull();
    });

    it('isAuthenticated is false when only token set', async () => {
        const { useAuthStore } = await import('./auth');
        const store = useAuthStore();
        store.accessToken = 'token';
        expect(store.isAuthenticated).toBe(false);
    });

    it('isAuthenticated is true when token and user set', async () => {
        const { useAuthStore } = await import('./auth');
        const store = useAuthStore();
        store.accessToken = 'token';
        store.user = sampleUser;
        expect(store.isAuthenticated).toBe(true);
    });

    it('isAdmin reflects user.is_admin', async () => {
        const { useAuthStore } = await import('./auth');
        const store = useAuthStore();
        store.user = sampleUser;
        expect(store.isAdmin).toBe(false);
        store.user = adminUser;
        expect(store.isAdmin).toBe(true);
    });

    it('canConfigure / canCreateBoards reflect the capability flags', async () => {
        const { useAuthStore } = await import('./auth');
        const store = useAuthStore();
        store.user = sampleUser;
        expect(store.canConfigure).toBe(false);
        expect(store.canCreateBoards).toBe(false);
        store.user = { ...sampleUser, can_configure: true, can_create_boards: true };
        expect(store.canConfigure).toBe(true);
        expect(store.canCreateBoards).toBe(true);
    });

    it('canConfigure / canCreateBoards fall back to is_admin for older backends', async () => {
        const { useAuthStore } = await import('./auth');
        const store = useAuthStore();
        // Simulate a /me payload from a backend that predates the capability flags.
        const legacyAdmin = { ...adminUser } as Partial<UserRead>;
        delete legacyAdmin.can_configure;
        delete legacyAdmin.can_create_boards;
        store.user = legacyAdmin as UserRead;
        expect(store.canConfigure).toBe(true);
        expect(store.canCreateBoards).toBe(true);
    });

    it('login() sets tokens and navigates home on success', async () => {
        const { useAuthStore } = await import('./auth');
        mockAuthApi.login.mockResolvedValue(sampleTokens);
        mockAuthApi.me.mockResolvedValue(sampleUser);

        const store = useAuthStore();
        await store.login('testuser', 'password');

        expect(store.accessToken).toBe('access-abc');
        expect(store.user).toEqual(sampleUser);
        expect(mockPush).toHaveBeenCalledWith({ name: 'home' });
    });

    it('login() sets error and rethrows on failure', async () => {
        const { useAuthStore } = await import('./auth');
        mockAuthApi.login.mockRejectedValue(new Error('Invalid credentials'));

        const store = useAuthStore();
        await expect(store.login('bad', 'bad')).rejects.toThrow('Invalid credentials');
        expect(store.error).toBe('Invalid credentials');
        expect(store.loading).toBe(false);
    });

    it('logout() clears auth state and navigates to login', async () => {
        const { useAuthStore } = await import('./auth');
        mockAuthApi.logout.mockResolvedValue(undefined);

        const store = useAuthStore();
        store.accessToken = 'token';
        store.user = sampleUser;
        sessionStorage.setItem('orbvis_access_token', 'token');

        await store.logout();

        expect(store.accessToken).toBeNull();
        expect(store.user).toBeNull();
        expect(sessionStorage.getItem('orbvis_access_token')).toBeNull();
        expect(mockPush).toHaveBeenCalledWith('/login');
    });

    it('refreshAccessToken() updates token on success', async () => {
        const { useAuthStore } = await import('./auth');
        mockAuthApi.refresh.mockResolvedValue({
            access_token: 'new-access',
            refresh_token: 'refresh-xyz',
        });

        const store = useAuthStore();
        store.refreshToken = 'refresh-xyz';

        const ok = await store.refreshAccessToken();
        expect(ok).toBe(true);
        expect(store.accessToken).toBe('new-access');
    });

    it('refreshAccessToken() returns false when no refresh token', async () => {
        const { useAuthStore } = await import('./auth');
        const store = useAuthStore();
        const ok = await store.refreshAccessToken();
        expect(ok).toBe(false);
    });

    it('refreshAccessToken() clears auth and returns false on error', async () => {
        const { useAuthStore } = await import('./auth');
        mockAuthApi.refresh.mockRejectedValue(new Error('Token expired'));

        const store = useAuthStore();
        store.refreshToken = 'expired-refresh';
        store.accessToken = 'old-access';
        store.user = sampleUser;

        const ok = await store.refreshAccessToken();
        expect(ok).toBe(false);
        expect(store.accessToken).toBeNull();
        expect(store.user).toBeNull();
    });
});
