import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { PresentationElement, PresentationView } from '@/types/api'
import { createElement } from '@/utils/presentationElements'

import PresentationInspectorPanel from './PresentationInspectorPanel.vue'

const { mockConnectionsApi } = vi.hoisted(() => ({
  mockConnectionsApi: {
    objects: vi.fn().mockResolvedValue([]),
    perfMetrics: vi.fn().mockResolvedValue([]),
    list: vi.fn().mockResolvedValue([])
  }
}))

vi.mock('@/api/client', () => ({
  connectionsApi: mockConnectionsApi,
  imagesApi: { list: vi.fn().mockResolvedValue([]) },
  boardsApi: { list: vi.fn().mockResolvedValue([]) }
}))

function makeView(): PresentationView {
  return { type: 'presentation', width: 1920, height: 1080, theme: 'midnight', elements: [] }
}

function mountPanel(selection: PresentationElement[]) {
  return mount(PresentationInspectorPanel, {
    props: {
      selection,
      view: makeView(),
      connectionId: 'live_1',
      targets: [],
      backgroundImageName: ''
    }
  })
}

describe('PresentationInspectorPanel', () => {
  beforeEach(() => {
    mockConnectionsApi.objects.mockClear()
  })

  it('shows slide settings when nothing is selected', () => {
    const wrapper = mountPanel([])
    expect(wrapper.text()).toContain('Slide')
    expect(wrapper.text()).toContain('Aspect / size')
    expect(wrapper.text()).toContain('Background')
  })

  it('emits a slide change for a size preset', async () => {
    const wrapper = mountPanel([])
    await wrapper.find('.insp__preset').trigger('click')
    const emitted = wrapper.emitted('slide')
    expect(emitted).toBeTruthy()
    expect(emitted![0]![0]).toEqual({ width: 1920, height: 1080 })
  })

  it('shows layout + typography for a text element and emits patches', async () => {
    const text = createElement('text', 0, 0)
    const wrapper = mountPanel([text])
    expect(wrapper.text()).toContain('Layout')
    expect(wrapper.text()).toContain('Typography')

    const bold = wrapper.findAll('button').find((b) => b.text() === 'B')
    expect(bold).toBeTruthy()
    await bold!.trigger('click')
    const patches = wrapper.emitted('patch')
    expect(patches).toBeTruthy()
    expect(patches![0]![0]).toHaveProperty('font_weight')
  })

  it('shows appearance + data sections for a shape', () => {
    const shape = createElement('rect', 0, 0)
    const wrapper = mountPanel([shape])
    expect(wrapper.text()).toContain('Appearance')
    expect(wrapper.text()).toContain('Data')
    expect(wrapper.text()).toContain('Data slot')
  })

  it('shows display controls and binding form for a data element', () => {
    const data = createElement('data', 0, 0)
    const wrapper = mountPanel([data])
    expect(wrapper.text()).toContain('Layout')
    expect(wrapper.text()).toContain('Host')
    expect(wrapper.text()).toContain('Display')
  })

  it('hides the layout numbers for connectors', () => {
    const line = createElement('line', 0, 0)
    const wrapper = mountPanel([line])
    expect(wrapper.text()).not.toContain('Layout')
    expect(wrapper.text()).toContain('Start endpoint')
  })

  it('shows the shared subset for a multi-selection', () => {
    const a = createElement('rect', 0, 0)
    const b = createElement('text', 0, 0)
    const wrapper = mountPanel([a, b])
    expect(wrapper.text()).toContain('2 elements selected')
    expect(wrapper.find('.orb-range').exists()).toBe(true)
  })

  it('renames the element via the header input', async () => {
    const shape = createElement('rect', 0, 0)
    const wrapper = mountPanel([shape])
    const name = wrapper.find('.insp__name')
    await name.setValue('Core switch')
    await name.trigger('change')
    const patches = wrapper.emitted('patch')!
    expect(patches[patches.length - 1]![0]).toEqual({ name: 'Core switch' })
  })
})
