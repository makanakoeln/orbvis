import { connectionsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

// Shared host/service/metric lookups for every binding surface (inspector,
// data panel, connect-data popover). Results are cached per connection so
// opening the inspector on ten elements fetches the host list once; a failed
// fetch is evicted so the next call retries instead of pinning an empty list.
const cache = new Map<string, Promise<string[]>>()

function cached(key: string, fetcher: () => Promise<string[]>): Promise<string[]> {
  const hit = cache.get(key)
  if (hit) return hit
  const p = fetcher().catch(() => {
    cache.delete(key)
    return [] as string[]
  })
  cache.set(key, p)
  return p
}

export function clearDataBindingCache(): void {
  cache.clear()
}

export function useDataBinding(connectionId: () => string) {
  const auth = useAuthStore()

  function token(): string {
    return auth.accessToken ?? ''
  }

  function hosts(): Promise<string[]> {
    const conn = connectionId()
    if (!conn || !token()) return Promise.resolve([])
    return cached(`hosts|${conn}`, () => connectionsApi.objects(conn, 'host', token()))
  }

  function services(host: string): Promise<string[]> {
    const conn = connectionId()
    if (!conn || !host || !token()) return Promise.resolve([])
    return cached(`services|${conn}|${host}`, () =>
      connectionsApi.objects(conn, 'service', token(), host)
    )
  }

  function metrics(host: string, service?: string | null): Promise<string[]> {
    const conn = connectionId()
    if (!conn || !host || !token()) return Promise.resolve([])
    return cached(`metrics|${conn}|${host}|${service ?? ''}`, () =>
      connectionsApi.perfMetrics(conn, host, token(), service ?? undefined)
    )
  }

  return { hosts, services, metrics }
}
