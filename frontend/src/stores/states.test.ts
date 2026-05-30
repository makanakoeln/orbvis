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
