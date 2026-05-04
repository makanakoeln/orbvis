<template>
    <div ref="el" class="w-full h-full" />
</template>

<script setup lang="ts">
import 'leaflet/dist/leaflet.css';

import L from 'leaflet';
import { onMounted, onUnmounted, ref, watch } from 'vue';

const props = defineProps<{
    lat: number;
    lng: number;
    zoom: number;
}>();

const el = ref<HTMLDivElement | null>(null);
let map: L.Map | null = null;

onMounted(() => {
    if (!el.value) return;
    map = L.map(el.value, {
        center: [props.lat, props.lng],
        zoom: props.zoom,
        zoomControl: false,
        attributionControl: false,
        dragging: false,
        touchZoom: false,
        scrollWheelZoom: false,
        doubleClickZoom: false,
        keyboard: false,
        boxZoom: false,
    });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
});

watch(
    () => [props.lat, props.lng, props.zoom] as const,
    ([lat, lng, zoom]) => {
        map?.setView([lat, lng], zoom);
    },
);

onUnmounted(() => {
    map?.remove();
    map = null;
});
</script>
