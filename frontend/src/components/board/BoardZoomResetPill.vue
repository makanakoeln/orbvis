<template>
    <Teleport to="body">
        <button
            v-if="visible"
            type="button"
            class="board-zoom-reset"
            title="Reset to fit"
            @click="$emit('reset')"
        >
            {{ Math.round(zoom * 100) }}% ↺
        </button>
    </Teleport>
</template>

<script setup lang="ts">
defineProps<{
    zoom: number;
    visible: boolean;
}>();
defineEmits<{ reset: [] }>();
</script>

<style scoped>
.board-zoom-reset {
    position: fixed;
    bottom: var(--dimension-5);
    left: var(--dimension-5);
    z-index: 6;
    padding: 6px 14px;
    border-radius: var(--border-radius);
    background: rgb(24 24 27 / 85%);
    border: 1px solid var(--border);
    color: var(--text);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    backdrop-filter: blur(6px);
}

.board-zoom-reset:hover {
    border-color: var(--color-corporate-green-50);
}
</style>
