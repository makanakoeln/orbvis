import type { FolderTreeNode } from '@/types/api';
import {
    type FilterField,
    type FilterTerm,
    matchesFilterTerms,
    parseFilterTerms,
} from '@/utils/objectFilter';

export type { FilterTerm };

const PROBLEM_STATES = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN']);

export function isProblemState(state: string): boolean {
    return PROBLEM_STATES.has(state);
}

// The foldertree only ever holds hosts and services, so only the `h:`/`s:`
// operators (and bare text) are meaningful here — hg:/sg:/id: are dropped,
// mirroring how FlowBoard filters out the fields its objects can't carry. The
// BoardSearch UI already hides those operators via `:exclude-prefixes`.
const FT_FIELDS = new Set<FilterField>(['host', 'service', 'any']);

/** Parse the BoardSearch string with the shared quicksearch grammar, keeping
 *  only the host/service-scoped (and bare) terms. */
export function parseFolderQuery(raw: string): FilterTerm[] {
    return parseFilterTerms(raw).filter((t) => FT_FIELDS.has(t.field));
}

/** Whether the parsed query + problems-only toggle actually constrain anything. */
export function isFilterActive(terms: FilterTerm[], problemsOnly: boolean): boolean {
    return problemsOnly || terms.length > 0;
}

const hasServiceTerm = (terms: FilterTerm[]): boolean => terms.some((t) => t.field === 'service');

// Host/any terms must all match the host name; service-scoped terms don't decide
// which hosts show — they constrain a host's service leaves (filtered separately).
function hostNameMatches(hostName: string, terms: FilterTerm[]): boolean {
    const n = hostName.toLowerCase();
    return terms.every((t) => t.field === 'service' || n.includes(t.needle));
}

// Whether a host shows under the active query. With a service-scoped term the
// answer is authoritative from the server's `matchedHosts` (host terms applied
// there too): a host without a matching service drops out, so a `s:` query
// narrows to hosts that actually run it instead of listing the whole site to
// drill into one by one. Without a service term it's the instant client-side
// host-name match, plus any server service-hit for bare terms.
function hostVisible(hostName: string, terms: FilterTerm[], matchedHosts?: Set<string>): boolean {
    if (hasServiceTerm(terms)) return matchedHosts?.has(hostName) ?? false;
    return hostNameMatches(hostName, terms) || (matchedHosts?.has(hostName) ?? false);
}

// A service leaf matches when every term is satisfied — host terms against its
// host name, service terms against its description, bare terms against either.
// Reuses the shared quicksearch matcher (one place for the AND/substring rules);
// the host name is supplied by the caller because service leaves don't carry it.
export function serviceMatches(
    hostName: string,
    serviceName: string,
    terms: FilterTerm[],
): boolean {
    return matchesFilterTerms(terms, (field) =>
        field === 'host'
            ? [hostName]
            : field === 'service'
              ? [serviceName]
              : [hostName, serviceName],
    );
}

// A folder's own name only counts as a hit for unscoped queries (no h:/s:): then
// every bare term must match the folder name (searching "Datacenters" reveals its
// whole subtree). A scoped query never matches on a folder name.
function folderNameMatches(folderName: string, terms: FilterTerm[]): boolean {
    if (terms.length === 0) return false;
    const n = folderName.toLowerCase();
    return terms.every((t) => t.field === 'any' && n.includes(t.needle));
}

/** Whether a node is itself a full query hit, so its whole subtree counts as
 *  matching (propagated down via the `ancestorMatched` flag). A host is a full
 *  hit only for host/bare queries — a service-scoped term must be checked against
 *  the actual service leaves, so it does not blanket-reveal a host's services. */
export function selfMatches(node: FolderTreeNode, terms: FilterTerm[]): boolean {
    if (node.kind === 'folder') return folderNameMatches(node.title, terms);
    if (node.kind === 'host') return !hasServiceTerm(terms) && hostNameMatches(node.title, terms);
    return false;
}

/** Combined "Problems only" + search visibility for a foldertree subtree of
 *  store-tree nodes (folders and hosts). Service leaves are lazily loaded and
 *  live outside `children`, so the caller filters them with {@link serviceVisible}
 *  using the owning host's name. `ancestorMatched` is set once a containing
 *  folder/host already matched, so its whole subtree counts as matching. */
export function subtreeVisible(
    node: FolderTreeNode,
    terms: FilterTerm[],
    problemsOnly: boolean,
    ancestorMatched = false,
    // Hosts that matched a server-side service search (see folderSearch). They
    // count as visible even when their own name doesn't match, so a `s:` query
    // surfaces the host to drill into — mirroring the Map's pruneTree svcMatch
    // branch, which the List/summary path can't derive on its own.
    matchedHosts?: Set<string>,
): boolean {
    if (node.kind === 'host') {
        const matched = ancestorMatched || hostVisible(node.title, terms, matchedHosts);
        return matched && (!problemsOnly || isProblemState(node.state));
    }
    if (node.kind === 'service') {
        // Reached only when a service leaf has no host context; match its
        // description against the non-host terms as a best effort.
        const matched = ancestorMatched || serviceMatches('', node.title, terms);
        return matched && (!problemsOnly || isProblemState(node.state));
    }
    const selfMatch = ancestorMatched || folderNameMatches(node.title, terms);
    if (node.children.some((c) => subtreeVisible(c, terms, problemsOnly, selfMatch, matchedHosts)))
        return true;
    return selfMatch && !problemsOnly && node.children.length === 0;
}

/** Visibility of a single lazily-loaded service leaf under `hostName`, combining
 *  the search terms (with host context) and the problems-only toggle. */
export function serviceVisible(
    hostName: string,
    node: FolderTreeNode,
    terms: FilterTerm[],
    problemsOnly: boolean,
    ancestorMatched = false,
): boolean {
    const matched = ancestorMatched || serviceMatches(hostName, node.title, terms);
    return matched && (!problemsOnly || isProblemState(node.state));
}
