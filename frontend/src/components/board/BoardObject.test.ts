import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { BoardObject as BoardObjectType, MonitoringState } from '@/types/api'

import BoardObject from './BoardObject.vue'

function makeImageObject(overrides: Partial<BoardObjectType> = {}): BoardObjectType {
  return {
    id: 'image_1',
    type: 'image',
    x: 100,
    y: 100,
    image_src: 'box.svg',
    label: { show: false, x: 0, y: 0, size: 11, color: '#fff', background: 'transparent' },
    url_target: '_blank',
    z: 1,
    ...overrides
  }
}

function imgStyle(object: BoardObjectType, iconSize: number): CSSStyleDeclaration {
  const wrapper = mount(BoardObject, { props: { object, state: undefined, iconSize } })
  return (wrapper.find('img.orb-obj__icon-img').element as HTMLImageElement).style
}

describe('BoardObject – image size', () => {
  it('scales an image to an explicit image_size, keeping its aspect', () => {
    const style = imgStyle(
      makeImageObject({
        display: { mode: 'icon', image: 'box.svg', image_size: 100 }
      }),
      100
    )
    expect(style.width).toBe('100px')
    expect(style.height).toBe('100px')
    expect(style.objectFit).toBe('contain')
  })

  it('only caps an image at the board icon size without an explicit image_size', () => {
    const style = imgStyle(makeImageObject(), 32)
    expect(style.width).toBe('')
    expect(style.maxWidth).toBe('32px')
    expect(style.maxHeight).toBe('32px')
  })
})

function textPillStyle(
  state: MonitoringState,
  display: Partial<NonNullable<BoardObjectType['display']>> = {}
): CSSStyleDeclaration {
  const object: BoardObjectType = {
    id: 'svc_1',
    type: 'service',
    x: 0,
    y: 0,
    host_name: 'web01',
    service_description: 'CPU load',
    display: { mode: 'text', ...display },
    // What the properties dialog / NagVis import store: a label color and border.
    label: { show: true, x: 0, y: 0, size: 11, color: '#ffffff', background: 'transparent' },
    label_border: '#e5e5e5',
    url_target: '_blank'
  }
  const wrapper = mount(BoardObject, {
    props: {
      object,
      state: {
        object_id: 'svc_1',
        type: 'service',
        state,
        output: '',
        perf_data: '',
        acknowledged: false,
        in_downtime: false,
        stale: false
      },
      iconSize: 32
    }
  })
  return (wrapper.find('.orb-obj__text-pill').element as HTMLElement).style
}

describe('BoardObject – text only', () => {
  it('colors the text by state when no fixed text color is set', () => {
    expect(textPillStyle('OK').color).toBe('rgb(34, 197, 94)')
    expect(textPillStyle('WARNING').color).not.toBe(textPillStyle('OK').color)
  })

  it('uses a fixed text color, white included, whatever the state', () => {
    expect(textPillStyle('CRITICAL', { text_color: '#ffffff' }).color).toBe('rgb(255, 255, 255)')
    expect(textPillStyle('OK', { text_color: '#facc15' }).color).toBe('rgb(250, 204, 21)')
  })

  it('fills the background by state and keeps state-colored text readable', () => {
    expect(textPillStyle('OK').background).toBe('rgba(0, 0, 0, 0.65)')
    const filled = textPillStyle('OK', { state_background: true })
    expect(filled.background).toBe('rgb(34, 197, 94)')
    expect(filled.color).toBe('rgb(255, 255, 255)')
    expect(textPillStyle('OK', { state_background: true, text_color: '#000000' }).color).toBe(
      'rgb(0, 0, 0)'
    )
  })

  it('keeps the label border unless the border follows the state', () => {
    expect(textPillStyle('CRITICAL').outline).toBe('1px solid #e5e5e5')
    expect(textPillStyle('OK', { state_border: true }).outline).toBe('2px solid rgb(34,197,94)')
  })
})
