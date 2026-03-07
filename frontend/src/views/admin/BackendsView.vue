<template>
  <div>
    <div class="flex justify-between items-center mb-8">
      <div>
        <h2 class="text-xl font-bold text-zinc-100 tracking-tight">Monitoring Backends</h2>
        <p class="text-sm text-zinc-500 mt-1">Configure connections to monitoring systems</p>
      </div>
      <button @click="openCreate"
        class="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition-all duration-150 shadow-lg shadow-indigo-900/20">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        Add Backend
      </button>
    </div>

    <div v-if="store.loading" class="flex items-center gap-2 text-zinc-500 text-sm py-8 justify-center">
      <svg class="animate-spin w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      Loading…
    </div>

    <div v-else-if="store.error" class="px-4 py-3 bg-red-500/8 ring-1 ring-red-500/20 rounded-xl text-red-400 text-sm">
      {{ store.error }}
    </div>

    <div v-else-if="store.backends.length === 0"
      class="text-center py-16 bg-zinc-900 ring-1 ring-white/5 rounded-xl">
      <p class="text-zinc-500 text-sm">No backends configured</p>
      <p class="text-zinc-600 text-xs mt-1">Add a backend to receive monitoring states</p>
    </div>

    <div v-else class="bg-zinc-900 ring-1 ring-white/5 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-white/5">
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Status</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">ID</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Label</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Type</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Connection</th>
            <th class="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-zinc-800">
          <tr v-for="b in store.backends" :key="b.id" class="hover:bg-zinc-800/40 transition-colors">
            <!-- Status -->
            <td class="px-4 py-3">
              <button @click="testExisting(b.id)" :disabled="statusLoading[b.id]"
                class="flex items-center gap-2 group" title="Click to retest">
                <span class="relative flex">
                  <span v-if="statusLoading[b.id]" class="w-2.5 h-2.5 rounded-full bg-zinc-500 animate-pulse" />
                  <span v-else-if="statuses[b.id] === undefined" class="w-2.5 h-2.5 rounded-full bg-zinc-600" />
                  <span v-else-if="statuses[b.id]"
                    class="w-2.5 h-2.5 rounded-full bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.6)]" />
                  <span v-else class="w-2.5 h-2.5 rounded-full bg-red-400" />
                </span>
                <span class="text-xs text-zinc-600 group-hover:text-zinc-400 transition-colors">
                  {{ statusLoading[b.id] ? 'Testing…' : statusMessages[b.id] ?? 'Test' }}
                </span>
              </button>
            </td>
            <td class="px-4 py-3 font-mono text-xs text-zinc-400">{{ b.id }}</td>
            <td class="px-4 py-3 text-zinc-300">{{ b.label || '—' }}</td>
            <td class="px-4 py-3">
              <span class="text-xs px-2 py-0.5 rounded-full font-medium ring-1"
                :class="b.type === 'livestatus'
                  ? 'bg-indigo-500/10 text-indigo-400 ring-indigo-500/20'
                  : 'bg-zinc-700/50 text-zinc-500 ring-zinc-700'">
                {{ b.type }}
              </span>
            </td>
            <td class="px-4 py-3 text-zinc-600 font-mono text-xs">
              <template v-if="b.type === 'livestatus'">
                {{ b.socket_path || `${b.host}:${b.port}` }}
              </template>
              <span v-else class="text-zinc-700">built-in</span>
            </td>
            <td class="px-4 py-3 text-right">
              <div class="flex items-center justify-end gap-3">
                <button @click="openEdit(b)" class="text-xs text-zinc-500 hover:text-indigo-400 transition-colors">Edit</button>
                <button @click="remove(b.id)" class="text-xs text-zinc-600 hover:text-red-400 transition-colors">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create / Edit dialog -->
    <Teleport to="body">
      <div v-if="dialog.open" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="dialog.open = false" />
        <div class="relative bg-zinc-900 ring-1 ring-white/10 shadow-2xl shadow-black/50 rounded-2xl p-6 w-[30rem] max-h-[90vh] overflow-y-auto">
          <div class="flex items-center justify-between mb-5">
            <h3 class="text-base font-bold text-zinc-100">
              {{ dialog.mode === 'create' ? 'Add Backend' : 'Edit Backend' }}
            </h3>
            <button @click="dialog.open = false"
              class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-all">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          <form @submit.prevent="save" class="space-y-4">
            <div v-if="dialog.mode === 'create'" class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                Backend ID <span class="normal-case font-normal text-zinc-600">(no spaces)</span>
              </label>
              <input v-model="form.id" required pattern="[a-zA-Z0-9_-]+" placeholder="cmk_heute"
                class="w-full px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            </div>

            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Display label</label>
              <input v-model="form.label" placeholder="Checkmk heute"
                class="w-full px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            </div>

            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Type</label>
              <select v-model="form.type"
                class="w-full px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
                <option value="livestatus">MK Livestatus</option>
                <option value="test">Test (built-in demo)</option>
              </select>
            </div>

            <template v-if="form.type === 'livestatus'">
              <div class="space-y-1.5">
                <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  Unix socket path <span class="normal-case font-normal text-zinc-600">or use TCP below</span>
                </label>
                <input v-model="form.socket_path" placeholder="/omd/sites/heute/tmp/run/live"
                  class="w-full px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
              </div>

              <div class="grid grid-cols-3 gap-3">
                <div class="col-span-2 space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">TCP host</label>
                  <input v-model="form.host" placeholder="192.168.1.10"
                    class="w-full px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
                </div>
                <div class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Port</label>
                  <input v-model.number="form.port" type="number" min="1" max="65535"
                    class="w-full px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
                </div>
              </div>

              <div class="grid grid-cols-3 gap-3 items-end">
                <div class="col-span-2 space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Checkmk URL <span class="normal-case font-normal text-zinc-600">for context links</span></label>
                  <input v-model="form.checkmk_url" placeholder="http://localhost/heute"
                    class="w-full px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
                </div>
                <div class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Timeout (s)</label>
                  <input v-model.number="form.timeout" type="number" min="1" max="120" step="0.5"
                    class="w-full px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
                </div>
              </div>
            </template>

            <!-- Test result -->
            <div v-if="dialogTest.ran"
              class="flex items-start gap-2.5 px-3.5 py-3 rounded-lg ring-1 text-sm"
              :class="dialogTest.ok
                ? 'bg-green-500/8 ring-green-500/20 text-green-400'
                : 'bg-red-500/8 ring-red-500/20 text-red-400'">
              <span class="w-2 h-2 rounded-full shrink-0 mt-1"
                :class="dialogTest.ok ? 'bg-green-400' : 'bg-red-400'" />
              {{ dialogTest.message }}
            </div>

            <p v-if="formError" class="text-red-400 text-xs flex items-center gap-1">
              <svg class="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" /></svg>
              {{ formError }}
            </p>

            <div class="flex gap-2 justify-end pt-2 border-t border-white/5">
              <button type="button" @click="dialog.open = false"
                class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-all">Cancel</button>
              <button type="button" @click="testDialog" :disabled="dialogTest.loading"
                class="px-4 py-2 ring-1 ring-zinc-700 hover:ring-zinc-500 rounded-lg text-sm text-zinc-300 hover:text-zinc-100 disabled:opacity-50 transition-all">
                {{ dialogTest.loading ? 'Testing…' : 'Test' }}
              </button>
              <button type="submit" :disabled="saving"
                class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-all">
                {{ saving ? 'Saving…' : 'Save' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useBackendsStore } from '@/stores/backends'
import { backendsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { BackendConfig } from '@/types/api'

const store = useBackendsStore()
const auth = useAuthStore()

const statuses = reactive<Record<string, boolean>>({})
const statusMessages = reactive<Record<string, string>>({})
const statusLoading = reactive<Record<string, boolean>>({})

async function testExisting(id: string) {
  statusLoading[id] = true
  try {
    const result = await backendsApi.test(id, auth.accessToken!)
    statuses[id] = result.ok
    statusMessages[id] = result.message
  } catch (e: unknown) {
    statuses[id] = false
    statusMessages[id] = e instanceof Error ? e.message : 'Error'
  } finally {
    statusLoading[id] = false
  }
}

async function testAll() {
  for (const b of store.backends) testExisting(b.id)
}

const dialog = reactive({ open: false, mode: 'create' as 'create' | 'edit', editId: '' })
const saving = ref(false)
const formError = ref('')
const dialogTest = reactive({ loading: false, ran: false, ok: false, message: '' })

const emptyForm = (): BackendConfig => ({
  id: '', type: 'livestatus', label: '',
  socket_path: null, host: null, port: 6557, timeout: 10, checkmk_url: null,
})
const form = reactive<BackendConfig>(emptyForm())

function openCreate() {
  Object.assign(form, emptyForm())
  Object.assign(dialogTest, { loading: false, ran: false, ok: false, message: '' })
  formError.value = ''
  dialog.mode = 'create'
  dialog.open = true
}

function openEdit(b: BackendConfig) {
  Object.assign(form, { ...b })
  Object.assign(dialogTest, { loading: false, ran: false, ok: false, message: '' })
  formError.value = ''
  dialog.mode = 'edit'
  dialog.editId = b.id
  dialog.open = true
}

async function testDialog() {
  dialogTest.loading = true
  dialogTest.ran = false
  try {
    const result = await backendsApi.testConnection({ ...form }, auth.accessToken!)
    dialogTest.ok = result.ok
    dialogTest.message = result.message
    dialogTest.ran = true
  } catch (e: unknown) {
    dialogTest.ok = false
    dialogTest.message = e instanceof Error ? e.message : 'Error'
    dialogTest.ran = true
  } finally {
    dialogTest.loading = false
  }
}

async function save() {
  formError.value = ''
  saving.value = true
  try {
    if (dialog.mode === 'create') {
      await store.createBackend({ ...form })
    } else {
      const { id: _id, ...rest } = form
      await store.updateBackend(dialog.editId, rest)
    }
    dialog.open = false
    testAll()
  } catch (e: unknown) {
    formError.value = e instanceof Error ? e.message : 'Save failed'
  } finally {
    saving.value = false
  }
}

async function remove(id: string) {
  if (!confirm(`Delete backend "${id}"?`)) return
  await store.deleteBackend(id)
  delete statuses[id]
  delete statusMessages[id]
}

onMounted(async () => {
  await store.fetchBackends()
  testAll()
})
</script>
