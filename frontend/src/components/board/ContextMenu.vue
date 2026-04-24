<template>
    <div
        class="fixed z-50 bg-[var(--bg-glass)] backdrop-blur-md ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-xl py-1.5 min-w-48"
        :style="{ left: `${x}px`, top: `${y}px` }"
    >
        <!-- Header -->
        <div class="px-3.5 py-2 border-b border-[var(--border)] mb-1">
            <p class="text-xs font-semibold text-[var(--text)] truncate max-w-52">
                {{ displayName }}
            </p>
            <p class="text-[10px] text-[var(--text-muted)] mt-0.5">
                {{ getObjectTypeLabel(object) }}
            </p>
        </div>

        <!-- Custom template block -->
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div
            v-if="renderedTemplate"
            class="px-3.5 py-2 text-xs text-[var(--text)] border-b border-[var(--border)] mb-1"
            v-html="renderedTemplate"
        />

        <a
            v-if="hostUrl"
            :href="hostUrl"
            target="_blank"
            class="flex items-center gap-2 px-3.5 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
        >
            <svg
                class="w-3.5 h-3.5 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
                />
            </svg>
            <span>{{ t('contextMenu.hostInCheckmk') }}</span>
        </a>
        <a
            v-if="hostServicesUrl"
            :href="hostServicesUrl"
            target="_blank"
            class="flex items-center gap-2 px-3.5 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
        >
            <svg
                class="w-3.5 h-3.5 shrink-0"
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
            <span>{{ t('contextMenu.hostProblemServices') }}</span>
        </a>
        <a
            v-if="serviceUrl"
            :href="serviceUrl"
            target="_blank"
            class="flex items-center gap-2 px-3.5 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
        >
            <svg
                class="w-3.5 h-3.5 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
                />
            </svg>
            <span>{{ t('contextMenu.serviceInCheckmk') }}</span>
        </a>
        <a
            v-if="groupUrl"
            :href="groupUrl"
            target="_blank"
            class="flex items-center gap-2 px-3.5 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
        >
            <svg
                class="w-3.5 h-3.5 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
                />
            </svg>
            <span>{{ t('contextMenu.groupInCheckmk') }}</span>
        </a>

        <div
            v-if="!hostUrl && !hostServicesUrl && !serviceUrl && !groupUrl && !checkmkUrl"
            class="px-3.5 py-2 text-xs text-[var(--text-muted)] italic"
        >
            {{ t('contextMenu.noCheckmkUrl') }}
        </div>

        <!-- CMK actions: ACK / Downtime / Force-check / Comment / Remove ACK / Notifications / Checks -->
        <template v-if="checkmkUrl && (object.type === 'host' || object.type === 'service')">
            <div class="border-t border-[var(--border)] mt-1 pt-1">
                <button
                    v-if="isProblematic && !state?.acknowledged"
                    class="w-full text-left flex items-center gap-2 px-3.5 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
                    @click="$emit('acknowledge')"
                >
                    <svg
                        class="w-3.5 h-3.5 shrink-0"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                    </svg>
                    <span>{{ t('contextMenu.acknowledge') }}</span>
                </button>
                <button
                    v-if="state?.acknowledged"
                    class="w-full text-left flex items-center gap-2 px-3.5 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
                    @click="$emit('removeAck')"
                >
                    <svg
                        class="w-3.5 h-3.5 shrink-0"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                    </svg>
                    <span>{{ t('contextMenu.removeAck') }}</span>
                </button>
                <button
                    class="w-full text-left flex items-center gap-2 px-3.5 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
                    @click="$emit('scheduleDowntime')"
                >
                    <svg
                        class="w-3.5 h-3.5 shrink-0"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                    </svg>
                    <span>{{ t('contextMenu.scheduleDowntime') }}</span>
                </button>
                <button
                    v-if="state?.in_downtime"
                    class="w-full text-left flex items-center gap-2 px-3.5 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
                    @click="$emit('removeDowntime')"
                >
                    <svg
                        class="w-3.5 h-3.5 shrink-0"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                    </svg>
                    <span>{{ t('contextMenu.removeDowntime') }}</span>
                </button>
                <button
                    class="w-full text-left flex items-center gap-2 px-3.5 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
                    @click="$emit('forceCheck')"
                >
                    <svg
                        class="w-3.5 h-3.5 shrink-0"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
                        />
                    </svg>
                    <span>{{ t('contextMenu.forceCheck') }}</span>
                </button>
                <button
                    class="w-full text-left flex items-center gap-2 px-3.5 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
                    @click="$emit('addComment')"
                >
                    <svg
                        class="w-3.5 h-3.5 shrink-0"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"
                        />
                    </svg>
                    <span>{{ t('contextMenu.addComment') }}</span>
                </button>
                <button
                    v-if="state?.notifications_enabled !== false"
                    class="w-full text-left flex items-center gap-2 px-3.5 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
                    @click="$emit('disableNotifications')"
                >
                    <svg
                        class="w-3.5 h-3.5 shrink-0"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M9.143 17.082a24.248 24.248 0 003.844.148m-3.844-.148a23.856 23.856 0 01-5.455-1.31 8.964 8.964 0 002.3-5.542m3.155 6.852a3 3 0 005.667 1.97m1.965-2.277L21 21m-4.225-4.225a23.81 23.81 0 003.536-1.003A8.967 8.967 0 0118 9.75V9A6 6 0 006.53 6.53m10.245 10.245L6.53 6.53M3 3l3.53 3.53"
                        />
                    </svg>
                    <span>{{ t('contextMenu.disableNotifications') }}</span>
                </button>
                <button
                    v-if="state?.notifications_enabled === false"
                    class="w-full text-left flex items-center gap-2 px-3.5 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
                    @click="$emit('enableNotifications')"
                >
                    <svg
                        class="w-3.5 h-3.5 shrink-0"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
                        />
                    </svg>
                    <span>{{ t('contextMenu.enableNotifications') }}</span>
                </button>
            </div>
        </template>

        <div class="border-t border-[var(--border)] mt-1 pt-1">
            <button
                v-if="showEdit"
                class="w-full text-left flex items-center gap-2 px-3.5 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
                @click="$emit('edit')"
            >
                <svg
                    class="w-3.5 h-3.5 shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125"
                    />
                </svg>
                {{ t('contextMenu.editProperties') }}
            </button>
            <button
                v-if="showEdit"
                class="w-full text-left flex items-center gap-2 px-3.5 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
                @click="$emit('duplicate')"
            >
                <svg
                    class="w-3.5 h-3.5 shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75"
                    />
                </svg>
                {{ t('contextMenu.duplicate') }}
            </button>
            <button
                v-if="showEdit"
                class="w-full text-left flex items-center gap-2 px-3.5 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/8 transition-colors"
                @click="$emit('delete')"
            >
                <svg
                    class="w-3.5 h-3.5 shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                    />
                </svg>
                {{ t('contextMenu.delete') }}
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import type { BoardObject, ObjectState } from '@/types/api';
import { getBoardObjectName, getObjectTypeLabel } from '@/utils/naming';
import { interpolateTemplate } from '@/utils/template';

