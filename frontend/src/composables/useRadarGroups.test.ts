import { describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'

import { useRadarGroups } from './useRadarGroups'

vi.mock('@/api/client', () => ({
  connectionsApi: { objects: vi.fn().mockResolvedValue([]) }
}))

function radarForm(radar_filter: string) {
  return ref({
    map_type: 'radar',
    radar_filter,
    connection_id: '',
    radar_filter_value: '',
    radar_object_filter: 'Filter: host_name ~ ^fw-'
  })
}

describe('useRadarGroups', () => {
  it('keeps the loaded Livestatus filter on open', async () => {
    const form = radarForm('all_hosts')
    useRadarGroups(form, () => null)
    await nextTick()
    expect(form.value.radar_object_filter).toBe('Filter: host_name ~ ^fw-')
  })

  it.each(['hostgroup', 'all_services'])(
    'clears the Livestatus filter when switching from all_hosts to %s',
    async (next) => {
      const form = radarForm('all_hosts')
      useRadarGroups(form, () => null)
      form.value.radar_filter = next
      await nextTick()
      expect(form.value.radar_object_filter).toBe('')
    }
  )
})
