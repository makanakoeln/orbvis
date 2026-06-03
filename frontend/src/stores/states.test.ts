import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/client', () => ({
    boardsApi: { getStates: vi.fn().mockResolvedValue({ states: [], connection_ok: true }) },
    connectionsApi: {},
}));

import { useStatesStore } from './states';

/** Minimal EventSource stand-in that lets the test drive open/error events. */
class FakeEventSource {
    static instances: FakeEventSource[] = [];
    static readonly OPEN = 1;
    onopen: (() => void) | null = null;
    onmessage: ((e: MessageEvent) => void) | null = null;
    onerror: (() => void) | null = null;
    readyState = 0;
    closed = false;
    constructor(public url: string) {
        FakeEventSource.instances.push(this);
    }
    close() {
        this.closed = true;
        this.readyState = 2;
    }
}

describe('states store — SSE polling fallback + re-probe (T14)', () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        FakeEventSource.instances = [];
        vi.stubGlobal('EventSource', FakeEventSource);
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it('falls back to polling when the first SSE connect fails, then heals via re-probe', async () => {
        const store = useStatesStore();
        await store.connectToMap('board1', 'token');

        // _connect opened exactly one EventSource; nothing has failed yet.
        expect(FakeEventSource.instances).toHaveLength(1);
        expect(store.wsAvailable).toBe(true);

        // The connection errors before it ever opened → permanent-polling path.
        FakeEventSource.instances[0].onerror?.();
        expect(store.wsAvailable).toBe(false);
        expect(FakeEventSource.instances[0].closed).toBe(true);

        // After the re-probe interval, a probe EventSource is opened to test SSE.
        vi.advanceTimersByTime(60_000);
        expect(FakeEventSource.instances).toHaveLength(2);
        const probe = FakeEventSource.instances[1];

        // Probe opens → SSE is back: probe discarded, live stream re-established.
        probe.onopen?.();
        expect(probe.closed).toBe(true);
        expect(store.wsAvailable).toBe(true);
        expect(FakeEventSource.instances).toHaveLength(3);
    });

    it('keeps polling (and does not leak probes) while SSE stays unreachable', async () => {
        const store = useStatesStore();
        await store.connectToMap('board1', 'token');
        FakeEventSource.instances[0].onerror?.();
        expect(store.wsAvailable).toBe(false);

        // First re-probe fails before opening → discarded, still polling.
        vi.advanceTimersByTime(60_000);
        expect(FakeEventSource.instances).toHaveLength(2);
        FakeEventSource.instances[1].onerror?.();
        expect(FakeEventSource.instances[1].closed).toBe(true);
        expect(store.wsAvailable).toBe(false);

        // Next interval re-probes again (one probe per tick, no overlap leak).
        vi.advanceTimersByTime(60_000);
        expect(FakeEventSource.instances).toHaveLength(3);

        // Disconnect stops all timers — no further probes are created.
        store.disconnect();
        vi.advanceTimersByTime(120_000);
        expect(FakeEventSource.instances).toHaveLength(3);
    });

    it('drops an in-flight probe on disconnect — no stream promoted for the wrong board', async () => {
        const store = useStatesStore();
        await store.connectToMap('board1', 'token');
        FakeEventSource.instances[0].onerror?.(); // → polling
        vi.advanceTimersByTime(60_000); // → probe (instance[1])
        const probe = FakeEventSource.instances[1];
        expect(probe.onopen).toBeTypeOf('function');

        // Board switch / unmount while the probe is still connecting.
        store.disconnect();
        expect(probe.closed).toBe(true);
        expect(probe.onopen).toBeNull();

        // A late open must not promote a stream (no instance[2] appears).
        probe.onopen?.();
        expect(FakeEventSource.instances).toHaveLength(2);
    });
});

describe('states store — folder-tree delta apply', () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        FakeEventSource.instances = [];
        vi.stubGlobal('EventSource', FakeEventSource);
    });
    afterEach(() => {
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    const host = (path: string, state: string) => ({
        path,
        title: path.split('/').pop(),
        kind: 'host',
        state,
        is_empty: false,
        folder_id: '',
        host_count: 1,
        problem_count: state === 'UP' ? 0 : 1,
        severity_counts: {},
        output: '',
        acknowledged: false,
        in_downtime: false,
        is_flapping: false,
        last_state_change: null,
        site_id: null,
        children: [],
    });
    const folder = (children: ReturnType<typeof host>[], state = 'OK', problem = 0) => ({
        path: 'f',
        title: 'F',
        kind: 'folder',
        state,
        is_empty: false,
        folder_id: '',
        host_count: children.length,
        problem_count: problem,
        severity_counts: {},
        output: '',
        acknowledged: false,
        in_downtime: false,
        site_id: null,
        children,
    });
    const send = (es: FakeEventSource, folder_tree_delta: unknown) =>
        es.onmessage?.({
            data: JSON.stringify({
                type: 'state_update',
                map: 'b',
                full: false,
                states: {
                    map_name: 'b',
                    states: [],
                    generated_at: 1,
                    connection_ok: true,
                    folder_tree_delta,
                },
            }),
        } as MessageEvent);

    it('applies a full delta then patches changed nodes in place', async () => {
        const store = useStatesStore();
        await store.connectToMap('b', 't');
        const es = FakeEventSource.instances[0];
        es.onopen?.();

        send(es, {
            full: true,
            tree: folder([host('f/h1', 'UP'), host('f/h2', 'UP')]),
            changed: [],
        });
        expect(store.folderTree?.host_count).toBe(2);
        expect(store.folderTree?.state).toBe('OK');

        send(es, {
            full: false,
            changed: [
                { ...host('f/h1', 'DOWN'), problem_count: 1 },
                {
                    path: 'f',
                    title: 'Renamed',
                    state: 'CRITICAL',
                    is_empty: false,
                    host_count: 2,
                    problem_count: 1,
                    severity_counts: { DOWN: 1 },
                    output: '',
                    acknowledged: false,
                    in_downtime: false,
                    is_flapping: false,
                },
            ],
        });
        expect(store.folderTree?.children.find((c) => c.path === 'f/h1')?.state).toBe('DOWN');
        expect(store.folderTree?.state).toBe('CRITICAL');
        expect(store.folderTree?.title).toBe('Renamed'); // title patch applied (folder rename)
        expect(store.folderTree?.severity_counts).toEqual({ DOWN: 1 });
        expect(store.folderTree?.children.find((c) => c.path === 'f/h2')?.state).toBe('UP');
    });

    it('reorders children when a delta carries children_order', async () => {
        const store = useStatesStore();
        await store.connectToMap('b', 't');
        const es = FakeEventSource.instances[0];
        es.onopen?.();
        send(es, {
            full: true,
            tree: folder([host('f/h1', 'UP'), host('f/h2', 'UP')]),
            changed: [],
        });
        expect(store.folderTree?.children.map((c) => c.path)).toEqual(['f/h1', 'f/h2']);

        send(es, {
            full: false,
            changed: [
                {
                    path: 'f',
                    title: 'F',
                    state: 'CRITICAL',
                    is_empty: false,
                    host_count: 2,
                    problem_count: 1,
                    severity_counts: {},
                    output: '',
                    acknowledged: false,
                    in_downtime: false,
                    is_flapping: false,
                    children_order: ['f/h2', 'f/h1'],
                },
            ],
        });
        expect(store.folderTree?.children.map((c) => c.path)).toEqual(['f/h2', 'f/h1']);
    });
});
