import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { FolderTreeNode } from '@/types/api'

import FolderTreeRow from './FolderTreeRow.vue'

function makeNode(overrides: Partial<FolderTreeNode> = {}): FolderTreeNode {
  return {
    path: '/main',
    title: 'Main',
    kind: 'folder',
    state: 'OK',
    is_empty: false,
    folder_id: 'main',
    host_count: 5,
    problem_count: 0,
    severity_counts: {},
    output: '',
    acknowledged: false,
    in_downtime: false,
    site_id: null,
    children: [],
    ...overrides
  }
}

const baseProps = {
  rev: 0,
  depth: 0,
  isOpen: false,
  isExpandable: true,
  multiSite: false
}

describe('FolderTreeRow', () => {
  it('renders a folder row with title and host count', () => {
    const wrapper = mount(FolderTreeRow, {
      props: { ...baseProps, node: makeNode() }
    })

    expect(wrapper.find('.ft-title').text()).toBe('Main')
    expect(wrapper.find('.ft-meta').text()).toContain('5 hosts')
    expect(wrapper.find('.ft-chevron').exists()).toBe(true)
  })

  it('shows severity pills with problem counts on a folder', () => {
    const wrapper = mount(FolderTreeRow, {
      props: {
        ...baseProps,
        node: makeNode({
          state: 'CRITICAL',
          problem_count: 3,
          severity_counts: { CRITICAL: 2, WARNING: 1 }
        })
      }
    })

    const pills = wrapper.findAll('.ft-pill')
    expect(pills.map((p) => p.text())).toEqual(['2', '1'])
    expect(pills[0]!.attributes('title')).toBe('2 CRITICAL')
    // Healthy remainder: 5 hosts − 3 problems = 2 OK.
    expect(wrapper.find('.ft-meta').text()).toContain('2 OK')
  })

  it('renders a host row with state dot and emits select-host on click', async () => {
    const node = makeNode({
      path: '/main/web-01',
      title: 'web-01',
      kind: 'host',
      state: 'DOWN',
      host_count: 0
    })
    const wrapper = mount(FolderTreeRow, {
      props: { ...baseProps, isExpandable: false, node }
    })

    expect(wrapper.find('.ft-title').text()).toBe('web-01')
    expect(wrapper.find('.ft-dot').attributes('title')).toBe('DOWN')

    await wrapper.find('.ft-row').trigger('click')
    expect(wrapper.emitted('select-host')).toEqual([[node]])
  })

  it('marks empty folders and renders the empty badge', () => {
    const wrapper = mount(FolderTreeRow, {
      props: {
        ...baseProps,
        isExpandable: false,
        node: makeNode({ title: 'Staging', is_empty: true, host_count: 0 })
      }
    })

    expect(wrapper.find('.ft-badge--empty').exists()).toBe(true)
    expect(wrapper.find('.ft-dot').exists()).toBe(false)
  })
})
