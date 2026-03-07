<template>
  <div class="absolute inset-0 overflow-auto bg-zinc-950">
    <div v-if="loading" class="flex items-center justify-center h-full text-zinc-500 text-sm">Loading topology…</div>
    <div v-else-if="error" class="flex items-center justify-center h-full text-red-400 text-sm">{{ error }}</div>
    <svg v-else :width="canvasW" :height="canvasH" class="block">
      <!-- Edges -->
      <g v-for="edge in edges" :key="edge.key">
        <line
          :x1="edge.x1" :y1="edge.y1" :x2="edge.x2" :y2="edge.y2"
          :stroke="stateColor(edge.parentState)"
          stroke-width="1.5"
          stroke-opacity="0.5"
        />
      </g>
      <!-- Nodes -->
      <g v-for="node in layoutNodes" :key="node.name"
        style="cursor: default"
        @click="onNodeClick(node)">
        <!-- Circle -->
        <circle
          :cx="node.x" :cy="node.y" :r="NODE_R"
          :fill="stateColor(node.state)"
          :class="node.state === 'DOWN' || node.state === 'CRITICAL' ? 'node-pulse' : ''"
          stroke="rgba(0,0,0,0.4)" stroke-width="1.5"
        />
        <!-- Label -->
        <text
          :x="node.x" :y="node.y + NODE_R + 14"
          text-anchor="middle"
          font-size="11"
          font-weight="500"
          fill="#e4e4e7"
          style="text-shadow: 0 1px 3px rgba(0,0,0,0.9)"
        >{{ node.name }}</text>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import type { TopologyNode } from '@/types/api'
import { backendsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{
  backendId: string
}>()

const auth = useAuthStore()

const NODE_R = 18
const H_GAP = 160
const V_GAP = 110
const PADDING = 80

const nodes = ref<TopologyNode[]>([])
const loading = ref(true)
const error = ref('')
let timer: ReturnType<typeof setInterval> | null = null

async function fetchTopology() {
  try {
    nodes.value = await backendsApi.topology(props.backendId, auth.accessToken!)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load topology'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchTopology()
  timer = setInterval(fetchTopology, 15000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })

// BFS layout
interface LayoutNode extends TopologyNode { x: number; y: number }

const layoutNodes = computed<LayoutNode[]>(() => {
  const all = nodes.value
  if (!all.length) return []
  const nameSet = new Set(all.map(n => n.name))
  // Assign levels via BFS from roots
  const levels = new Map<string, number>()
  const roots = all.filter(n => !n.parents.length || n.parents.every(p => !nameSet.has(p)))
  const queue: string[] = roots.map(r => r.name)
  roots.forEach(r => levels.set(r.name, 0))
  while (queue.length) {
    const name = queue.shift()!
    const lvl = levels.get(name)!
    for (const n of all) {
      if (n.parents.includes(name) && !levels.has(n.name)) {
        levels.set(n.name, lvl + 1)
        queue.push(n.name)
      }
    }
  }
  // Nodes not reached → put at bottom
  all.filter(n => !levels.has(n.name)).forEach((n, i) => levels.set(n.name, (Math.max(0, ...levels.values()) + 1) + Math.floor(i / 5)))

  // Group by level
  const byLevel = new Map<number, string[]>()
  for (const [name, lvl] of levels) {
    if (!byLevel.has(lvl)) byLevel.set(lvl, [])
    byLevel.get(lvl)!.push(name)
  }

  // Compute positions
  const positions = new Map<string, { x: number; y: number }>()
  const maxWidth = Math.max(...[...byLevel.values()].map(v => v.length))
  for (const [lvl, names] of byLevel) {
    const totalW = (names.length - 1) * H_GAP
    names.forEach((name, i) => {
      positions.set(name, {
        x: PADDING + i * H_GAP - totalW / 2 + (maxWidth * H_GAP) / 2,
        y: PADDING + lvl * V_GAP,
      })
    })
  }

  return all.map(n => ({ ...n, ...(positions.get(n.name) ?? { x: PADDING, y: PADDING }) }))
})

const edges = computed(() => {
  const nodeMap = new Map(layoutNodes.value.map(n => [n.name, n]))
  const result: { key: string; x1: number; y1: number; x2: number; y2: number; parentState: string }[] = []
  for (const n of layoutNodes.value) {
    for (const p of n.parents) {
      const parent = nodeMap.get(p)
      if (parent) {
        result.push({ key: `${p}→${n.name}`, x1: parent.x, y1: parent.y, x2: n.x, y2: n.y, parentState: parent.state })
      }
    }
  }
  return result
})

const canvasW = computed(() => {
  if (!layoutNodes.value.length) return 800
  return Math.max(800, Math.max(...layoutNodes.value.map(n => n.x)) + PADDING + NODE_R + 60)
})
const canvasH = computed(() => {
  if (!layoutNodes.value.length) return 600
  return Math.max(400, Math.max(...layoutNodes.value.map(n => n.y)) + PADDING + NODE_R + 30)
})

function stateColor(state: string): string {
  const map: Record<string, string> = {
    UP: '#22c55e', OK: '#22c55e',
    DOWN: '#ef4444', CRITICAL: '#ef4444',
    UNREACHABLE: '#f97316', UNKNOWN: '#f97316',
    WARNING: '#f59e0b',
  }
  return map[state] ?? '#6b7280'
}

function onNodeClick(node: LayoutNode) {
  // Future: show detail / open checkmk
}
</script>

<style scoped>
@keyframes node-pulse {
  0%, 100% { filter: drop-shadow(0 0 4px rgba(239,68,68,0.5)); }
  50%       { filter: drop-shadow(0 0 12px rgba(239,68,68,0.9)); }
}
.node-pulse { animation: node-pulse 1.8s ease-in-out infinite; }
</style>
