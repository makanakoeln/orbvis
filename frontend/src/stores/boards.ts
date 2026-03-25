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
      currentBoard.value = await boardsApi.get(name, token());
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load board';
    } finally {
      loading.value = false;
    }
  }

  async function createBoard(
    name: string,
    alias: string,
    backendId = 'live_1',
    boardType = 'static',
    iconSize?: number,
  ) {
    const cfg = await boardsApi.create(
      { name, alias, backend_id: backendId, icon_size: iconSize, view: { type: boardType } },
      token(),
    );
    await fetchBoards();
    return cfg;
  }

  async function deleteBoard(name: string) {
    await boardsApi.delete(name, token());
    await fetchBoards();
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
