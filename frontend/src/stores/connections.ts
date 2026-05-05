import { defineStore } from 'pinia';
import { ref } from 'vue';

import { connectionsApi } from '@/api/client';
import type { ConnectionConfig } from '@/types/api';

import { useAuthStore } from './auth';

export const useConnectionsStore = defineStore('connections', () => {
    const connections = ref<ConnectionConfig[]>([]);
    const loading = ref(false);
    const error = ref<string | null>(null);

    function token() {
        return useAuthStore().accessToken ?? '';
    }

    async function fetchConnections() {
        loading.value = true;
        error.value = null;
        try {
            connections.value = await connectionsApi.list(token());
        } catch (e: unknown) {
            error.value = e instanceof Error ? e.message : 'Failed to load connections';
        } finally {
            loading.value = false;
        }
    }

    async function createConnection(data: ConnectionConfig) {
        const b = await connectionsApi.create(data, token());
        connections.value.push(b);
        return b;
    }

    async function updateConnection(id: string, data: Omit<ConnectionConfig, 'id'>) {
        const b = await connectionsApi.update(id, data, token());
        const i = connections.value.findIndex((x) => x.id === id);
        if (i !== -1) connections.value[i] = b;
        return b;
    }

    async function deleteConnection(id: string) {
        await connectionsApi.delete(id, token());
        connections.value = connections.value.filter((x) => x.id !== id);
    }

    return {
        connections,
        loading,
        error,
        fetchConnections,
        createConnection,
        updateConnection,
        deleteConnection,
    };
});
