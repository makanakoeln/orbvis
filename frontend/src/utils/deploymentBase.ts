declare global {
  interface Window {
    // Built-in Checkmk injects the per-site deployment base (e.g.
    // "/heute/orbvis") via the page handler, so one shared bundle can serve
    // every site. Absent in the standalone / MKP build.
    __ORBVIS_BASE__?: string
  }
}

// The base path the OrbVis REST API and SSE stream live under, without a
// trailing slash (e.g. "/heute/orbvis" or "").
//
// Resolution order:
//   1. window.__ORBVIS_BASE__ — injected by the built-in Checkmk page handler.
//   2. the Vite build-time base (import.meta.env.BASE_URL), e.g. "/heute/orbvis/"
//      for the standalone / MKP build.
//   3. for a relative build (--base=./), the current document path.
export function resolveDeploymentBase(): string {
  const injected = window.__ORBVIS_BASE__
  if (injected) {
    return injected.replace(/\/+$/, '')
  }
  const base = import.meta.env.BASE_URL
  return base.startsWith('.')
    ? window.location.pathname.replace(/\/+$/, '')
    : base.replace(/\/+$/, '')
}
