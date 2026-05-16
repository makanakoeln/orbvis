<template>
    <div class="max-w-5xl">
        <div class="flex justify-between items-center" style="margin-bottom: var(--dimension-6)">
            <div>
                <CmkHeading type="h2">
                    {{ t('admin.connectionsTitle') }}
                </CmkHeading>
                <CmkParagraph class="admin-subtitle">
                    {{ t('admin.connectionsSubtitle') }}
                </CmkParagraph>
            </div>
            <CmkButton variant="primary" @click="openCreate">
                <CmkIcon name="add" size="small" style="margin-right: var(--dimension-3)" />
                {{ t('admin.addConnection') }}
            </CmkButton>
        </div>

        <div v-if="store.loading" class="flex items-center justify-center py-8">
            <CmkLoading />
        </div>

        <CmkAlertBox v-else-if="store.error" variant="error">{{ store.error }}</CmkAlertBox>

        <div
            v-else-if="store.connections.length === 0"
            class="text-center py-16 bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl"
        >
            <p class="text-[var(--text-muted)] text-sm">{{ t('admin.noConnections') }}</p>
            <p class="text-[var(--text-muted)] text-sm mt-1">{{ t('admin.noConnectionsHint') }}</p>
        </div>

        <div
            v-else
            class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden"
        >
            <table class="w-full text-sm">
                <thead>
                    <tr class="border-b border-[var(--border)]">
                        <th
                            class="text-left text-sm font-semibold text-[var(--text-muted)] tracking-wider"
                            style="padding: 6px 12px"
                        >
                            {{ t('admin.status') }}
                        </th>
                        <th
                            class="text-left text-sm font-semibold text-[var(--text-muted)] tracking-wider"
                            style="padding: 6px 12px"
                        >
                            ID
                        </th>
                        <th
                            class="text-left text-sm font-semibold text-[var(--text-muted)] tracking-wider"
                            style="padding: 6px 12px"
                        >
                            {{ t('admin.displayLabel') }}
                        </th>
                        <th
                            class="text-left text-sm font-semibold text-[var(--text-muted)] tracking-wider"
                            style="padding: 6px 12px"
                        >
                            {{ t('admin.type') }}
                        </th>
                        <th
                            class="text-left text-sm font-semibold text-[var(--text-muted)] tracking-wider"
                            style="padding: 6px 12px"
                        >
                            {{ t('admin.connection') }}
                        </th>
                        <th
                            class="text-right text-sm font-semibold text-[var(--text-muted)] tracking-wider"
                            style="padding: 6px 12px"
                        >
                            {{ t('admin.actions') }}
                        </th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-[var(--border)]">
                    <tr
                        v-for="b in store.connections"
                        :key="b.id"
                        class="hover:bg-[var(--bg-hover)] transition-colors"
                    >
                        <td style="padding: 6px 12px">
                            <button
                                :disabled="statusLoading[b.id]"
                                class="flex items-center gap-[6px] group cursor-pointer"
                                :title="t('common.test')"
                                @click="testExisting(b.id)"
                            >
                                <span class="relative flex shrink-0">
                                    <span
                                        v-if="statusLoading[b.id]"
                                        class="rounded-full bg-[var(--color-pending)] animate-pulse"
                                        style="width: 8px; height: 8px"
                                    />
                                    <span
                                        v-else-if="statuses[b.id] === undefined"
                                        class="rounded-full bg-[var(--color-pending)]"
                                        style="width: 8px; height: 8px"
                                    />
                                    <span
                                        v-else-if="statuses[b.id]"
                                        class="rounded-full bg-[var(--color-corporate-green-50)] shadow-[0_0_6px_rgba(74,222,128,0.6)]"
                                        style="width: 8px; height: 8px"
                                    />
                                    <span
                                        v-else
                                        class="rounded-full bg-[var(--color-light-red-40)]"
                                        style="width: 8px; height: 8px"
                                    />
                                </span>
                                <span
                                    class="text-sm text-[var(--text-muted)] group-hover:text-[var(--text)] transition-colors"
                                >
                                    {{
                                        statusLoading[b.id]
                                            ? t('common.testing')
                                            : (statusMessages[b.id] ?? t('common.test'))
                                    }}
                                </span>
                                <svg
                                    class="text-[var(--text-muted)] group-hover:text-[var(--text-muted)] transition-colors opacity-0 group-hover:opacity-100 shrink-0"
                                    style="width: 11px; height: 11px"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2.5"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
                                    />
                                </svg>
                            </button>
                        </td>
                        <td
                            class="font-mono text-sm text-[var(--text-muted)]"
                            style="padding: 6px 12px"
                        >
                            {{ b.id }}
                        </td>
                        <td class="text-[var(--text)]" style="padding: 6px 12px">
                            {{ b.label || '—' }}
                        </td>
                        <td style="padding: 6px 12px">
                            <CmkBadge
                                size="small"
                                type="outline"
                                :color="
                                    b.type === 'livestatus'
                                        ? 'success'
                                        : b.type === 'icinga2'
                                          ? 'warning'
                                          : 'default'
                                "
                                >{{ b.type }}</CmkBadge
                            >
                        </td>
                        <td
                            class="text-[var(--text-muted)] font-mono text-sm"
                            style="padding: 6px 12px"
                        >
                            <template v-if="b.type === 'livestatus'">
                                {{
                                    b.socket_path ||
                                    (b.host ? (b.port ? `${b.host}:${b.port}` : b.host) : '—')
                                }}
                            </template>
                            <template v-else-if="b.type === 'icinga2'">
                                {{ b.icinga2_url || '—' }}
                            </template>
                            <span v-else class="text-[var(--text-muted)]">{{
                                t('admin.builtIn')
                            }}</span>
                        </td>
                        <td class="text-right" style="padding: 6px 12px">
                            <div class="flex items-center justify-end gap-[4px]">
                                <button
                                    class="p-[4px] rounded-md text-[var(--text-muted)] hover:text-[var(--color-corporate-green-50)] hover:bg-[var(--color-corporate-green-50)]/10 transition-all"
                                    :title="t('common.edit')"
                                    @click="openEdit(b)"
                                >
                                    <CmkIcon name="edit" size="small" />
                                </button>
                                <button
                                    class="p-[4px] rounded-md text-[var(--text-muted)] hover:text-[var(--color-light-red-40)] hover:bg-[var(--color-light-red-50)]/10 transition-all"
                                    :title="t('common.delete')"
                                    @click="deleteTarget = b.id"
                                >
                                    <CmkIcon name="delete" size="small" />
                                </button>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <OrbConfirmDialog
            :open="!!deleteTarget"
            :title="deleteTarget ? t('admin.deleteConnection', { id: deleteTarget }) : ''"
            :message="t('board.cannotBeUndone')"
            :confirm-label="t('common.delete')"
            @confirm="confirmRemove"
            @cancel="deleteTarget = null"
        />

        <CmkSlideInDialog
            v-if="dialog.open"
            :open="dialog.open"
            size="small"
            :header="{
                title:
                    dialog.mode === 'create'
                        ? t('admin.addConnectionTitle')
                        : t('admin.editConnection'),
                closeButton: true,
            }"
            @close="closeDialog"
        >
            <div class="connection-edit__body">
                <div class="connection-edit__id">
                    <CmkLabel>{{ t('admin.connectionId') }}</CmkLabel>
                    <CmkInput
                        v-if="dialog.mode === 'create'"
                        v-model="dialogId"
                        placeholder="cmk_heute"
                        field-size="FILL"
                    />
                    <p v-else class="connection-edit__id-readonly">{{ dialogId }}</p>
                    <p
                        v-if="dialog.mode === 'create'"
                        class="text-sm text-[var(--text-muted)]"
                        style="margin-top: var(--dimension-2)"
                    >
                        {{ t('admin.connectionIdHint') }}
                    </p>
                </div>

                <div v-if="schemaError" class="text-sm text-[var(--color-light-red-40)]">
                    {{ schemaError }}
                </div>
                <div
                    v-else-if="!formSchema"
                    class="flex items-center justify-center py-6 text-[var(--text-muted)]"
                >
                    <CmkLoading />
                </div>
                <FormEdit
                    v-else
                    v-model:data="formSpecData"
                    :spec="formSchema"
                    :backend-validation="[]"
                />

                <CmkAlertBox v-if="dialogTest.ran" :variant="dialogTest.ok ? 'success' : 'error'">
                    {{ dialogTest.message }}
                </CmkAlertBox>

                <p v-if="formError" class="text-[var(--color-light-red-40)] text-sm">
                    {{ formError }}
                </p>

                <div class="connection-edit__footer">
                    <CmkButton variant="secondary" @click="closeDialog">
                        {{ t('common.cancel') }}
                    </CmkButton>
                    <CmkButton
                        variant="optional"
                        :disabled="dialogTest.loading || !formSchema"
                        @click="testDialog"
                    >
                        {{ dialogTest.loading ? t('common.testing') : t('common.test') }}
                    </CmkButton>
                    <CmkButton variant="primary" :disabled="saving || !formSchema" @click="save">
                        {{ saving ? t('common.saving') : t('common.save') }}
                    </CmkButton>
                </div>
            </div>
        </CmkSlideInDialog>
    </div>
