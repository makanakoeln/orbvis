<template>
  <Teleport to="body">
    <div class="orb-toasts">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="orb-toast"
          :class="toast.type === 'success' ? 'orb-toast--success' : 'orb-toast--error'"
        >
          <svg
            v-if="toast.type === 'success'"
            class="orb-toast__icon"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          <svg
            v-else
            class="orb-toast__icon"
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
          <span>{{ toast.message }}</span>
          <button
            v-if="toast.action"
            type="button"
            class="orb-toast__action"
            @click="toast.action.onClick()"
          >
            {{ toast.action.label }}
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useToast } from '@/composables/useToast'

const { toasts } = useToast()
</script>

<style scoped>
.orb-toasts {
  position: fixed;
  right: var(--dimension-7);
  bottom: var(--dimension-7);
  z-index: 200;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  pointer-events: none;
}

.orb-toast {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  max-width: 384px;
  padding: 12px 16px;
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 500;
  background: var(--bg-surface);
  border-radius: 12px;
  pointer-events: auto;
}

.orb-toast--success {
  color: var(--color-corporate-green-50);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 30%, transparent),
    0 20px 25px -5px rgb(0 0 0 / 40%),
    0 8px 10px -6px rgb(0 0 0 / 40%);
}

.orb-toast--error {
  color: var(--color-light-red-40);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--color-light-red-50) 30%, transparent),
    0 20px 25px -5px rgb(0 0 0 / 40%),
    0 8px 10px -6px rgb(0 0 0 / 40%);
}

.orb-toast__icon {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  margin-top: 2px;
}

.orb-toast__action {
  margin-left: var(--dimension-3);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.orb-toast__action:hover {
  text-decoration: none;
}

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
