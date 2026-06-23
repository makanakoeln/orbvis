import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, authApi, mapsApi } from './client'

const originalFetch = globalThis.fetch

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'content-type': 'application/json' },
    ...init
  })
}

function errorResponse(status: number, detail: unknown): Response {
  return new Response(JSON.stringify({ detail }), {
    status,
    headers: { 'content-type': 'application/json' }
  })
}

beforeEach(() => {
  globalThis.fetch = vi.fn() as unknown as typeof fetch
})

afterEach(() => {
  globalThis.fetch = originalFetch
  vi.restoreAllMocks()
})

describe('api client request()', () => {
  it('sends bearer token when provided', async () => {
    const mock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    mock.mockResolvedValueOnce(jsonResponse({ name: 'admin' }))

    await authApi.me('my-access-token')

    expect(mock).toHaveBeenCalledTimes(1)
    const [url, init] = mock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/auth/me')
    const headers = init.headers as Record<string, string>
    expect(headers['Authorization']).toBe('Bearer my-access-token')
  })

  it('omits the Authorization header when no token is given', async () => {
    const mock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    mock.mockResolvedValueOnce(jsonResponse({ access_token: 'a', refresh_token: 'r' }))

    await authApi.login('admin', 'secret')

    const [, init] = mock.mock.calls[0] as [string, RequestInit]
    const headers = init.headers as Record<string, string>
    expect(headers['Authorization']).toBeUndefined()
    expect(init.method).toBe('POST')
    expect(init.body).toBe(JSON.stringify({ username: 'admin', password: 'secret' }))
  })

  it('tunnels PATCH/PUT/DELETE through POST with X-HTTP-Method-Override', async () => {
    const mock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    mock.mockResolvedValueOnce(new Response(null, { status: 204 }))

    await mapsApi.delete('foo', 't')

    const [, init] = mock.mock.calls[0] as [string, RequestInit]
    expect(init.method).toBe('POST')
    const headers = init.headers as Record<string, string>
    expect(headers['X-HTTP-Method-Override']).toBe('DELETE')
  })

  it('does not tunnel GET or POST', async () => {
    const mock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    mock.mockResolvedValueOnce(jsonResponse([]))

    await mapsApi.list('t')

    const [, init] = mock.mock.calls[0] as [string, RequestInit]
    expect(init.method).toBe('GET')
    const headers = init.headers as Record<string, string>
    expect(headers['X-HTTP-Method-Override']).toBeUndefined()
  })

  it('returns undefined for 204 No Content', async () => {
    const mock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    mock.mockResolvedValueOnce(new Response(null, { status: 204 }))

    const result = await authApi.logout('t')
    expect(result).toBeUndefined()
  })

  it('throws ApiError with status + detail on 4xx', async () => {
    const mock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    mock.mockResolvedValueOnce(errorResponse(401, 'Invalid credentials'))

    await expect(authApi.login('admin', 'bad')).rejects.toMatchObject({
      name: 'ApiError',
      status: 401,
      message: 'Invalid credentials'
    })
  })

  it('falls back to "HTTP <code>" when the error body is not JSON', async () => {
    const mock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    mock.mockResolvedValueOnce(
      new Response('<html>500</html>', {
        status: 500,
        headers: { 'content-type': 'text/html' }
      })
    )

    await expect(authApi.login('admin', 'x')).rejects.toMatchObject({
      name: 'ApiError',
      status: 500,
      message: 'HTTP 500'
    })
  })

  it('uses ApiError as the thrown type so handlers can branch on instanceof', async () => {
    const mock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    mock.mockResolvedValueOnce(errorResponse(403, 'nope'))

    try {
      await authApi.me('t')
      throw new Error('should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect((err as ApiError).detail).toEqual({ detail: 'nope' })
    }
  })
})
