<template>
    <div>
        <div class="flex justify-between items-center" style="margin-bottom: var(--dimension-6)">
            <div>
                <CmkHeading type="h2">
                    {{ t('admin.icons') }}
                </CmkHeading>
                <CmkParagraph class="admin-subtitle">
                    {{ t('admin.iconsSubtitle') }}
                </CmkParagraph>
            </div>
            <CmkButton variant="primary" @click="fileInputEl?.click()">
                <svg
                    style="width: 13px; height: 13px; margin-right: var(--dimension-3)"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                    />
                </svg>
                {{ t('admin.uploadIcon') }}
            </CmkButton>
            <input
                ref="fileInputEl"
                type="file"
                accept="image/png,image/jpeg,image/svg+xml,image/webp"
                multiple
                class="hidden"
                @change="uploadIcons"
            />
        </div>

        <!-- Upload feedback -->
        <CmkAlertBox v-if="uploadError" variant="error">{{ uploadError }}</CmkAlertBox>

        <!-- Image is not in use → simple confirm dialog. -->
        <OrbConfirmDialog
            :open="dialogReady && !!deleteTargetName && !pendingUsage.length"
            :title="deleteTargetName ? t('admin.deleteIcon', { name: deleteTargetName }) : ''"
            :message="t('board.cannotBeUndone')"
            :confirm-label="t('common.delete')"
            @confirm="confirmDeleteIcon"
            @cancel="cancelDelete"
        />

        <!-- Image is referenced by N boards → CMK SlideIn with link cards.
             Mirrors CMK's WATO pattern (see watolib/timeperiods.py +
             CmkSlideInDialog/CmkLinkCard) so a long usage list scrolls
             gracefully and operators can jump to each affected board. -->
        <CmkSlideInDialog
            :open="dialogReady && !!deleteTargetName && pendingUsage.length > 0"
            :header="{
                title: t('admin.imageInUseTitle'),
                icon: { name: 'warning', size: 'large' },
                closeButton: true,
            }"
            size="medium"
            border-color="warning"
            @close="cancelDelete"
        >
            <div class="image-usage-pane">
                <CmkParagraph class="image-usage-pane__intro">
                    {{
                        t('admin.imageInUseBody', {
                            name: deleteTargetName,
                            count: pendingUsage.length,
                        })
                    }}
                </CmkParagraph>
                <CmkLinkCardContainer>
                    <CmkLinkCard
                        v-for="entry in pendingUsage"
                        :key="entry.board"
                        icon-name="dashboard-main"
                        :title="entry.alias || entry.board"
                        :subtitle="usageSubtitle(entry)"
                        :url="boardUrl(entry)"
                        :open-in-new-tab="true"
                    />
                </CmkLinkCardContainer>
                <div class="image-usage-pane__actions">
                    <CmkButton variant="secondary" @click="cancelDelete">
                        {{ t('common.cancel') }}
                    </CmkButton>
                    <CmkButton variant="warning" @click="confirmDeleteIcon">
                        {{ t('common.delete') }}
                    </CmkButton>
                </div>
            </div>
        </CmkSlideInDialog>

        <div v-if="loading" class="flex items-center justify-center py-8">
            <CmkLoading />
        </div>

        <div
            v-else-if="!icons.length"
            class="text-center py-[40px] text-[var(--text-muted)] text-sm"
        >
            <svg
                class="mx-auto text-[var(--text-muted)]"
                style="width: 32px; height: 32px; margin-bottom: var(--dimension-4)"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="1.5"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
                />
            </svg>
            {{ t('admin.noIcons') }}
        </div>

        <div v-else class="grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-[8px]">
            <div
                v-for="icon in icons"
                :key="icon.name"
                class="group relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl flex flex-col items-center gap-[6px] hover:ring-[var(--default-form-element-border-color)] transition-all"
                style="padding: var(--dimension-4)"
            >
                <img
                    :src="`${BASE_URL}${icon.url}`"
                    :alt="icon.name"
                    class="object-contain"
                    style="width: 40px; height: 40px"
                    :class="icon.name.endsWith('.svg') ? 'svg-icon' : ''"
                />
                <p
                    class="text-[10px] text-[var(--text-muted)] font-mono text-center truncate w-full"
                    :title="icon.name"
                >
                    {{ icon.name }}
                </p>
                <span
                    v-if="icon.builtin"
                    class="absolute text-[8px] uppercase tracking-wide font-semibold text-[var(--text-muted)] bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded px-1 py-[1px]"
                    style="top: 4px; left: 4px"
                    :title="t('admin.builtinImageCannotDelete')"
                >
                    {{ t('admin.builtinImage') }}
                </span>
                <button
                    v-if="!icon.builtin"
                    class="absolute rounded bg-[var(--color-light-red-50)]/0 hover:bg-[var(--color-light-red-50)]/20 text-[var(--text-muted)] hover:text-[var(--color-light-red-40)] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all"
                    style="top: 4px; right: 4px; width: 18px; height: 18px"
                    :title="t('common.delete')"
                    @click="onDeleteClick(icon.name)"
                >
                    <svg
                        style="width: 12px; height: 12px"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2.5"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M6 18L18 6M6 6l12 12"
                        />
                    </svg>
                </button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import CmkAlertBox from '@cmk/components/CmkAlertBox.vue';
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkLinkCard from '@cmk/components/CmkLinkCard/CmkLinkCard.vue';
import CmkLinkCardContainer from '@cmk/components/CmkLinkCard/CmkLinkCardContainer.vue';
import CmkLoading from '@cmk/components/CmkLoading.vue';
import CmkSlideInDialog from '@cmk/components/CmkSlideInDialog.vue';
import CmkHeading from '@cmk/components/typography/CmkHeading.vue';
import CmkParagraph from '@cmk/components/typography/CmkParagraph.vue';
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { ApiError, imagesApi } from '@/api/client';
import OrbConfirmDialog from '@/components/OrbConfirmDialog.vue';
import { useAuthStore } from '@/stores/auth';
import type { ImageEntry, ImageUsageEntry } from '@/types/api';

