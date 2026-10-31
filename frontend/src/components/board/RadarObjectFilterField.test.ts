import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import RadarObjectFilterField from './RadarObjectFilterField.vue'

function mountField(modelValue: string, objectTypes: 'host' | 'service' = 'host') {
  return mount(RadarObjectFilterField, { props: { modelValue, objectTypes } })
}

describe('RadarObjectFilterField', () => {
  it('emits the typed filter', async () => {
    const wrapper = mountField('')
    await wrapper.find('textarea').setValue('Filter: host_name ~ ^fw-')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['Filter: host_name ~ ^fw-'])
  })

  it('shows no error for an empty or valid filter', () => {
    expect(mountField('').find('.radar-filter__error').exists()).toBe(false)
    expect(mountField('Filter: state > 0').find('.radar-filter__error').exists()).toBe(false)
  })

  it('flags a filter with non-filter headers', () => {
    const wrapper = mountField('Columns: name')
    expect(wrapper.find('.radar-filter__error').exists()).toBe(true)
    expect(wrapper.find('textarea').attributes('aria-invalid')).toBe('true')
  })

  it('suggests columns of the matching Livestatus table', () => {
    expect(mountField('', 'host').find('textarea').attributes('placeholder')).toContain('host_name')
    expect(mountField('', 'service').find('textarea').attributes('placeholder')).toContain(
      'description'
    )
  })
})
