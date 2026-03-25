import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { SETTINGS_DEFAULTS, useSettingsStore } from './settings';

const { mockSettingsApi } = vi.hoisted(() => ({
  mockSettingsApi: { get: vi.fn(), update: vi.fn() },
}));

vi.mock('@/api/client', () => ({
  settingsApi: mockSettingsApi,
  authApi: {
    login: vi.fn(),
    sso: vi.fn().mockRejectedValue(new Error('no sso')),
    me: vi.fn(),
    refresh: vi.fn(),
    logout: vi.fn(),
  },
  boardsApi: { list: vi.fn(), get: vi.fn(), create: vi.fn(), delete: vi.fn() },
  connectionsApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/router', () => ({
  default: { push: vi.fn(), currentRoute: { value: { query: {} } } },
}));
vi.mock('@/i18n', () => ({ i18n: { global: { locale: { value: 'en' } } } }));

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
});

describe('useSettingsStore', () => {
  it('starts with default settings', () => {
    const store = useSettingsStore();
    expect(store.settings).toEqual(SETTINGS_DEFAULTS);
  });

  it('load() skips when no token', async () => {
    const store = useSettingsStore();
    await store.load();
    expect(mockSettingsApi.get).not.toHaveBeenCalled();
  });

  it('load() updates settings on success', async () => {
    const { useAuthStore } = await import('./auth');
    const auth = useAuthStore();
    auth.accessToken = 'test-token';

    const updated = { ...SETTINGS_DEFAULTS, icon_size: 64 };
    mockSettingsApi.get.mockResolvedValue(updated);

    const store = useSettingsStore();
    await store.load();
    expect(store.settings.icon_size).toBe(64);
  });

  it('load() falls back to defaults on API error', async () => {
    const { useAuthStore } = await import('./auth');
    const auth = useAuthStore();
    auth.accessToken = 'test-token';

    mockSettingsApi.get.mockRejectedValue(new Error('Network error'));

    const store = useSettingsStore();
    await store.load();
    expect(store.settings).toEqual(SETTINGS_DEFAULTS);
  });

  it('save() updates settings with API response', async () => {
    const { useAuthStore } = await import('./auth');
    const auth = useAuthStore();
    auth.accessToken = 'test-token';

    const newSettings = { ...SETTINGS_DEFAULTS, icon_size: 48 };
    mockSettingsApi.update.mockResolvedValue(newSettings);

    const store = useSettingsStore();
    await store.save(newSettings);
    expect(store.settings.icon_size).toBe(48);
    expect(mockSettingsApi.update).toHaveBeenCalledWith(newSettings, 'test-token');
  });
});
