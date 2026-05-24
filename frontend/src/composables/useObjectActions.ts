import { type MaybeRefOrGetter, reactive, ref, toValue } from 'vue';
import { useI18n } from 'vue-i18n';

import { cmkApi } from '@/api/client';
import { useToast } from '@/composables/useToast';
import { useStatesStore } from '@/stores/states';
import type { BoardObject, DowntimeEntry } from '@/types/api';

interface DispatchOptions {
    hostFn: (baseUrl: string, hostname: string) => Promise<void>;
    serviceFn: (baseUrl: string, hostname: string, service: string) => Promise<void>;
    errorKey: string;
    successKey?: string;
}

export interface UseObjectActions {
    ackModalObject: ReturnType<typeof ref<BoardObject | null>>;
    downtimeModalObject: ReturnType<typeof ref<BoardObject | null>>;
    commentModalObject: ReturnType<typeof ref<BoardObject | null>>;
    removeDowntimeModal: { visible: boolean; downtimes: DowntimeEntry[]; objectName: string };
    handlers: {
        acknowledge(obj: BoardObject | null): void;
        removeAck(obj: BoardObject | null): Promise<void>;
        scheduleDowntime(obj: BoardObject | null): void;
        removeDowntime(obj: BoardObject | null): Promise<void>;
        addComment(obj: BoardObject | null): void;
        forceCheck(obj: BoardObject | null): Promise<void>;
        toggleNotifications(obj: BoardObject | null, enable: boolean): Promise<void>;
    };
}

/**
 * Shared cmkApi-action plumbing for board context menus. Holds modal-state and
 * the host/service dispatch boilerplate so BoardCanvas and FlowBoard don't each
 * re-implement the same seven handlers.
 */
export function useObjectActions(
    checkmkUrl: MaybeRefOrGetter<string | null | undefined>,
    onActionStart?: () => void,
): UseObjectActions {
    const { t } = useI18n();
    const toast = useToast();
    const statesStore = useStatesStore();

    const ackModalObject = ref<BoardObject | null>(null);
    const downtimeModalObject = ref<BoardObject | null>(null);
    const commentModalObject = ref<BoardObject | null>(null);
    const removeDowntimeModal = reactive<{
        visible: boolean;
        downtimes: DowntimeEntry[];
        objectName: string;
    }>({ visible: false, downtimes: [], objectName: '' });

    function start(): string | null {
        onActionStart?.();
        const url = toValue(checkmkUrl);
        return url ?? null;
    }

    async function dispatchHostOrService(
        url: string,
        obj: BoardObject,
        { hostFn, serviceFn, errorKey, successKey }: DispatchOptions,
    ): Promise<void> {
        try {
            if (obj.type === 'service' && obj.host_name && obj.service_description) {
                await serviceFn(url, obj.host_name, obj.service_description);
            } else if (obj.host_name) {
                await hostFn(url, obj.host_name);
            } else {
                return;
            }
            if (successKey) toast.success(t(successKey));
            statesStore.refreshAfterCommand();
        } catch (err) {
            const detail = err instanceof Error ? err.message : '';
            toast.error(detail ? `${t(errorKey)}: ${detail}` : t(errorKey));
        }
    }

    function acknowledge(obj: BoardObject | null): void {
        start();
        if (obj) ackModalObject.value = obj;
    }

    async function removeAck(obj: BoardObject | null): Promise<void> {
        const url = start();
        if (!obj || !url) return;
        await dispatchHostOrService(url, obj, {
            hostFn: cmkApi.removeAcknowledgementHost,
            serviceFn: cmkApi.removeAcknowledgementService,
            errorKey: 'contextMenu.removeAckFailed',
        });
    }

    function scheduleDowntime(obj: BoardObject | null): void {
        start();
        if (obj) downtimeModalObject.value = obj;
    }

    async function removeDowntime(obj: BoardObject | null): Promise<void> {
        const url = start();
        if (!obj || !url) return;
        let downtimes: DowntimeEntry[];
        try {
            if (obj.type === 'service' && obj.host_name && obj.service_description) {
                downtimes = await cmkApi.listDowntimesService(
                    url,
                    obj.host_name,
                    obj.service_description,
                );
            } else if (obj.host_name) {
                downtimes = await cmkApi.listDowntimesHost(url, obj.host_name);
            } else {
                return;
            }
        } catch {
            toast.error(t('contextMenu.removeDowntimeFailed'));
            return;
        }
        if (downtimes.length === 0) {
            toast.error(t('contextMenu.noDowntimesFound'));
            return;
        }
        if (downtimes.length === 1) {
            try {
                await cmkApi.removeDowntimeById(url, downtimes[0].id, downtimes[0].site_id);
                toast.success(t('contextMenu.removeDowntimeSuccess'));
                statesStore.refreshAfterCommand();
            } catch {
                toast.error(t('contextMenu.removeDowntimeFailed'));
            }
            return;
        }
        removeDowntimeModal.downtimes = downtimes;
        removeDowntimeModal.objectName = obj.host_name ?? '';
        removeDowntimeModal.visible = true;
    }

    function addComment(obj: BoardObject | null): void {
        start();
        if (obj) commentModalObject.value = obj;
    }

    async function forceCheck(obj: BoardObject | null): Promise<void> {
        const url = start();
        if (!obj || !url) return;
        await dispatchHostOrService(url, obj, {
            hostFn: cmkApi.forceCheckHost,
            serviceFn: cmkApi.forceCheckService,
            errorKey: 'contextMenu.forceCheckFailed',
            successKey: 'contextMenu.forceCheckSuccess',
        });
    }

    async function toggleNotifications(obj: BoardObject | null, enable: boolean): Promise<void> {
        const url = start();
        if (!obj || !url) return;
        await dispatchHostOrService(url, obj, {
            hostFn: enable ? cmkApi.enableNotificationsHost : cmkApi.disableNotificationsHost,
            serviceFn: enable
                ? cmkApi.enableNotificationsService
                : cmkApi.disableNotificationsService,
            errorKey: 'contextMenu.toggleNotificationsFailed',
            successKey: 'contextMenu.toggleNotificationsSuccess',
        });
    }

    return {
        ackModalObject,
        downtimeModalObject,
        commentModalObject,
        removeDowntimeModal,
        handlers: {
            acknowledge,
            removeAck,
            scheduleDowntime,
            removeDowntime,
            addComment,
            forceCheck,
            toggleNotifications,
        },
    };
}
