import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { ConnectionConfig } from '@/types/api';

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

const sampleBackend: ConnectionConfig = {
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
    it('starts with empty connections', () => {
        const store = useConnectionsStore();
        expect(store.connections).toEqual([]);
    });

    it('fetchConnections() populates connections on success', async () => {
        mockConnectionsApi.list.mockResolvedValue([sampleBackend]);
        const store = useConnectionsStore();
        await store.fetchConnections();
        expect(store.connections).toEqual([sampleBackend]);
        expect(store.error).toBeNull();
    });

    it('fetchConnections() sets error on failure', async () => {
        mockConnectionsApi.list.mockRejectedValue(new Error('Failed'));
        const store = useConnectionsStore();
        await store.fetchConnections();
        expect(store.error).toBe('Failed');
    });

    it('createConnection() pushes to connections list', async () => {
        mockConnectionsApi.create.mockResolvedValue(sampleBackend);
        const store = useConnectionsStore();
        const result = await store.createConnection(sampleBackend);
        expect(store.connections).toHaveLength(1);
        expect(store.connections[0]).toEqual(sampleBackend);
        expect(result).toEqual(sampleBackend);
    });

    it('updateConnection() replaces the correct entry', async () => {
        const updated = { ...sampleBackend, label: 'Updated' };
        mockConnectionsApi.update.mockResolvedValue(updated);
        const store = useConnectionsStore();
        store.connections = [sampleBackend];
        await store.updateConnection('live_1', {
            label: 'Updated',
            type: 'livestatus',
            port: 6557,
            timeout: 10,
            icinga2_verify_ssl: true,
        });
        expect(store.connections[0].label).toBe('Updated');
    });

    it('deleteConnection() removes the entry', async () => {
        mockConnectionsApi.delete.mockResolvedValue(undefined);
        const store = useConnectionsStore();
        store.connections = [sampleBackend];
        await store.deleteConnection('live_1');
        expect(store.connections).toHaveLength(0);
    });
});
