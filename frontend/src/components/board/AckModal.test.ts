import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'

import type { BoardObject } from '@/types/api'

import AckModal from './AckModal.vue'

const { cmkApi } = vi.hoisted(() => ({
  cmkApi: {
    acknowledgeHost: vi.fn().mockResolvedValue(undefined),
    acknowledgeService: vi.fn().mockResolvedValue(undefined),
    acknowledgeHostgroup: vi.fn().mockResolvedValue(undefined),
    acknowledgeServicegroup: vi.fn().mockResolvedValue(undefined)
  }
}))

vi.mock('@/api/client', () => ({ cmkApi }))

// Minimal stubs for the vendored CMK widgets so the test exercises AckModal's
// own routing/validation logic, not the design-system internals.
const InputStub = defineComponent({
  props: { modelValue: { type: String, default: '' } },
  emits: ['update:modelValue'],
  // AckModal calls commentEl.value?.focus() onMounted; the ref resolves to this
  // component instance, so it must expose a focus() method.
  methods: { focus() {} },
  template: `<input :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" />`
})
const ButtonStub = defineComponent({
  props: { disabled: { type: Boolean, default: false } },
  emits: ['click'],
  template: `<button :disabled="disabled" @click="$emit('click')"><slot /></button>`
})
const PassThrough = defineComponent({ template: `<div><slot /><slot name="footer" /></div>` })
const CheckboxStub = defineComponent({
  props: { modelValue: { type: Boolean, default: false } },
  template: `<span />`
})

function obj(extra: Partial<BoardObject> = {}): BoardObject {
  return { id: 'o', type: 'host', x: 0, y: 0, url_target: '', host_name: 'web01', ...extra }
}

function render(object: BoardObject) {
  return mount(AckModal, {
    props: { object, checkmkUrl: 'https://cmk.example.com/site' },
    global: {
      stubs: {
        OrbModal: PassThrough,
        CmkInput: InputStub,
        CmkButton: ButtonStub,
        CmkCheckbox: CheckboxStub,
        CmkAlertBox: PassThrough
      }
    }
  })
}

async function submitWithComment(wrapper: ReturnType<typeof render>, comment = 'fixing it') {
  await wrapper.find('input').setValue(comment)
  // The Acknowledge button is the second (primary) button in the footer.
  const buttons = wrapper.findAll('button')
  await buttons[buttons.length - 1]!.trigger('click')
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('AckModal submit routing', () => {
  it('acknowledges a host', async () => {
    const wrapper = render(obj({ type: 'host', host_name: 'web01' }))
    await submitWithComment(wrapper)
    expect(cmkApi.acknowledgeHost).toHaveBeenCalledWith(
      'https://cmk.example.com/site',
      'web01',
      'fixing it',
      true,
      true,
      false,
      null
    )
  })

  it('acknowledges a service', async () => {
    const wrapper = render(
      obj({ type: 'service', host_name: 'web01', service_description: 'PING' })
    )
    await submitWithComment(wrapper)
    expect(cmkApi.acknowledgeService).toHaveBeenCalledWith(
      'https://cmk.example.com/site',
      'web01',
      'PING',
      'fixing it',
      true,
      true,
      false,
      null
    )
  })

  it('acknowledges a hostgroup via the fan-out endpoint', async () => {
    const wrapper = render(obj({ type: 'hostgroup', group_name: 'linux', host_name: null }))
    await submitWithComment(wrapper)
    expect(cmkApi.acknowledgeHostgroup).toHaveBeenCalledWith(
      'https://cmk.example.com/site',
      'linux',
      'fixing it',
      true,
      true,
      false
    )
  })

  it('acknowledges a servicegroup via the fan-out endpoint', async () => {
    const wrapper = render(obj({ type: 'servicegroup', group_name: 'db', host_name: null }))
    await submitWithComment(wrapper)
    expect(cmkApi.acknowledgeServicegroup).toHaveBeenCalledWith(
      'https://cmk.example.com/site',
      'db',
      'fixing it',
      true,
      true,
      false
    )
  })
})

describe('AckModal validation + feedback', () => {
  it('does not submit with an empty comment', async () => {
    const wrapper = render(obj())
    const buttons = wrapper.findAll('button')
    await buttons[buttons.length - 1]!.trigger('click')
    await flushPromises()
    expect(cmkApi.acknowledgeHost).not.toHaveBeenCalled()
  })

  it('shows a success message after acknowledging', async () => {
    const wrapper = render(obj())
    await submitWithComment(wrapper)
    expect(wrapper.text()).toContain('Acknowledgement set')
  })

  it('surfaces an error and appends the group hint for unconfigured groups', async () => {
    cmkApi.acknowledgeHostgroup.mockRejectedValueOnce(
      new Error('These fields have problems: hostgroup_name')
    )
    const wrapper = render(obj({ type: 'hostgroup', group_name: 'adhoc', host_name: null }))
    await submitWithComment(wrapper)
    expect(wrapper.text()).toContain('hostgroup_name')
    expect(wrapper.text()).toContain('Setup → Host groups')
  })
})
