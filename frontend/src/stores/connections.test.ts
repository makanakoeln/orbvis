import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { BackendConfig } from '@/types/api';

import { useConnectionsStore } from './connections';

const { mockConnectionsApi } = vi.hoisted(() => ({
  mockConnectionsApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('@/api/client', () => ({
  connectionsApi: mockConnectionsApi,
  authApi: {
    login: vi.fn(),
    sso: vi.fn().mockRejectedValue(new Error('no sso')),
    me: vi.fn(),
    refresh: vi.fn(),
    logout: vi.fn(),
  },
  boardsApi: { list: vi.fn(), get: vi.fn(), create: vi.fn(), delete: vi.fn() },
  settingsApi: { get: vi.fn(), update: vi.fn() },
}));

vi.mock('@/router', () => ({
  default: { push: vi.fn(), currentRoute: { value: { query: {} } } },
}));
vi.mock('@/i18n', () => ({ i18n: { global: { locale: { value: 'en' } } } }));

const sampleBackend: BackendConfig = {
  id: 'live_1',
  type: 'livestatus',
  label: 'Live 1',
  socket_path: '/tmp/live',
  port: 6557,
  timeout: 10,
  icinga2_verify_ssl: true,
};

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
});

describe('useConnectionsStore', () => {
  it('starts with empty backends', () => {
    const store = useConnectionsStore();
    expect(store.backends).toEqual([]);
  });

  it('fetchBackends() populates backends on success', async () => {
    mockConnectionsApi.list.mockResolvedValue([sampleBackend]);
    const store = useConnectionsStore();
    await store.fetchBackends();
    expect(store.backends).toEqual([sampleBackend]);
    expect(store.error).toBeNull();
  });

  it('fetchBackends() sets error on failure', async () => {
    mockConnectionsApi.list.mockRejectedValue(new Error('Failed'));
    const store = useConnectionsStore();
    await store.fetchBackends();
    expect(store.error).toBe('Failed');
  });

  it('createBackend() pushes to backends list', async () => {
    mockConnectionsApi.create.mockResolvedValue(sampleBackend);
    const store = useConnectionsStore();
    const result = await store.createBackend(sampleBackend);
    expect(store.backends).toHaveLength(1);
    expect(store.backends[0]).toEqual(sampleBackend);
    expect(result).toEqual(sampleBackend);
  });

  it('updateBackend() replaces the correct entry', async () => {
    const updated = { ...sampleBackend, label: 'Updated' };
    mockConnectionsApi.update.mockResolvedValue(updated);
    const store = useConnectionsStore();
    store.backends = [sampleBackend];
    await store.updateBackend('live_1', {
      label: 'Updated',
      type: 'livestatus',
      port: 6557,
      timeout: 10,
      icinga2_verify_ssl: true,
    });
    expect(store.backends[0].label).toBe('Updated');
  });

  it('deleteBackend() removes the entry', async () => {
    mockConnectionsApi.delete.mockResolvedValue(undefined);
    const store = useConnectionsStore();
    store.backends = [sampleBackend];
    await store.deleteBackend('live_1');
    expect(store.backends).toHaveLength(0);
  });
});
