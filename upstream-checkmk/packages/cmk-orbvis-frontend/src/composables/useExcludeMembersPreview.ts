import { computed, ref, watch } from 'vue'

import { connectionsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { AggregationNode } from '@/types/api'
import {
  BI_STATE_LABEL,
  aggregationLeafId,
  flattenAggregationLeaves
} from '@/utils/aggregationTree'
import { compileRegex } from '@/utils/regex'
import usei18n from '@cmk/lib/i18n'

interface ExcludeMembersPreviewOptions {
  connectionId: () => string
  aggregationId: () => string
  excludeMembers: () => string
  excludeMemberStates: () => string
}

/**
 * Live "N of M leaves hidden" preview for the BI `exclude_members` filter. The
 * aggregation tree is fetched once per aggregation id (depth 10 = the API cap,
 * so the count reflects every leaf), then the suppression count recomputes
 * locally as the operator types the member regex / state list — no per-keystroke
 * round-trip. A leaf is suppressed when every *defined* filter matches it.
 */
export function useExcludeMembersPreview(options: ExcludeMembersPreviewOptions) {
  const { connectionId, aggregationId, excludeMembers, excludeMemberStates } = options
  const auth = useAuthStore()
  const { _t } = usei18n()

  const excludeMembersTree = ref<AggregationNode | null>(null)

  watch(
    () => [aggregationId(), connectionId()] as const,
    async ([aggId, cid]) => {
      if (!aggId || !cid || !auth.accessToken) {
        excludeMembersTree.value = null
        return
      }
      try {
        // Fixed depth=10 = the API cap; "every leaf" guarantees the
        // count reflects the full aggregation, not just the
        // currently-displayed subtree.
        const result = await connectionsApi.aggregationTree(cid, aggId, 10, auth.accessToken)
        excludeMembersTree.value = result.tree
      } catch {
        excludeMembersTree.value = null
      }
    },
    { immediate: true }
  )

  const excludeMembersFeedback = computed<{ text: string; tone: string } | null>(() => {
    const tree = excludeMembersTree.value
    if (!tree) return null
    const memberRe = (excludeMembers() || '').trim()
    const stateList = (excludeMemberStates() || '')
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean)
    if (!memberRe && stateList.length === 0) return null

    let regex: RegExp | null = null
    if (memberRe) {
      try {
        // Pattern is operator-typed and only used to test against the
        // already-fetched leaves array — no server round-trip and no
        // unbounded input source. compileRegex centralises the eslint
        // tradeoff for security/detect-non-literal-regexp so we can
        // keep using the standard linter elsewhere.
        regex = compileRegex(memberRe)
      } catch {
        return {
          text: _t('Invalid regular expression.'),
          tone: 'orb-props__feedback--invalid'
        }
      }
    }

    const leaves = flattenAggregationLeaves(tree)
    const total = leaves.length
    let suppressed = 0
    for (const l of leaves) {
      const key = aggregationLeafId(l)
      const matchesMember = regex ? regex.test(key) : true
      const matchesState = stateList.length
        ? stateList.includes(BI_STATE_LABEL[l.state] ?? '')
        : true
      // exclude when BOTH (or only-defined) filters match the leaf.
      const memberApplies = !!regex
      const stateApplies = stateList.length > 0
      if (
        (memberApplies && stateApplies && matchesMember && matchesState) ||
        (memberApplies && !stateApplies && matchesMember) ||
        (!memberApplies && stateApplies && matchesState)
      ) {
        suppressed += 1
      }
    }

    if (suppressed === 0) {
      return {
        text: _t('0 of %{total} leaves hidden — filter matches nothing.', { total }),
        tone: 'orb-props__feedback--muted'
      }
    }
    if (suppressed >= total) {
      return {
        text: _t('All %{count} leaves would be hidden — the filter is too broad.', {
          count: suppressed,
          total
        }),
        tone: 'orb-props__feedback--warn'
      }
    }
    return {
      text: _t('%{count} of %{total} leaves will be hidden.', { count: suppressed, total }),
      tone: 'orb-props__feedback--matched'
    }
  })

  return { excludeMembersFeedback }
}
