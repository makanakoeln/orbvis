import { computed, reactive } from 'vue'

import { useHoverGrace } from '@/composables/useHoverGrace'
import { useStatesStore } from '@/stores/states'
import type { BoardObject, ObjectState } from '@/types/api'

export interface HoverAnchorRect {
  left: number
  top: number
  right: number
  bottom: number
}

interface OpenOptions {
  /** Explicit page position; defaults to the event's cursor + 12px offset. */
  x?: number
  y?: number
  /** Anchor box for the viewport flip — when the card has to flip away from
   * a screen edge it docks on this rect instead of covering the object.
   * `null` disables (lines span the whole board); omitted = derived from
   * the event target. */
  anchorRect?: HoverAnchorRect | null
  /** Explicit state for objects that have no entry in the states store
   * (BI subtree nodes, foldertree leaves). */
  stateOverride?: ObjectState | null
}

interface HoverMenuOptions {
  /** Live state resolver for the hovered object — re-evaluated reactively so
   * an open card keeps ticking. Default: states-store lookup by object id. */
  resolveState?: (obj: BoardObject) => ObjectState | undefined
  /** Invoked whenever the card closes (grace or programmatic) so hosts can
   * drop their own per-hover context (e.g. the flow board's hovered node). */
  onClose?: () => void
}

/**
 * The shared hover-card state machine behind every board type's HoverMenu:
 * position, anchor rect, close grace and live state resolution. Boards only
 * decide *what* a hoverable object is (and how it renders) — what happens on
 * hover is the same contract everywhere.
 *
 * Wire-up:
 *   object @hover        -> open(obj, event)
 *   object @hover-leave  -> scheduleClose()
 *   HoverMenu @card-enter -> cancelClose()
 *   HoverMenu @card-leave -> scheduleClose()
 *   programmatic exits (context menu, click-to-open) -> close()
 */
export function useObjectHoverMenu(options: HoverMenuOptions = {}) {
  const statesStore = useStatesStore()

  const hover = reactive({
    visible: false,
    object: null as BoardObject | null,
    x: 0,
    y: 0,
    anchorRect: null as HoverAnchorRect | null,
    stateOverride: null as ObjectState | null
  })

  const grace = useHoverGrace(() => {
    hover.visible = false
    hover.object = null
    hover.stateOverride = null
    options.onClose?.()
  })

  const state = computed<ObjectState | undefined>(() => {
    const obj = hover.object
    if (!obj) return undefined
    if (hover.stateOverride) return hover.stateOverride
    return options.resolveState ? options.resolveState(obj) : statesStore.states[obj.id]
  })

  function open(obj: BoardObject, event: MouseEvent | null, opts: OpenOptions = {}): void {
    grace.cancelClose()
    hover.object = obj
    hover.x = opts.x ?? (event ? event.pageX + 12 : hover.x)
    hover.y = opts.y ?? (event ? event.pageY + 12 : hover.y)
    hover.anchorRect =
      opts.anchorRect !== undefined
        ? opts.anchorRect
        : obj.type === 'line'
          ? null
          : findIconWrapperRect(event?.target ?? null)
    hover.stateOverride = opts.stateOverride ?? null
    hover.visible = true
  }

  function close(): void {
    grace.cancelClose()
    hover.visible = false
    hover.object = null
    hover.stateOverride = null
    options.onClose?.()
  }

  return {
    hover,
    state,
    open,
    close,
    scheduleClose: grace.scheduleClose,
    cancelClose: grace.cancelClose
  }
}

/** Walk up from an event target to the icon-sized wrapper of the hovered
 * object. Icon wrappers are roughly square and small — a real icon plus its
 * label tops out around 100×100 px; anything larger is a container.
 * `event.currentTarget` is already null by the time Vue's emit bridge runs,
 * so callers hand in `event.target`. */
function findIconWrapperRect(target: EventTarget | null): HoverAnchorRect | null {
  let el = target instanceof Element ? target : null
  while (el && el !== document.body) {
    const r = el.getBoundingClientRect()
    if (r.width > 0 && r.width < 200 && r.height > 0 && r.height < 200) {
      return { left: r.left, top: r.top, right: r.right, bottom: r.bottom }
    }
    el = el.parentElement
  }
  return null
}