</template>

<script setup lang="ts">
import CmkAlertBox from '@cmk/components/CmkAlertBox.vue';
import CmkBadge from '@cmk/components/CmkBadge.vue';
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkIcon from '@cmk/components/CmkIcon';
import CmkLabel from '@cmk/components/CmkLabel.vue';
import CmkLoading from '@cmk/components/CmkLoading.vue';
import CmkSlideInDialog from '@cmk/components/CmkSlideInDialog.vue';
import CmkHeading from '@cmk/components/typography/CmkHeading.vue';
import CmkParagraph from '@cmk/components/typography/CmkParagraph.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import FormEdit from '@cmk/form/FormEdit.vue';
import { initializeComponentRegistry } from '@cmk/form/private/FormEditDispatcher/dispatch';
import type { VueFormspecComponents } from 'cmk-shared-typing/typescript/vue_formspec_components';
import { onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { connectionsApi, connectionsApiFormSpec } from '@/api/client';
import OrbConfirmDialog from '@/components/OrbConfirmDialog.vue';
import { useToast } from '@/composables/useToast';
import { useAuthStore } from '@/stores/auth';
import { useConnectionsStore } from '@/stores/connections';
import type { ConnectionConfig } from '@/types/api';

type Schema = NonNullable<VueFormspecComponents['components']>;

initializeComponentRegistry();

const { t } = useI18n();
const store = useConnectionsStore();
const auth = useAuthStore();
const toast = useToast();

const statuses = reactive<Record<string, boolean>>({});
const statusMessages = reactive<Record<string, string>>({});
const statusLoading = reactive<Record<string, boolean>>({});

async function testExisting(id: string) {
    statusLoading[id] = true;
    try {
        const result = await connectionsApi.test(id, auth.accessToken!);
        statuses[id] = result.ok;
        statusMessages[id] = result.message;
    } catch (e: unknown) {
        statuses[id] = false;
        statusMessages[id] = e instanceof Error ? e.message : 'Error';
    } finally {
        statusLoading[id] = false;
    }
}

async function testAll() {
    for (const b of store.connections) testExisting(b.id);
}

const deleteTarget = ref<string | null>(null);
const dialog = reactive({ open: false, mode: 'create' as 'create' | 'edit' });
const saving = ref(false);
const formError = ref('');
const schemaError = ref('');
const dialogId = ref('');
const dialogTest = reactive({ loading: false, ran: false, ok: false, message: '' });

const formSchema = ref<Schema | null>(null);
const formSpecData = ref<Record<string, unknown>>({});

async function ensureSchema() {
    if (formSchema.value) return;
    try {
        const spec = await connectionsApiFormSpec.getSchema(auth.accessToken!);
        formSchema.value = spec as unknown as Schema;
    } catch (e: unknown) {
        schemaError.value = e instanceof Error ? e.message : 'Schema load failed';
    }
}

function prepareDialog(mode: 'create' | 'edit', id: string) {
    Object.assign(dialogTest, { loading: false, ran: false, ok: false, message: '' });
    formError.value = '';
    schemaError.value = '';
    dialog.mode = mode;
    dialogId.value = id;
    formSpecData.value = {};
    dialog.open = true;
}

async function openCreate() {
    prepareDialog('create', '');
    await ensureSchema();
    // After schema arrives, seed defaults so the cascading 'type' starts on
    // livestatus instead of an empty body.
    if (formSchema.value) {
        const dv = (formSchema.value as { default_value?: unknown }).default_value;
        if (dv && typeof dv === 'object') {
            formSpecData.value = structuredClone(dv) as Record<string, unknown>;
        }
    }
}

async function openEdit(b: ConnectionConfig) {
    prepareDialog('edit', b.id);
    const fdataPromise = connectionsApiFormSpec.getFormData(b.id, auth.accessToken!);
    await ensureSchema();
    try {
        formSpecData.value = await fdataPromise;
    } catch (e: unknown) {
        formError.value = e instanceof Error ? e.message : 'Failed to load connection data';
    }
}

function closeDialog() {
    dialog.open = false;
}

function validateNewId(): string | null {
    if (dialog.mode !== 'create') return null;
    const id = dialogId.value.trim();
    if (!id) return t('admin.connectionIdRequired');
    if (!/^[A-Za-z0-9_-]+$/.test(id)) return t('admin.connectionIdInvalid');
    if (store.connections.some((c) => c.id === id)) return t('admin.connectionIdTaken');
    return null;
}

async function testDialog() {
    formError.value = '';
    dialogTest.ran = false;
    const idError = validateNewId();
    if (idError) {
        formError.value = idError;
        return;
    }
    dialogTest.loading = true;
    try {
        const result = await connectionsApiFormSpec.testFromForm(
            dialogId.value.trim(),
            formSpecData.value,
            auth.accessToken!,
        );
        dialogTest.ok = result.ok;
        dialogTest.message = result.message;
        dialogTest.ran = true;
    } catch (e: unknown) {
        dialogTest.ok = false;
        dialogTest.message = e instanceof Error ? e.message : 'Error';
        dialogTest.ran = true;
    } finally {
        dialogTest.loading = false;
    }
}

async function save() {
    formError.value = '';
    const idError = validateNewId();
    if (idError) {
        formError.value = idError;
        return;
    }
    saving.value = true;
    try {
        const id = dialogId.value.trim();
        if (dialog.mode === 'create') {
            await connectionsApiFormSpec.createFromForm(id, formSpecData.value, auth.accessToken!);
            toast.success(t('admin.connectionCreated'));
        } else {
            await connectionsApiFormSpec.updateFromForm(id, formSpecData.value, auth.accessToken!);
            toast.success(t('admin.connectionUpdated'));
        }
        await store.fetchConnections();
        dialog.open = false;
        testAll();
    } catch (e: unknown) {
        formError.value = e instanceof Error ? e.message : t('admin.saveFailed');
    } finally {
        saving.value = false;
    }
}

async function confirmRemove() {
    const id = deleteTarget.value;
    if (!id) return;
    deleteTarget.value = null;
    try {
        await store.deleteConnection(id);
        delete statuses[id];
        delete statusMessages[id];
        toast.success(t('admin.connectionDeleted'));
    } catch (e: unknown) {
        toast.error(e instanceof Error ? e.message : t('admin.deleteFailed'));
    }
}

onMounted(async () => {
    await store.fetchConnections();
    testAll();
});
</script>

<style scoped>
.connection-edit__body {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-5);
    padding-bottom: var(--dimension-5);
}

.connection-edit__id {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-2);
}

.connection-edit__id-readonly {
    font-family: var(--font-family-mono, monospace);
    font-size: 0.875rem;
    color: var(--text);
    padding: var(--dimension-3) var(--dimension-4);
    background: var(--bg-elevated, var(--bg-hover));
    border-radius: 6px;
    border: 1px solid var(--border);
    width: max-content;
}

.connection-edit__footer {
    position: sticky;
    bottom: 0;
    display: flex;
    justify-content: flex-end;
    gap: var(--dimension-3);
    padding: var(--dimension-4) 0;
    background: linear-gradient(
        to top,
        var(--bg-surface) 0%,
        var(--bg-surface) 75%,
        transparent 100%
    );
    margin-top: var(--dimension-3);
}
</style>
