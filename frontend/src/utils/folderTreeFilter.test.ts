import { describe, expect, it } from 'vitest';

import type { FolderTreeNode } from '@/types/api';

import {
    parseFolderQuery,
    selfMatches,
    serviceMatches,
    serviceVisible,
    subtreeVisible,
} from './folderTreeFilter';

function folder(title: string, children: FolderTreeNode[] = []): FolderTreeNode {
    return {
        path: title,
        title,
        kind: 'folder',
        state: 'OK',
        is_empty: children.length === 0,
        folder_id: title,
        host_count: 0,
        problem_count: 0,
        severity_counts: {},
        output: '',
        acknowledged: false,
        in_downtime: false,
        site_id: null,
        children,
    } as FolderTreeNode;
}

function host(title: string, state = 'UP'): FolderTreeNode {
    return { ...folder(title), kind: 'host', state, is_empty: false } as FolderTreeNode;
}

function service(title: string, state = 'OK'): FolderTreeNode {
    return { ...folder(title), kind: 'service', state, is_empty: false } as FolderTreeNode;
}

describe('parseFolderQuery', () => {
    it('keeps only host/service/bare terms (drops hg/sg/id)', () => {
        expect(parseFolderQuery('h:web s:cpu')).toEqual([
            { field: 'host', needle: 'web' },
            { field: 'service', needle: 'cpu' },
        ]);
        expect(parseFolderQuery('hg:linux sg:db id:foo')).toEqual([]);
        expect(parseFolderQuery('h:web hg:linux')).toEqual([{ field: 'host', needle: 'web' }]);
    });

    it('treats bare text as an "any" term', () => {
        expect(parseFolderQuery('datacenter')).toEqual([{ field: 'any', needle: 'datacenter' }]);
    });

    it('tolerates whitespace after the operator (CMK parity)', () => {
        expect(parseFolderQuery('h: web')).toEqual([{ field: 'host', needle: 'web' }]);
    });
});

describe('serviceMatches', () => {
    it('matches host terms against the host name, service terms against the service', () => {
        expect(serviceMatches('web-01', 'CPU load', parseFolderQuery('h:web'))).toBe(true);
        expect(serviceMatches('web-01', 'CPU load', parseFolderQuery('s:cpu'))).toBe(true);
        expect(serviceMatches('web-01', 'CPU load', parseFolderQuery('s:disk'))).toBe(false);
    });

    it('AND-combines host + service terms', () => {
        const q = parseFolderQuery('h:web s:cpu');
        expect(serviceMatches('web-01', 'CPU load', q)).toBe(true);
        expect(serviceMatches('db-01', 'CPU load', q)).toBe(false);
        expect(serviceMatches('web-01', 'Disk /', q)).toBe(false);
    });

    it('matches a bare term against either host or service', () => {
        const q = parseFolderQuery('web');
        expect(serviceMatches('web-01', 'CPU', q)).toBe(true);
        expect(serviceMatches('db-01', 'web check', q)).toBe(true);
        expect(serviceMatches('db-01', 'CPU', q)).toBe(false);
    });
});

describe('selfMatches', () => {
    it('reveals a whole host only for host/bare queries (no service term)', () => {
        expect(selfMatches(host('web-01'), parseFolderQuery('h:web'))).toBe(true);
        expect(selfMatches(host('web-01'), parseFolderQuery('web'))).toBe(true);
        // A service-scoped term must be checked against the leaves, so the host
        // is not a blanket hit.
        expect(selfMatches(host('web-01'), parseFolderQuery('h:web s:cpu'))).toBe(false);
        expect(selfMatches(host('web-01'), parseFolderQuery('s:cpu'))).toBe(false);
    });

    it('matches a folder name only for unscoped queries', () => {
        expect(selfMatches(folder('Datacenters'), parseFolderQuery('datacenter'))).toBe(true);
        expect(selfMatches(folder('Datacenters'), parseFolderQuery('h:data'))).toBe(false);
    });
});

describe('subtreeVisible', () => {
    it('shows hosts matching host/bare terms', () => {
        expect(subtreeVisible(host('web-01'), parseFolderQuery('h:web'), false)).toBe(true);
        expect(subtreeVisible(host('db-01'), parseFolderQuery('h:web'), false)).toBe(false);
    });

    it('keeps every host drillable for a pure service query', () => {
        expect(subtreeVisible(host('db-01'), parseFolderQuery('s:cpu'), false)).toBe(true);
    });

    it('filters hosts by name even when a service term is present', () => {
        const q = parseFolderQuery('h:web s:cpu');
        expect(subtreeVisible(host('web-01'), q, false)).toBe(true);
        expect(subtreeVisible(host('db-01'), q, false)).toBe(false);
    });

    it('reveals a folder whose name matches an unscoped query', () => {
        const tree = folder('Datacenters', [host('node-1')]);
        expect(subtreeVisible(tree, parseFolderQuery('datacenter'), false)).toBe(true);
    });

    it('honours the problems-only toggle on hosts', () => {
        expect(subtreeVisible(host('web-01', 'UP'), [], true)).toBe(false);
        expect(subtreeVisible(host('web-01', 'DOWN'), [], true)).toBe(true);
    });
});

describe('serviceVisible', () => {
    it('filters lazily-loaded service leaves with their host in context', () => {
        const q = parseFolderQuery('h:web s:cpu');
        expect(serviceVisible('web-01', service('CPU load'), q, false)).toBe(true);
        expect(serviceVisible('web-01', service('Disk /'), q, false)).toBe(false);
    });

    it('shows all services once an ancestor (host self-match) matched', () => {
        expect(
            serviceVisible('web-01', service('Disk /'), parseFolderQuery('h:web'), false, true),
        ).toBe(true);
    });

    it('applies the problems-only toggle', () => {
        expect(serviceVisible('web-01', service('CPU', 'OK'), [], true)).toBe(false);
        expect(serviceVisible('web-01', service('CPU', 'CRITICAL'), [], true)).toBe(true);
    });
});
