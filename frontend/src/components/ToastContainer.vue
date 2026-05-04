<template>
    <Teleport to="body">
        <div class="fixed bottom-5 right-5 z-[200] flex flex-col gap-2 pointer-events-none">
            <TransitionGroup name="toast">
                <div
                    v-for="toast in toasts"
                    :key="toast.id"
                    class="flex items-start gap-2.5 px-4 py-3 rounded-xl shadow-xl shadow-black/40 ring-1 text-sm font-medium max-w-sm pointer-events-auto"
                    :class="
                        toast.type === 'success'
                            ? 'bg-zinc-800 ring-green-500/30 text-green-300'
                            : 'bg-zinc-800 ring-red-500/30 text-red-300'
                    "
                >
                    <svg
                        v-if="toast.type === 'success'"
                        class="w-4 h-4 shrink-0 mt-0.5 text-green-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                    <svg
                        v-else
                        class="w-4 h-4 shrink-0 mt-0.5 text-red-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                        />
                    </svg>
                    {{ toast.message }}
                </div>
            </TransitionGroup>
        </div>
    </Teleport>
</template>

<script setup lang="ts">
import { useToast } from '@/composables/useToast';

const { toasts } = useToast();
</script>

<style scoped>
.toast-enter-active {
    transition:
        opacity 0.2s ease,
        transform 0.2s ease;
}

.toast-leave-active {
    transition:
        opacity 0.25s ease,
        transform 0.25s ease;
}

.toast-enter-from {
    opacity: 0;
    transform: translateY(8px);
}

.toast-leave-to {
    opacity: 0;
    transform: translateX(16px);
}
</style>
