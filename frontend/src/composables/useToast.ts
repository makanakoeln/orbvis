import { ref } from 'vue';

export type ToastType = 'success' | 'error';

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

const toasts = ref<Toast[]>([]);
let _nextId = 0;

export function useToast() {
  function show(type: ToastType, message: string, duration = 3500): void {
    const id = _nextId++;
    toasts.value.push({ id, type, message });
    setTimeout(() => {
      const idx = toasts.value.findIndex((t) => t.id === id);
      if (idx !== -1) toasts.value.splice(idx, 1);
    }, duration);
  }

  return {
    toasts,
    success: (msg: string) => show('success', msg),
    error: (msg: string) => show('error', msg, 5000),
  };
}
