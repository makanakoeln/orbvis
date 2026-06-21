import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'

import type { BulkAckTarget } from '@/types/api'

import BulkAckModal from './BulkAckModal.vue'

const { cmkApi } = vi.hoisted(() => ({
  cmkApi: {
    acknowledgeHost: vi.fn().mockResolvedValue(undefined),
    acknowledgeService: vi.fn().mockResolvedValue(undefined)
  }
}))

vi.mock('@/api/client', () => ({ cmkApi }))

const InputStub = defineComponent({
  props: { modelValue: { type: String, default: '' } },
  emits: ['update:modelValue'],
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

function target(host: string, service: string | null = null): BulkAckTarget {
  return { host, service }
}

function render(targets: BulkAckTarget[]) {
  return mount(BulkAckModal, {
    props: { aggregationId: 'agg-1', targets, checkmkUrl: 'https://cmk.example.com/site' },
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

async function clickSubmit(wrapper: ReturnType<typeof render>) {
  const buttons = wrapper.findAll('button')
  await buttons[buttons.length - 1]!.trigger('click')
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('BulkAckModal', () => {
  it('pre-fills the comment with the aggregation trailer', () => {
    const wrapper = render([target('web01')])
    expect(wrapper.find('input').element.value).toBe('Bulk-ack: agg-1')
  })

  it('lists every target', () => {
    const wrapper = render([target('web01', 'PING'), target('db02')])
    const items = wrapper.findAll('.bulk-ack__item')
    expect(items).toHaveLength(2)
    expect(items[0]!.text()).toContain('web01')
    expect(items[0]!.text()).toContain('PING')
  })

  it('routes each leaf to host or service ack', async () => {
    const wrapper = render([target('web01', 'PING'), target('db02')])
    await clickSubmit(wrapper)
    expect(cmkApi.acknowledgeService).toHaveBeenCalledTimes(1)
    expect(cmkApi.acknowledgeService).toHaveBeenCalledWith(
      'https://cmk.example.com/site',
      'web01',
      'PING',
      'Bulk-ack: agg-1',
      true,
      true,
      false
    )
    expect(cmkApi.acknowledgeHost).toHaveBeenCalledTimes(1)
    expect(cmkApi.acknowledgeHost).toHaveBeenCalledWith(
      'https://cmk.example.com/site',
      'db02',
      'Bulk-ack: agg-1',
      true,
      true,
      false
    )
  })

  it('acknowledges every target even beyond the concurrency cap', async () => {
    const targets = Array.from({ length: 12 }, (_, i) => target(`h${i}`))
    const wrapper = render(targets)
    await clickSubmit(wrapper)
    expect(cmkApi.acknowledgeHost).toHaveBeenCalledTimes(12)
    expect(wrapper.text()).toContain('12 leaves acknowledged')
  })

  it('reports partial failures without aborting the rest', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    cmkApi.acknowledgeHost.mockRejectedValueOnce(new Error('pipe closed'))
    const wrapper = render([target('bad'), target('good')])
    await clickSubmit(wrapper)
    expect(cmkApi.acknowledgeHost).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('1 of 2 failed')
    expect(wrapper.text()).toContain('bad')
    warn.mockRestore()
  })
})
