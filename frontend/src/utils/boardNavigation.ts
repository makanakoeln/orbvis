import type { BoardObject, ObjectState } from '@/types/api';

function _baseAndSite(
    checkmkUrl: string | null,
): { base: string; p: Record<string, string> } | null {
    const base = checkmkUrl?.replace(/\/check_mk\/?$/, '').replace(/\/$/, '');
    if (!base) return null;
    const parts = base.split('/');
    const site = parts[parts.length - 1] || null;
    const p: Record<string, string> = {};
    if (site) p.site = site;
    return { base, p };
}

// Wrap a relative Checkmk path in `index.py?start_url=…` so the landing page
// keeps Checkmk's chrome (sidebar, top-bar, breadcrumbs) instead of dropping
// the operator into a bare view. Bare view URLs are still useful inside an
// embedded iframe (no double chrome), but at the OrbVis layer "open in
// Checkmk" always means "open the real Checkmk page".
function _wrapInChrome(base: string, viewPath: string, viewParams: URLSearchParams): string {
    const inner = `${viewPath}?${viewParams}`;
    const outer = new URLSearchParams({ start_url: inner });
    return `${base}/check_mk/index.py?${outer}`;
}

export function buildCheckmkUrl(obj: BoardObject, checkmkUrl: string | null): string | null {
    const r = _baseAndSite(checkmkUrl);
    if (!r) return null;
    const { base, p } = r;

    if ((obj.type === 'host' || obj.type === 'line') && obj.host_name && !obj.service_description) {
        p.view_name = 'hoststatus';
        p.host = obj.host_name;
        return _wrapInChrome(base, 'view.py', new URLSearchParams(p));
    }
    if (
        (obj.type === 'service' || obj.type === 'line') &&
        obj.host_name &&
        obj.service_description
    ) {
        p.view_name = 'service';
        p.host = obj.host_name;
        p.service = obj.service_description;
        return _wrapInChrome(base, 'view.py', new URLSearchParams(p));
    }
    if (obj.type === 'hostgroup' && obj.group_name) {
        p.view_name = 'hostgroup';
        p.hostgroup = obj.group_name;
        return _wrapInChrome(base, 'view.py', new URLSearchParams(p));
    }
    if (obj.type === 'servicegroup' && obj.group_name) {
        p.view_name = 'servicegroup';
        p.servicegroup = obj.group_name;
        return _wrapInChrome(base, 'view.py', new URLSearchParams(p));
    }
    if (obj.type === 'aggregation' && obj.aggregation_id) {
        p.view_name = 'aggr_single';
        p.aggr_name = obj.aggregation_id;
        p.po_aggr_expand = '1';
        return _wrapInChrome(base, 'view.py', new URLSearchParams(p));
    }
    if (obj.type === 'site' && obj.host_name) {
        // Site root drills into the per-site host overview.
        p.view_name = 'allhosts';
        p.site = obj.host_name;
        return _wrapInChrome(base, 'view.py', new URLSearchParams(p));
    }
    return null;
}

/**
 * For object types where the live monitoring view (``buildCheckmkUrl``)
 * isn't where the operator's "edit this thing" intent leads, return the
 * configuration/setup URL.
 *
 * BI aggregations: when ``packId`` is supplied (resolved from the
 * AggregationInfo cache the EditPanel + Drawer already keep), deep-link
 * straight into the rules editor of that pack (``mode=bi_rules&pack=…``)
 * so the operator can immediately find + edit the aggregation. Falls
 * back to the BI packs overview (``mode=bi_packs``) when no pack id is
 * available — better than nothing, just one extra click.
 */
export function buildCheckmkSetupUrl(
    obj: BoardObject,
    checkmkUrl: string | null,
    packId?: string | null,
): string | null {
    const r = _baseAndSite(checkmkUrl);
    if (!r) return null;
    const { base, p } = r;
    if (obj.type === 'aggregation') {
        if (packId) {
            p.mode = 'bi_rules';
            p.pack = packId;
        } else {
            p.mode = 'bi_packs';
        }
        return _wrapInChrome(base, 'wato.py', new URLSearchParams(p));
    }
    return null;
}

export function buildCheckmkUrlFromState(
    state: ObjectState,
    checkmkUrl: string | null,
): string | null {
    const r = _baseAndSite(checkmkUrl);
    if (!r) return null;
    const { base, p } = r;

    if (state.type === 'service' && state.object_id.includes(';')) {
        const [host, svc] = state.object_id.split(';', 2);
        p.view_name = 'service';
        p.host = host;
        p.service = svc;
        return _wrapInChrome(base, 'view.py', new URLSearchParams(p));
    }
    if (state.type === 'host') {
        p.view_name = 'hoststatus';
        p.host = state.object_id;
        return _wrapInChrome(base, 'view.py', new URLSearchParams(p));
    }
    return null;
}

// Uses a real <a> click so the browser doesn't treat it as a popup (important
// when OrbVis runs inside a Checkmk iframe — window.open gets popup-blocked).
export function openUrl(url: string, target: string): void {
    const a = document.createElement('a');
    a.href = url;
    a.target = target;
    a.rel = 'noreferrer';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}
