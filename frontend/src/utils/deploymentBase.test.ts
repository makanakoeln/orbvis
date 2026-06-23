import { afterEach, describe, expect, it } from 'vitest'

import { resolveDeploymentBase } from './deploymentBase'

describe('resolveDeploymentBase', () => {
  afterEach(() => {
    delete window.__ORBVIS_BASE__
  })

  it('prefers the injected base and strips trailing slashes', () => {
    window.__ORBVIS_BASE__ = '/heute/orbvis/'
    expect(resolveDeploymentBase()).toBe('/heute/orbvis')
  })

  it('ignores an empty injected base', () => {
    window.__ORBVIS_BASE__ = ''
    // import.meta.env.BASE_URL is '/' under vitest -> stripped to ''
    expect(resolveDeploymentBase()).toBe('')
  })

  it('falls back to the build-time base when not injected', () => {
    expect(resolveDeploymentBase()).toBe('')
  })
})
