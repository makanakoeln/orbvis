import { connectionsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { AggregationInfo, MetricChoice } from '@/types/api'

// Shared host/service/group/metric lookups for every binding surface
// (inspector, data panel, connect-data popover). Results are cached per
// connection so opening the inspector on ten elements fetches the host list
// once; a failed fetch is evicted so the next call retries instead of pinning
// an empty list.
const cache = new Map<string, Promise<unknown>>()

function cached<T>(key: string, fetcher: () => Promise<T>, empty: T): Promise<T> {
  const hit = cache.get(key)
  if (hit) return hit as Promise<T>
  const p = fetcher().catch(() => {
    cache.delete(key)
    return empty
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

  function objectNames(type: 'host' | 'hostgroup' | 'servicegroup'): Promise<string[]> {
    const conn = connectionId()
    if (!conn || !token()) return Promise.resolve([])
    return cached(`${type}|${conn}`, () => connectionsApi.objects(conn, type, token()), [])
  }

  function hosts(): Promise<string[]> {
    return objectNames('host')
  }

  function hostgroups(): Promise<string[]> {
    return objectNames('hostgroup')
  }

  function servicegroups(): Promise<string[]> {
    return objectNames('servicegroup')
  }

  function aggregations(): Promise<AggregationInfo[]> {
    const conn = connectionId()
    if (!conn || !token()) return Promise.resolve([])
    return cached(`aggregations|${conn}`, () => connectionsApi.aggregations(conn, token()), [])
  }

  function services(host: string): Promise<string[]> {
    const conn = connectionId()
    if (!conn || !host || !token()) return Promise.resolve([])
    return cached(
      `services|${conn}|${host}`,
      () => connectionsApi.objects(conn, 'service', token(), host),
      []
    )
  }

  function metrics(host: string, service?: string | null): Promise<MetricChoice[]> {
    const conn = connectionId()
    if (!conn || !host || !token()) return Promise.resolve([])
    return cached(
      `metrics|${conn}|${host}|${service ?? ''}`,
      () => connectionsApi.perfMetrics(conn, host, token(), service ?? undefined),
      []
    )
  }

  return { hosts, hostgroups, servicegroups, aggregations, services, metrics }
}
