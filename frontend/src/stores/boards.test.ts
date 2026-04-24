import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { BoardConfig, BoardRead } from '@/types/api';

import { useBoardsStore } from './boards';

const { mockBoardsApi } = vi.hoisted(() => ({
    mockBoardsApi: {
        list: vi.fn(),
        get: vi.fn(),
        create: vi.fn(),
        delete: vi.fn(),
    },
}));

vi.mock('@/api/client', () => ({
    boardsApi: mockBoardsApi,
    authApi: {
        login: vi.fn(),
        sso: vi.fn().mockRejectedValue(new Error('no sso')),
        me: vi.fn(),
        refresh: vi.fn(),
        logout: vi.fn(),
    },
    settingsApi: { get: vi.fn(), update: vi.fn() },
    connectionsApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/router', () => ({
    default: { push: vi.fn(), currentRoute: { value: { query: {} } } },
}));
vi.mock('@/i18n', () => ({ i18n: { global: { locale: { value: 'en' } } } }));

const sampleBoards: BoardRead[] = [
    {
        name: 'board1',
        alias: 'Board 1',
        background_image: null,
        icon_size: 30,
        backend_id: 'live_1',
        view_type: 'static',
        view: { type: 'static' },
        object_count: 0,
        rotation_interval: 0,
        sort_order: 0,
        click_action: 'link',
        readonly: false,
        show_in_lists: true,
        hover_template: null,
        context_template: null,
    },
];

const sampleConfig: BoardConfig = {
    name: 'board1',
    alias: 'Board 1',
    icon_size: 30,
    backend_id: 'live_1',
    rotation_interval: 0,
    sort_order: 0,
    click_action: 'link',
    view: { type: 'static' },
    objects: [],
};

beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
});

describe('useBoardsStore', () => {
    it('starts with empty boards', () => {
        const store = useBoardsStore();
        expect(store.boards).toEqual([]);
        expect(store.loading).toBe(false);
        expect(store.error).toBeNull();
    });

    it('fetchBoards() populates boards on success', async () => {
        mockBoardsApi.list.mockResolvedValue(sampleBoards);
        const store = useBoardsStore();
        await store.fetchBoards();
        expect(store.boards).toEqual(sampleBoards);
        expect(store.loading).toBe(false);
        expect(store.error).toBeNull();
    });

    it('fetchBoards() sets error on failure', async () => {
        mockBoardsApi.list.mockRejectedValue(new Error('Network error'));
        const store = useBoardsStore();
        await store.fetchBoards();
        expect(store.error).toBe('Network error');
        expect(store.loading).toBe(false);
        expect(store.boards).toEqual([]);
    });

    it('fetchBoard() clears currentBoard immediately', async () => {
        const store = useBoardsStore();
        store.currentBoard = sampleConfig;
        mockBoardsApi.get.mockResolvedValue(sampleConfig);

        const fetchPromise = store.fetchBoard('board1');
        expect(store.currentBoard).toBeNull();
        await fetchPromise;
        expect(store.currentBoard).toEqual(sampleConfig);
    });

    it('fetchBoard() sets error on failure', async () => {
        mockBoardsApi.get.mockRejectedValue(new Error('Not found'));
        const store = useBoardsStore();
        await store.fetchBoard('nonexistent');
        expect(store.error).toBe('Not found');
        expect(store.currentBoard).toBeNull();
    });

    it('createBoard() appends the new board in place without re-fetching', async () => {
        mockBoardsApi.create.mockResolvedValue(sampleConfig);
        const store = useBoardsStore();
        const result = await store.createBoard('board1', 'Board 1');
        expect(mockBoardsApi.create).toHaveBeenCalled();
        // In-place append: no extra list() round-trip.
        expect(mockBoardsApi.list).not.toHaveBeenCalled();
        expect(store.boards).toHaveLength(1);
        expect(store.boards[0].name).toBe('board1');
        expect(result).toEqual(sampleConfig);
    });

    it('deleteBoard() removes the board in place without re-fetching', async () => {
        mockBoardsApi.list.mockResolvedValue(sampleBoards);
        mockBoardsApi.delete.mockResolvedValue(undefined);
        const store = useBoardsStore();
        await store.fetchBoards();
        mockBoardsApi.list.mockClear();

        await store.deleteBoard('board1');
        expect(mockBoardsApi.delete).toHaveBeenCalledWith('board1', expect.any(String));
        // No extra list() round-trip — board is removed in place.
        expect(mockBoardsApi.list).not.toHaveBeenCalled();
        expect(store.boards).toEqual([]);
    });
});
