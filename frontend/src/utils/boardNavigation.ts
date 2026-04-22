import type { BoardObject } from '@/types/api';

export function buildCheckmkUrl(obj: BoardObject, checkmkUrl: string | null): string | null {
  const base = checkmkUrl?.replace(/\/check_mk\/?$/, '').replace(/\/$/, '');
  if (!base) return null;
  const parts = base.split('/');
  const site = parts[parts.length - 1] || null;
  const p: Record<string, string> = {};
  if (site) p.site = site;

  if (obj.type === 'host' && obj.host_name) {
    p.view_name = 'hoststatus';
    p.host = obj.host_name;
    return `${base}/check_mk/view.py?${new URLSearchParams(p)}`;
  }
  if (obj.type === 'service' && obj.host_name && obj.service_description) {
    p.view_name = 'service';
    p.host = obj.host_name;
    p.service = obj.service_description;
    return `${base}/check_mk/view.py?${new URLSearchParams(p)}`;
  }
  if (obj.type === 'hostgroup' && obj.group_name) {
    p.view_name = 'hostgroup';
    p.hostgroup = obj.group_name;
    return `${base}/check_mk/view.py?${new URLSearchParams(p)}`;
  }
  if (obj.type === 'servicegroup' && obj.group_name) {
    p.view_name = 'servicegroup';
    p.servicegroup = obj.group_name;
    return `${base}/check_mk/view.py?${new URLSearchParams(p)}`;
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
