<template>
    <div class="board-search">
        <svg
            style="width: 12px; height: 12px"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
            class="text-zinc-400 shrink-0"
        >
            <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 105.62 5.62a7.5 7.5 0 0011.03 11.03z"
            />
        </svg>
        <input
            v-model="local"
            :placeholder="placeholder ?? t('board.flow.searchPlaceholder')"
            type="search"
            class="board-search__input"
            :aria-label="placeholder ?? t('board.flow.searchPlaceholder')"
        />
        <button v-if="local" type="button" class="board-search__clear" @click="local = ''">
            ×
        </button>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps<{ modelValue: string; placeholder?: string }>();
const emit = defineEmits<{ 'update:modelValue': [string] }>();

const { t } = useI18n();

const local = computed({
    get: () => props.modelValue,
    set: (v: string) => emit('update:modelValue', v),
});
</script>

<style scoped>
.board-search {
    position: absolute;
    top: var(--dimension-5);
    right: var(--dimension-5);
    z-index: 6;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    border-radius: var(--border-radius);
    background: rgb(24 24 27 / 85%);
    border: 1px solid var(--border);
    backdrop-filter: blur(6px);
    min-width: 200px;
}

.board-search__input {
    flex: 1;
    min-width: 0;
    background: transparent;
    border: none;
    outline: none;
    color: var(--text);
    font-size: 12px;
}

.board-search__input::placeholder {
    color: var(--zinc-500, #71717a);
}

.board-search__clear {
    background: transparent;
    border: none;
    color: var(--zinc-500, #71717a);
    cursor: pointer;
    font-size: 16px;
    line-height: 1;
    padding: 0 2px;
}

.board-search__clear:hover {
    color: var(--text);
}
</style>
