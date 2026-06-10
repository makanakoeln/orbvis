import { type Ref, computed, ref } from 'vue'

import { useHoverGrace } from '@/composables/useHoverGrace'
import { useStatesStore } from '@/stores/states'
import type { BoardObject, FolderTreeNode, MonitoringState, ObjectState } from '@/types/api'
import { stripCheckmkBase } from '@/utils/boardNavigation'

interface FolderHover {
  object: BoardObject
  state: ObjectState | undefined
  x: number
  y: number
}

interface FolderCtx {
  node: FolderTreeNode
  x: number
  y: number
}

interface FolderTreeOptions {
  isPreview: Ref<boolean>
  checkmkUrl: Ref<string | null>
  canBulkCommand: Ref<boolean>
  isClickActionNone: () => boolean
  onObjectClick: (obj: BoardObject) => void
  setDrawerSeed: (state: ObjectState) => void
}

/**
 * Hover popup, folder context menu and bulk-action modal for the foldertree
 * board. Foldertree leaves never enter the SSE state map (services are lazy,
 * the flat host list is empty by design), so each interaction synthesises an
 * ObjectState from the tree node via {@link folderNodeToState}.
 *
 * Selecting a leaf seeds the drawer (`setDrawerSeed`) and opens it through the
 * shared `onObjectClick`; both are injected because the drawer lives in the
 * host view.
 */
export function useFolderTreeInteractions(options: FolderTreeOptions) {
  const { isPreview, checkmkUrl, canBulkCommand, isClickActionNone, onObjectClick, setDrawerSeed } =
    options
  const statesStore = useStatesStore()

  // Synthesise an ObjectState from a tree node for the hover/drawer. Pass
  // `host` for a service leaf, omit for a host.
  function folderNodeToState(node: FolderTreeNode, host?: string): ObjectState {
    const isService = host !== undefined
    return {
      object_id: isService ? `${host};${node.title}` : node.title,
      type: isService ? 'service' : 'host',
      state: node.state as MonitoringState,
      output: node.output,
      perf_data: '',
      acknowledged: node.acknowledged,
      in_downtime: node.in_downtime,
      stale: false,
      site_id: node.site_id,
      last_state_change: node.last_state_change ?? null,
      services_summary: node.services_summary ?? null
    }
  }

  function onFolderHostSelect(node: FolderTreeNode): void {
    if (isPreview.value) return
    if (node.kind !== 'host') return
    setDrawerSeed(folderNodeToState(node))
    onObjectClick({
      id: node.title,
      type: 'host',
      host_name: node.title,
      x: 0,
      y: 0,
      z: 0,
      url_target: '_blank'
    })
  }

  function onFolderServiceSelect(host: string, node: FolderTreeNode): void {
    if (isPreview.value) return
    // The drawer self-fetches the richer detail (long output, comments,
    // downtimes) by host + service on top of this node-derived state.
    const id = `${host};${node.title}`
    setDrawerSeed(folderNodeToState(node, host))
    onObjectClick({
      id,
      type: 'service',
      host_name: host,
      service_description: node.title,
      x: 0,
      y: 0,
      z: 0,
      url_target: '_blank'
    })
  }

  const folderBulkModal = ref<FolderTreeNode | null>(null)
  function onFolderAction(node: FolderTreeNode): void {
    if (!canBulkCommand.value) return
    folderBulkModal.value = node
  }

  const folderHover = ref<FolderHover | null>(null)

  function onFolderHoverHost(node: FolderTreeNode, x: number, y: number): void {
    folderHoverGrace.cancelClose()
    folderHover.value = {
      object: {
        id: node.title,
        type: 'host',
        host_name: node.title,
        x: 0,
        y: 0,
        z: 0,
        url_target: '_blank'
      },
      state: folderNodeToState(node),
      x: x + 12,
      y: y + 12
    }
  }

  function onFolderHoverService(host: string, node: FolderTreeNode, x: number, y: number): void {
    folderHoverGrace.cancelClose()
    const id = `${host};${node.title}`
    folderHover.value = {
      object: {
        id,
        type: 'service',
        host_name: host,
        service_description: node.title,
        x: 0,
        y: 0,
        z: 0,
        url_target: '_blank'
      },
      state: folderNodeToState(node, host),
      x: x + 12,
      y: y + 12
    }
  }

  const folderHoverGrace = useHoverGrace(() => {
    folderHover.value = null
  })

  function onFolderHoverClear(): void {
    folderHoverGrace.scheduleClose()
  }

  const folderCtx = ref<FolderCtx | null>(null)

  function onFolderCtx(node: FolderTreeNode, x: number, y: number): void {
    // The settings preview is non-interactive; read-only displays (click_action
    // 'none') get no context menu, mirroring onObjectClick's click gating.
    if (isPreview.value || isClickActionNone()) return
    folderHover.value = null
    folderCtx.value = { node, x, y }
  }

  function closeFolderCtx(): void {
    folderCtx.value = null
  }

  function onFolderCtxBulk(): void {
    if (folderCtx.value) onFolderAction(folderCtx.value.node)
    closeFolderCtx()
  }

  // wato.py addresses folders by their relative path (Main = ""), which is the
  // tree node's path.
  const folderSetupUrl = computed(() => {
    const node = folderCtx.value?.node
    if (!node) return null
    const raw = checkmkUrl.value
    if (!raw) return null
    const base = stripCheckmkBase(raw)
    const p = new URLSearchParams({ mode: 'folder', folder: node.path })
    return `${base}/check_mk/wato.py?${p.toString()}`
  })

  function closeFolderBulkModal(): void {
    folderBulkModal.value = null
    statesStore.refreshAfterCommand()
  }

  return {
    folderHover,
    folderHoverGrace,
    folderCtx,
    folderBulkModal,
    folderSetupUrl,
    onFolderHostSelect,
    onFolderServiceSelect,
    onFolderHoverHost,
    onFolderHoverService,
    onFolderHoverClear,
    onFolderCtx,
    closeFolderCtx,
    onFolderCtxBulk,
    closeFolderBulkModal
  }
}
