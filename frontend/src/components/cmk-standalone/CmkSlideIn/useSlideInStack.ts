/**
 * OrbVis-native slide-in stack helper, used by the standalone CmkSlideIn.
 * Mirrors the upstream priority/order semantics so nested slide-ins behave
 * identically across build modes.
 */
import { computed, type Ref, ref } from 'vue';

type StackEntry = { id: string; priority: number; order: number };

const openStack = ref<StackEntry[]>([]);
let idCounter = 0;
let orderCounter = 0;

function removeFromStack(id: string) {
    const index = openStack.value.findIndex((entry) => entry.id === id);
    if (index >= 0) openStack.value.splice(index, 1);
}

function sortStack() {
    openStack.value.sort((a, b) =>
        a.priority !== b.priority ? a.priority - b.priority : a.order - b.order,
    );
}

export function useSlideInStack(stackPriority?: number | null): {
    instanceId: string;
    isTopMost: Ref<boolean>;
    register: () => void;
    unregister: () => void;
} {
    const instanceId = `orb-slide-in-${++idCounter}`;
    const priority = stackPriority ?? 0;
    const isTopMost = computed(
        () => openStack.value[openStack.value.length - 1]?.id === instanceId,
    );

    function register() {
        removeFromStack(instanceId);
        openStack.value.push({ id: instanceId, priority, order: ++orderCounter });
        sortStack();
    }

    function unregister() {
        removeFromStack(instanceId);
    }

    return { instanceId, isTopMost, register, unregister };
}
