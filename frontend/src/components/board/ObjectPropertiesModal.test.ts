import { flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { BoardObject } from '@/types/api'

import ObjectPropertiesModal from './ObjectPropertiesModal.vue'

// The dialog loads metric / board / image choices on mount; any API call
// resolves empty so the test only exercises the form layout.
vi.mock('@/api/client', () => {
  const empty = new Proxy({}, { get: () => vi.fn().mockResolvedValue([]) })
  return { boardsApi: empty, connectionsApi: empty, imagesApi: empty }
})

function makeObject(mode: 'icon' | 'text', show: boolean, stateBorder = false): BoardObject {
  // stateBorder also switches the state background on, so one mount covers both.
  return {
    id: 'svc_1',
    type: 'service',
    x: 0,
    y: 0,
    host_name: 'web01',
    service_description: 'CPU load',
    display: { mode, state_border: stateBorder, state_background: stateBorder },
    label: { show, x: 0, y: 0, size: 11, color: '#ffffff', background: 'transparent' },
    url_target: '_blank'
  }
}

async function mountModal(mode: 'icon' | 'text', show: boolean, stateBorder = false) {
  const wrapper = shallowMount(ObjectPropertiesModal, {
    props: { object: makeObject(mode, show, stateBorder), connectionId: 'c1' },
    global: { renderStubDefaultSlot: true }
  })
  await flushPromises()
  return wrapper
}

function fieldLabels(wrapper: Awaited<ReturnType<typeof mountModal>>, disabledOnly: boolean) {
  return wrapper
    .findAll('.field-row')
    .filter(
      (row) =>
        !disabledOnly ||
        row.classes('orb-props__disabled') ||
        row.element.closest('.orb-props__disabled')
    )
    .map((row) => row.find('label.field-label').text())
}

describe('ObjectPropertiesModal – text only', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('greys out the fields without effect and keeps the effective label fields editable', async () => {
    const disabled = fieldLabels(await mountModal('text', false), true)
    expect(disabled).toEqual(expect.arrayContaining(['Show label', 'Color', 'Size', 'Custom icon']))
    expect(disabled).not.toContain('Label text')
    expect(disabled).not.toContain('Offset X')
  })

  it('still greys out the label fields when an icon hides its label', async () => {
    const disabled = fieldLabels(await mountModal('icon', false), true)
    expect(disabled).toEqual(expect.arrayContaining(['Label text', 'Color', 'Offset X']))
    expect(disabled).not.toContain('Show label')
    expect(disabled).not.toContain('Custom icon')
  })

  it('offers a state border only for text-only objects and greys out the border color then', async () => {
    // The "Background & border" fields sit behind a collapsed toggle.
    const text = await mountModal('text', true, true)
    await text.find('button.orb-props__toggle').trigger('click')
    expect(fieldLabels(text, false)).toEqual(
      expect.arrayContaining(['Border by state', 'Background by state'])
    )
    expect(fieldLabels(text, true)).toEqual(expect.arrayContaining(['Border color', 'Background']))

    const icon = await mountModal('icon', true)
    await icon.find('button.orb-props__toggle').trigger('click')
    expect(fieldLabels(icon, false)).not.toContain('Border by state')
    expect(fieldLabels(icon, false)).not.toContain('Background by state')
    expect(fieldLabels(icon, true)).not.toContain('Border color')
    expect(fieldLabels(icon, true)).not.toContain('Background')
  })
})
