import type { BoardObject } from '@/types/api'
import { type BindableElement, hasBinding } from '@/utils/presentationSampleState'

/**
 * Expose a bound presentation element as a transient BoardObject so the
 * shared view-mode surfaces (HoverMenu, DetailDrawer) work on presentation
 * boards without knowing about the element model. The id matches the
 * element's id, which is also the key of its entry in the states store.
 */
export function boardObjectFromElement(el: BindableElement): BoardObject | null {
  if (!hasBinding(el)) return null
  const type: BoardObject['type'] = el.aggregation_id
    ? 'aggregation'
    : el.group_name
      ? el.object_type === 'servicegroup'
        ? 'servicegroup'
        : 'hostgroup'
      : el.service_description
        ? 'service'
        : 'host'
  return {
    id: el.id,
    type,
    x: 0,
    y: 0,
    host_name: el.host_name ?? null,
    service_description: el.service_description ?? null,
    group_name: el.group_name ?? null,
    aggregation_id: el.aggregation_id ?? null,
    connection_id: el.connection_id ?? null,
    only_hard_states: el.only_hard_states ?? false,
    url_target: '_blank'
  }
}
