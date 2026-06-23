import { type Ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

/**
 * Kiosk / fullscreen navigation for a map. "Enter fullscreen" routes to the
 * kiosk variant and requests the browser fullscreen API; leaving fullscreen
 * via the browser (Esc) routes back to the normal map. Opening kiosk in a
 * new tab uses a transient anchor so it isn't blocked as a popup.
 *
 * The fullscreenchange listener is registered/removed automatically.
 */
export function useMapFullscreen(mapName: Ref<string>, isKiosk: Ref<boolean>) {
  const router = useRouter()

  function openKioskInNewTab(): void {
    const url = router.resolve({ name: 'map-kiosk', params: { name: mapName.value } }).href
    const a = document.createElement('a')
    a.href = url
    a.target = '_blank'
    a.rel = 'noreferrer'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  function enterFullscreen(): void {
    router.push({ name: 'map-kiosk', params: { name: mapName.value } })
    document.documentElement.requestFullscreen().catch(() => {})
  }

  function exitFullscreen(): void {
    router.push({ name: 'map', params: { name: mapName.value } })
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {})
  }

  function onFullscreenChange(): void {
    if (!document.fullscreenElement && isKiosk.value) {
      router.push({ name: 'map', params: { name: mapName.value } })
    }
  }

  onMounted(() => document.addEventListener('fullscreenchange', onFullscreenChange))
  onUnmounted(() => document.removeEventListener('fullscreenchange', onFullscreenChange))

  return { openKioskInNewTab, enterFullscreen, exitFullscreen }
}
