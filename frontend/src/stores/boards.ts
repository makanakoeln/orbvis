import { defineStore } from 'pinia';
import { ref } from 'vue';

import { boardsApi } from '@/api/client';
import type { BoardConfig, BoardRead } from '@/types/api';

import { useAuthStore } from './auth';

export const useBoardsStore = defineStore('boards', () => {
    const boards = ref<BoardRead[]>([]);
    const currentBoard = ref<BoardConfig | null>(null);
    const loading = ref(false);
    const error = ref<string | null>(null);

    function token(): string {
        return useAuthStore().accessToken ?? '';
    }

    async function fetchBoards() {
        loading.value = true;
        error.value = null;
        try {
            boards.value = await boardsApi.list(token());
        } catch (e: unknown) {
            error.value = e instanceof Error ? e.message : 'Failed to load boards';
        } finally {
            loading.value = false;
        }
    }

    async function fetchBoard(name: string) {
        loading.value = true;
        error.value = null;
        currentBoard.value = null; // clear stale data immediately
        try {
            const cfg = await boardsApi.get(name, token());
            // Worldmap boards with auto_source merge transient hosts on top of
            // the persisted set. The merge happens here (not in the editor)
            // so the canvas, drawer and websocket flow all see one object list.
            const wv = cfg.view?.type === 'worldmap' ? cfg.view : null;
            if (wv?.auto_source) {
                try {
                    const auto = await boardsApi.autoObjects(name, token());
                    cfg.objects = [...cfg.objects, ...auto];
                } catch {
                    // Auto-source failures shouldn't block the persisted view.
                }
            }
            currentBoard.value = cfg;
        } catch (e: unknown) {
            error.value = e instanceof Error ? e.message : 'Failed to load board';
        } finally {
            loading.value = false;
        }
    }

    async function createBoard(
        name: string,
        alias: string,
        connectionId = 'live_1',
        boardType = 'static',
        iconSize?: number | null,
    ) {
        const cfg = await boardsApi.create(
            {
                name,
                alias,
                connection_id: connectionId,
                icon_size: iconSize,
                view: { type: boardType },
            },
            token(),
        );
        // In-place append instead of a full re-fetch. BoardRead is a projection of
        // BoardConfig, so we build the list-shape from the returned config.
        boards.value.push({
            name: cfg.name,
            alias: cfg.alias,
            background_image: cfg.background_image ?? null,
            icon_size: cfg.icon_size,
            connection_id: cfg.connection_id,
            view_type: cfg.view?.type ?? 'static',
            view: cfg.view,
            object_count: cfg.objects?.length ?? 0,
            rotation_interval: cfg.rotation_interval,
            sort_order: cfg.sort_order,
            click_action: cfg.click_action,
            readonly: cfg.readonly ?? false,
            show_in_lists: true, // BoardConfig does not carry this; list endpoint defaults it
            hover_template: cfg.hover_template ?? null,
            context_template: cfg.context_template ?? null,
        });
        return cfg;
    }

    async function deleteBoard(name: string) {
        await boardsApi.delete(name, token());
        boards.value = boards.value.filter((b) => b.name !== name);
    }

    return {
        boards,
        currentBoard,
        loading,
        error,
        fetchBoards,
        fetchBoard,
        createBoard,
        deleteBoard,
    };
});