const { t } = useI18n();

const props = defineProps<{
    object: BoardObject;
    state?: ObjectState;
    x: number;
    y: number;
    checkmkUrl?: string | null;
    showEdit?: boolean;
    template?: string | null;
}>();

defineEmits<{
    close: [];
    edit: [];
    duplicate: [];
    delete: [];
    acknowledge: [];
    removeAck: [];
    scheduleDowntime: [];
    removeDowntime: [];
    forceCheck: [];
    addComment: [];
    enableNotifications: [];
    disableNotifications: [];
}>();

const renderedTemplate = computed(() =>
    props.template ? interpolateTemplate(props.template, props.object, props.state) : null,
);

// ACK is only meaningful for problem states
const _OK_STATES = new Set(['UP', 'OK', 'PENDING']);
const isProblematic = computed(
    () => props.state !== undefined && !_OK_STATES.has(props.state.state),
);

const displayName = computed(() => getBoardObjectName(props.object));

const base = computed(() => {
    // Strip trailing /check_mk or /check_mk/ so we can safely append /check_mk/view.py
    return props.checkmkUrl?.replace(/\/check_mk\/?$/, '').replace(/\/$/, '') ?? null;
});

// Extract site name from last path segment, e.g. "http://host/heute" → "heute"
const site = computed(() => {
    if (!base.value) return null;
    const parts = base.value.split('/');
    return parts[parts.length - 1] || null;
});

const hostUrl = computed(() => {
    if (!base.value || !props.object.host_name) return null;
    const p: Record<string, string> = { view_name: 'hoststatus', host: props.object.host_name };
    if (site.value) p.site = site.value;
    return `${base.value}/check_mk/view.py?${new URLSearchParams(p)}`;
});

const serviceUrl = computed(() => {
    if (!base.value || !props.object.host_name || !props.object.service_description) return null;
    const p: Record<string, string> = {
        view_name: 'service',
        host: props.object.host_name,
        service: props.object.service_description,
    };
    if (site.value) p.site = site.value;
    return `${base.value}/check_mk/view.py?${new URLSearchParams(p)}`;
});

const groupUrl = computed(() => {
    if (!base.value || !props.object.group_name) return null;
    const view = props.object.type === 'hostgroup' ? 'hostgroup' : 'servicegroup';
    const key = props.object.type === 'hostgroup' ? 'hostgroup' : 'servicegroup';
    const p: Record<string, string> = { view_name: view, [key]: props.object.group_name };
    if (site.value) p.site = site.value;
    return `${base.value}/check_mk/view.py?${new URLSearchParams(p)}`;
});

const hostServicesUrl = computed(() => {
    if (!base.value || props.object.type !== 'host' || !props.object.host_name) return null;
    if (!isProblematic.value) return null;
    // When the host itself is down/unreachable, services can't be checked independently
    const hostState = props.state?.state;
    if (hostState === 'DOWN' || hostState === 'UNREACHABLE') return null;
    const p: Record<string, string> = {
        view_name: 'host',
        host: props.object.host_name,
        filled_in: 'filter',
        _active: 'serviceregex;svcstate;host;siteopt',
        st1: 'on',
        st2: 'on',
        st3: 'on',
        stp: 'on',
    };
    if (site.value) p.site = site.value;
    return `${base.value}/check_mk/view.py?${new URLSearchParams(p)}`;
});
</script>