const BASE_URL = import.meta.env.BASE_URL;
const { t } = useI18n();
const auth = useAuthStore();

const fileInputEl = ref<HTMLInputElement | null>(null);
const icons = ref<ImageEntry[]>([]);
const loading = ref(false);
const uploadError = ref('');

async function fetchIcons() {
    loading.value = true;
    try {
        icons.value = await imagesApi.list(auth.accessToken!);
    } finally {
        loading.value = false;
    }
}

async function uploadIcons(event: Event) {
    const files = (event.target as HTMLInputElement).files;
    if (!files?.length) return;
    uploadError.value = '';
    try {
        const results = await Promise.allSettled(
            Array.from(files).map((file) => imagesApi.upload(file, auth.accessToken!)),
        );
        await fetchIcons();
        const failed = results.find((r): r is PromiseRejectedResult => r.status === 'rejected');
        if (failed) {
            uploadError.value =
                failed.reason instanceof Error ? failed.reason.message : 'Upload failed';
        }
    } catch (e: unknown) {
        uploadError.value = e instanceof Error ? e.message : 'Upload failed';
    }
    // Reset file input
    (event.target as HTMLInputElement).value = '';
}

const deleteTargetName = ref<string | null>(null);
const pendingUsage = ref<ImageUsageEntry[]>([]);
// Gate the dialog until the usage check resolves — otherwise the simple
// "delete?" prompt flashes briefly before the in-use warning takes over.
const dialogReady = ref(false);

async function onDeleteClick(name: string) {
    deleteTargetName.value = name;
    pendingUsage.value = [];
    dialogReady.value = false;
    try {
        const usage = await imagesApi.usage(name, auth.accessToken!);
        if (usage.length) pendingUsage.value = usage;
    } catch {
        // best-effort: fall through to confirm dialog if usage check fails
    } finally {
        // Only open the dialog after we know whether the image is in use, so
        // we never have to swap the dialog content under the user.
        if (deleteTargetName.value === name) dialogReady.value = true;
    }
}

function usageSubtitle(entry: ImageUsageEntry): string {
    const parts: string[] = [];
    if (entry.is_background) parts.push(t('admin.usedAsBackground'));
    if (entry.object_ids.length) parts.push(t('admin.usedByObjects', entry.object_ids.length));
    return parts.join(', ');
}

function boardUrl(entry: ImageUsageEntry): string {
    // Hash router: build a full URL so target=_blank opens the right route in
    // a new tab (a bare "#/boards/..." would resolve against the current
    // location and stay in-tab on some browsers).
    return `${window.location.pathname}#/boards/${entry.board}`;
}

function cancelDelete() {
    deleteTargetName.value = null;
    pendingUsage.value = [];
    dialogReady.value = false;
}

async function confirmDeleteIcon() {
    const name = deleteTargetName.value;
    if (!name) return;
    // Force=true when usage was detected; the user just confirmed via the
    // in-use warning. Without force the backend rejects with 409.
    const force = pendingUsage.value.length > 0;
    try {
        await imagesApi.delete(name, auth.accessToken!, force);
        icons.value = icons.value.filter((i) => i.name !== name);
        cancelDelete();
    } catch (e: unknown) {
        if (e instanceof ApiError && e.status === 409) {
            // Server-side double-check picked up usage we didn't see locally.
            const detail = e.detail as { usage?: ImageUsageEntry[] } | null;
            if (detail?.usage?.length) {
                pendingUsage.value = detail.usage;
                return;
            }
        }
        uploadError.value = e instanceof Error ? e.message : 'Delete failed';
        cancelDelete();
    }
}

onMounted(fetchIcons);
</script>

<style scoped>
.image-usage-pane {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-5);
    padding-bottom: var(--dimension-6);
}

.image-usage-pane__intro {
    line-height: 1.5;
}

.image-usage-pane__actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--dimension-3);
    padding-top: var(--dimension-4);
    border-top: 1px solid var(--border);
    position: sticky;
    bottom: 0;
    background: var(--bg-surface);
}
</style>
