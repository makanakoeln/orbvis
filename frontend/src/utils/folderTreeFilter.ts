import type { FolderTreeNode } from '@/types/api';

const PROBLEM_STATES = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN']);

export function isProblemState(state: string): boolean {
    return PROBLEM_STATES.has(state);
}

export interface ParsedQuery {
    field: 'any' | 'host' | 'service';
    text: string;
}

/** Parse the BoardSearch string, honouring the `h:` / `s:` scope operators. */
export function parseQuery(raw: string): ParsedQuery {
    const q = (raw ?? '').trim().toLowerCase();
    if (q.startsWith('h:')) return { field: 'host', text: q.slice(2).trim() };
    if (q.startsWith('s:')) return { field: 'service', text: q.slice(2).trim() };
    return { field: 'any', text: q };
}

/** Whether the parsed query + problems-only toggle actually constrain anything. */
export function isFilterActive(q: ParsedQuery, problemsOnly: boolean): boolean {
    return problemsOnly || q.field !== 'any' || q.text !== '';
}

function leafMatches(node: FolderTreeNode, q: ParsedQuery): boolean {
    if (q.field === 'host' && node.kind !== 'host') return false;
    if (q.field === 'service' && node.kind !== 'service') return false;
    return !q.text || node.title.toLowerCase().includes(q.text);
}

// A folder's own name only counts as a hit for unscoped (`h:`/`s:`-free) queries.
function folderNameMatches(node: FolderTreeNode, q: ParsedQuery): boolean {
    return q.field === 'any' && q.text !== '' && node.title.toLowerCase().includes(q.text);
}

/** Whether a node (folder/host) is itself a query hit — used to propagate the
 *  "ancestor matched → show whole subtree" flag down the tree. */
export function selfMatches(node: FolderTreeNode, q: ParsedQuery): boolean {
    return node.kind === 'folder' ? folderNameMatches(node, q) : leafMatches(node, q);
}

/**
 * Combined "Problems only" + text-search visibility for a foldertree subtree.
 *
 * Shared by List and Map so both show the same set. `ancestorMatched` is set
 * once a containing folder/host already matched the query, so its whole subtree
 * counts as matching (searching "Datacenters" reveals its hosts). Folders
 * survive only when a descendant is visible (or, for an unscoped name hit, when
 * empty and no problems filter is active). A host's lazily-loaded services live
 * outside `children`, so a matching host is kept and the caller filters the
 * service leaves separately with the same predicate.
 */
export function subtreeVisible(
    node: FolderTreeNode,
    q: ParsedQuery,
    problemsOnly: boolean,
    ancestorMatched = false,
): boolean {
    if (node.kind !== 'folder') {
        const matched = ancestorMatched || leafMatches(node, q);
        return matched && (!problemsOnly || isProblemState(node.state));
    }
    const selfMatch = ancestorMatched || folderNameMatches(node, q);
    if (node.children.some((c) => subtreeVisible(c, q, problemsOnly, selfMatch))) return true;
    return selfMatch && !problemsOnly && node.children.length === 0;
}
