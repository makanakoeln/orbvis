import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { AggregationNode } from '@/types/api'

import AggregationSubtree from './AggregationSubtree.vue'

const WORST_PATH_COLOR = 'rgb(244 114 182)'

function leaf(name: string, state: number, extra: Partial<AggregationNode> = {}): AggregationNode {
  return { name, node_type: 'bi_leaf', state, children: [], host_name: name, ...extra }
}

function agg(name: string, children: AggregationNode[], state = 0): AggregationNode {
  return { name, node_type: 'bi_aggregator', state, children }
}

function render(tree: AggregationNode, maxDepth = 5) {
  return mount(AggregationSubtree, {
    props: { tree, iconSize: 32, maxDepth }
  })
}

describe('AggregationSubtree rendering', () => {
  it('renders one node per non-root tree node', () => {
    const tree = agg('root', [leaf('a', 0), leaf('b', 0)])
    const wrapper = render(tree)
    // Root is the board icon itself and is skipped.
    expect(wrapper.findAll('.orb-aggr-subtree__node')).toHaveLength(2)
  })

  it('draws a link per parent-child edge', () => {
    const tree = agg('root', [leaf('a', 0), agg('mid', [leaf('c', 0)])])
    const wrapper = render(tree)
    // 3 non-root nodes → 3 edges from their parents.
    expect(wrapper.findAll('line')).toHaveLength(3)
  })

  it('respects maxDepth by trimming deeper nodes', () => {
    const deep = agg('root', [agg('mid', [leaf('deep', 0)])])
    const wrapper = render(deep, 1)
    // Only the depth-1 "mid" node remains; the depth-2 leaf is trimmed.
    expect(wrapper.findAll('.orb-aggr-subtree__node')).toHaveLength(1)
  })
})

describe('AggregationSubtree worst-path highlight', () => {
  it('highlights only the link to the worst leaf', () => {
    const tree = agg('root', [leaf('ok', 0), leaf('crit', 2)])
    const wrapper = render(tree)
    const worstLinks = wrapper
      .findAll('line')
      .filter((l) => l.attributes('stroke') === WORST_PATH_COLOR)
    expect(worstLinks).toHaveLength(1)
  })

  it('has no highlight when every leaf is OK', () => {
    const tree = agg('root', [leaf('a', 0), leaf('b', 0)])
    const wrapper = render(tree)
    const worstLinks = wrapper
      .findAll('line')
      .filter((l) => l.attributes('stroke') === WORST_PATH_COLOR)
    expect(worstLinks).toHaveLength(0)
  })
})

describe('AggregationSubtree node decoration', () => {
  it('writes name, state and flags into the node tooltip', () => {
    const tree = agg('root', [leaf('web01', 2, { acknowledged: true })])
    const wrapper = render(tree)
    const title = wrapper.find('.orb-aggr-subtree__node title')
    expect(title.text()).toContain('web01')
    expect(title.text()).toContain('CRITICAL')
    expect(title.text()).toContain('ack')
  })

  it('dashes the circle stroke for a node in downtime', () => {
    const tree = agg('root', [leaf('web01', 1, { in_downtime: true })])
    const wrapper = render(tree)
    const circle = wrapper.find('.orb-aggr-subtree__node circle')
    expect(circle.attributes('stroke-dasharray')).toBe('3 2')
  })
})

describe('AggregationSubtree interaction', () => {
  it('emits node-enter with a synthetic object and state on hover', async () => {
    const tree = agg('root', [leaf('web01', 2)])
    const wrapper = render(tree)
    await wrapper.find('.orb-aggr-subtree__node').trigger('mouseenter')
    const events = wrapper.emitted('node-enter')
    expect(events).toHaveLength(1)
    const [obj, state] = events![0] as [{ host_name: string }, { state: string }]
    expect(obj.host_name).toBe('web01')
    expect(state.state).toBe('CRITICAL')
  })
})
