<template>
  <div class="breadcrumb">
    <template v-for="(item, idx) in items" :key="idx">
      <router-link v-if="item.to" :to="item.to">{{ item.title }}</router-link>
      <button v-else-if="item.onClick" type="button" class="as-link" @click="item.onClick">
        {{ item.title }}
      </button>
      <span v-else>{{ item.title }}</span>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'

export interface BreadcrumbItem {
  title: string
  to?: RouteLocationRaw
  onClick?: () => void
}

defineProps<{ items: BreadcrumbItem[] }>()
</script>

<style scoped>
.breadcrumb {
  white-space: nowrap;
  font-size: 13px;
  line-height: 1;
}

.breadcrumb > span {
  color: var(--font-color-breadcrumb-inactive);
}

.breadcrumb > a,
.breadcrumb > .as-link {
  color: var(--font-color-breadcrumb-interactive);
  text-decoration: underline;
  background: none;
  border: 0;
  padding: 0;
  font: inherit;
  cursor: pointer;
}

.breadcrumb > a:hover,
.breadcrumb > .as-link:hover {
  color: var(--font-color-breadcrumb-hover);
}

.breadcrumb > *::after {
  color: var(--font-color-breadcrumb-inactive);
  content: '>';
  cursor: default;
  display: inline-block;
  padding: 0 4px;
  text-decoration: none;
}

.breadcrumb > *:last-child::after {
  content: '';
  padding: 0;
}
</style>
