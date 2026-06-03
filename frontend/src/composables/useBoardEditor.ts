/**
 * Map edit-mode state: drag & drop, line editing, object selection, placing new objects.
 */
import { getCurrentInstance, onBeforeUnmount, reactive, type Ref, ref, toRaw } from 'vue';

import { boardsApi } from '@/api/client';
import { useAuthStore } from '@/stores/auth';
import { useBoardsStore } from '@/stores/boards';
import { useSettingsStore } from '@/stores/settings';
import type { BoardObject, ObjectType } from '@/types/api';

export interface NewObjectDraft {
    type: ObjectType | '';
    host_name: string;
    service_description: string;
    group_name: string;
    board_name: string;
    aggregation_id: string;
    object_types: 'host' | 'service';
    object_filter: string;
    expand_depth: number;
    label_text: string;
    image_src: string;
    graph_url: string;
}

interface LineCoords {
    x: number;
    y: number;
    x2: number;
    y2: number;
    mid_x?: number | null;
    mid_y?: number | null;
}

type DragTarget = {
    kind: 'line';
    id: string;
    mode: 'move' | 'start' | 'end' | 'mid';
    init: LineCoords;
    mouseStartX: number;
    mouseStartY: number;
};

// mapName is a Ref so that this composable stays in sync when Vue Router reuses
// the MapView component for a different map (avoids stale closure over the old name).
export function useBoardEditor(mapName: Ref<string>, onMapChange: () => Promise<void>) {
    const auth = useAuthStore();
    const boardsStore = useBoardsStore();

    const editMode = ref(false);
    function toggleEditMode() {
        editMode.value = !editMode.value;
        if (!editMode.value) {
            selectedObjectId.value = null;
            placing.value = false;
        }
    }

    const selectedObjectId = ref<string | null>(null);
    function selectObject(id: string | null) {
        selectedObjectId.value = id;
    }

    let _onDragSaved: ((id: string) => void) | null = null;
    function setDragSavedCallback(cb: (id: string) => void) {
        _onDragSaved = cb;
    }

    const snapGrid = ref(0); // 0 = off, 10 or 20 = snap to grid
    function _snap(v: number): number {
        if (!snapGrid.value) return v;
        return Math.round(v / snapGrid.value) * snapGrid.value;
    }

    const dragTarget = ref<DragTarget | null>(null);
    let _canvasEl: HTMLElement | null = null;

    const lineDragPositions = reactive<Record<string, LineCoords>>({});

    function _mouseToCanvas(event: MouseEvent, canvasEl: HTMLElement) {
        const rect = canvasEl.getBoundingClientRect();
        // When canvas fills its parent (background image mode), positions are percentages
        // of native image size — read native dims from data attributes set by BoardCanvas.
        const nativeW = parseFloat(canvasEl.dataset.nativeWidth ?? '0');
        const nativeH = parseFloat(canvasEl.dataset.nativeHeight ?? '0');
        if (nativeW > 0 && nativeH > 0) {
            return {
                x: ((event.clientX - rect.left) / rect.width) * nativeW,
                y: ((event.clientY - rect.top) / rect.height) * nativeH,
            };
        }
        const parent = canvasEl.parentElement!;
        return {
            x: event.clientX - rect.left + parent.scrollLeft,
            y: event.clientY - rect.top + parent.scrollTop,
        };
    }

    function _onDocMouseMove(event: MouseEvent) {
        event.preventDefault();
        if (!_canvasEl) return;
        const t = dragTarget.value;
        if (!t) return;
        const pos = _mouseToCanvas(event, _canvasEl);

        const dx = pos.x - t.mouseStartX;
        const dy = pos.y - t.mouseStartY;
        const { init, mode } = t;
        // A bend only exists once the user starts dragging the mid handle; until
        // then mid stays null so the renderer keeps using the geometric center.
        const hasMid = init.mid_x != null && init.mid_y != null;
        const baseMidX = init.mid_x ?? (init.x + init.x2) / 2;
        const baseMidY = init.mid_y ?? (init.y + init.y2) / 2;
        if (mode === 'move') {
            lineDragPositions[t.id] = {
                x: _snap(Math.round(init.x + dx)),
                y: _snap(Math.round(init.y + dy)),
                x2: _snap(Math.round(init.x2 + dx)),
                y2: _snap(Math.round(init.y2 + dy)),
                mid_x: hasMid ? _snap(Math.round(baseMidX + dx)) : null,
                mid_y: hasMid ? _snap(Math.round(baseMidY + dy)) : null,
            };
        } else if (mode === 'start') {
            lineDragPositions[t.id] = {
                x: _snap(Math.round(init.x + dx)),
                y: _snap(Math.round(init.y + dy)),
                x2: init.x2,
                y2: init.y2,
                mid_x: init.mid_x,
                mid_y: init.mid_y,
            };
        } else if (mode === 'end') {
            lineDragPositions[t.id] = {
                x: init.x,
                y: init.y,
                x2: _snap(Math.round(init.x2 + dx)),
                y2: _snap(Math.round(init.y2 + dy)),
                mid_x: init.mid_x,
                mid_y: init.mid_y,
            };
        } else {
            lineDragPositions[t.id] = {
                x: init.x,
                y: init.y,
                x2: init.x2,
                y2: init.y2,
                mid_x: _snap(Math.round(baseMidX + dx)),
                mid_y: _snap(Math.round(baseMidY + dy)),
            };
        }
    }

    // Track whether this composable has registered document listeners so the
    // unmount cleanup can tear them down without double-removing (the capture
    // flag has to match what was used at addEventListener time, hence the flag).
    let _docListenersActive = false;

    function _removeDocListeners() {
        if (!_docListenersActive) return;
        document.removeEventListener('mousemove', _onDocMouseMove, { capture: true });
        document.removeEventListener('mouseup', _onDocMouseUp, { capture: true });
        _docListenersActive = false;
    }

    function _onDocMouseUp() {
        _removeDocListeners();
        endLineDrag();
    }

    function _startDocDrag(canvasEl: HTMLElement) {
        _canvasEl = canvasEl;
        if (_docListenersActive) return;
        // Use capture phase so we receive events before any child element that may
        // call stopPropagation() (e.g. D3 internal handlers).
        document.addEventListener('mousemove', _onDocMouseMove, { capture: true });
        document.addEventListener('mouseup', _onDocMouseUp, { capture: true });
        _docListenersActive = true;
    }

    // Critical cleanup: if the component using this composable unmounts while a
    // drag is in flight (e.g. router navigation mid-drag), the document-level
    // listeners would otherwise linger and hold references to stale state.
    if (getCurrentInstance()) {
        onBeforeUnmount(() => {
            _removeDocListeners();
            _canvasEl = null;
        });
    }

    async function saveObjectPosition(id: string, x: number, y: number) {
        const objects = boardsStore.currentBoard?.objects ?? [];
        // Nudge to free spot if the drop lands on top of another object — otherwise
        // they overlap pixel-perfect and the lower one becomes invisible.
        const adjusted = _avoidOverlap(id, x, y, objects);
        const obj = objects.find((o) => o.id === id);
        if (obj) {
            obj.x = adjusted.x;
            obj.y = adjusted.y;
        }
        try {
            await boardsApi.updateObject(
                mapName.value,
                id,
                { x: adjusted.x, y: adjusted.y },
                auth.accessToken!,
            );
            if (_onDragSaved) _onDragSaved(id);
        } catch (e) {
            console.error('Failed to save drag', e);
            await onMapChange();
        }
    }

    function _avoidOverlap(id: string, x: number, y: number, objects: readonly BoardObject[]) {
        const COLLISION_RADIUS = 12;
        const STEP = 28;
        const MAX_STEPS = 8;
        for (let i = 0; i < MAX_STEPS; i++) {
            const hit = objects.some(
                (o) =>
                    o.id !== id &&
                    o.type !== 'line' &&
                    Math.abs(o.x - x) < COLLISION_RADIUS &&
                    Math.abs(o.y - y) < COLLISION_RADIUS,
            );
            if (!hit) return { x: _snap(x), y: _snap(y) };
            x += STEP;
            y += STEP;
        }
        return { x: _snap(x), y: _snap(y) };
    }

    function startLineDrag(
        event: MouseEvent,
        obj: BoardObject,
        mode: 'move' | 'start' | 'end' | 'mid',
        canvasEl: HTMLElement,
    ) {
        const mouse = _mouseToCanvas(event, canvasEl);
        const x2 = obj.x2 ?? obj.x + 100;
        const y2 = obj.y2 ?? obj.y + 100;
        const init: LineCoords = {
            x: obj.x,
            y: obj.y,
            x2,
            y2,
            mid_x: obj.mid_x ?? null,
            mid_y: obj.mid_y ?? null,
        };
        lineDragPositions[obj.id] = { ...init };
        dragTarget.value = {
            kind: 'line',
            id: obj.id,
            mode,
            init,
            mouseStartX: mouse.x,
            mouseStartY: mouse.y,
        };
        selectedObjectId.value = obj.id;
        _startDocDrag(canvasEl);
        event.preventDefault();
        event.stopPropagation();
    }

    async function endLineDrag() {
        const t = dragTarget.value;
        if (!t || t.kind !== 'line') return;
        dragTarget.value = null;
        try {
            const lp = lineDragPositions[t.id];
            await boardsApi.updateObject(
                mapName.value,
                t.id,
                {
                    x: lp.x,
                    y: lp.y,
                    x2: lp.x2,
                    y2: lp.y2,
                    mid_x: lp.mid_x ?? null,
                    mid_y: lp.mid_y ?? null,
                },
                auth.accessToken!,
            );
            const obj = boardsStore.currentBoard?.objects.find((o) => o.id === t.id);
            if (obj) {
                obj.x = lp.x;
                obj.y = lp.y;
                obj.x2 = lp.x2;
                obj.y2 = lp.y2;
                obj.mid_x = lp.mid_x ?? null;
                obj.mid_y = lp.mid_y ?? null;
            }
            delete lineDragPositions[t.id];
            if (_onDragSaved) _onDragSaved(t.id);
        } catch (e) {
            console.error('Failed to save line drag', e);
            await onMapChange();
        }
    }

    async function updateObjectProperties(id: string, updates: Record<string, unknown>) {
        const updated = await boardsApi.updateObject(mapName.value, id, updates, auth.accessToken!);
        const objects = boardsStore.currentBoard?.objects;
        if (objects && updated) {
            const idx = objects.findIndex((o) => o.id === id);
            if (idx !== -1) objects[idx] = updated;
        }
    }

    const placing = ref(false);
    const draft = reactive<NewObjectDraft>({
        type: '',
        host_name: '',
        service_description: '',
        group_name: '',
        board_name: '',
        aggregation_id: '',
        object_types: 'host' as 'host' | 'service',
        object_filter: '',
        expand_depth: 0,
        label_text: '',
        image_src: '',
        graph_url: '',
    });

    function startPlacing() {
        if (!draft.type) return;
        placing.value = true;
        selectedObjectId.value = null;
    }

    function resetDraft() {
        draft.type = '';
        draft.host_name = '';
        draft.service_description = '';
        draft.group_name = '';
        draft.board_name = '';
        draft.aggregation_id = '';
        draft.object_types = 'host';
        draft.object_filter = '';
        draft.expand_depth = 0;
        draft.label_text = '';
        draft.image_src = '';
        draft.graph_url = '';
    }

    async function placeAt(x: number, y: number) {
        if (!placing.value || !draft.type) return;
        placing.value = false;
        const s = useSettingsStore().settings;
        // Use crypto.randomUUID() to avoid collisions from rapid or concurrent placements.
        const id = `${draft.type}_${crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36)}`;
        const existing = boardsStore.currentBoard?.objects ?? [];
        const placePos =
            draft.type === 'line'
                ? { x: _snap(Math.round(x)), y: _snap(Math.round(y)) }
                : _avoidOverlap(id, Math.round(x), Math.round(y), existing);
        const obj: BoardObject = {
            id,
            type: draft.type,
            x: placePos.x,
            y: placePos.y,
            host_name: draft.host_name || undefined,
            service_description: draft.service_description || undefined,
            group_name: draft.group_name || undefined,
            map_name: draft.board_name || undefined,
            aggregation_id: draft.aggregation_id || undefined,
            object_types: draft.type === 'dyngroup' ? draft.object_types : undefined,
            object_filter: draft.type === 'dyngroup' ? draft.object_filter || undefined : undefined,
            expand_depth: draft.expand_depth || undefined,
            label: {
                show: s.label_show,
                text:
                    draft.label_text ||
                    (draft.type === 'image' && draft.image_src
                        ? (draft.image_src
                              .split('/')
                              .pop()
                              ?.replace(/\.[^/.]+$/, '') ?? null)
                        : null),
                x: 0,
                y: 0,
                size: s.label_size,
                color: s.label_color,
                background: s.label_background,
            },
            display:
                draft.type === 'line' || draft.type === 'graph'
                    ? null
                    : {
                          mode: s.view_type as 'icon' | 'text' | 'gadget',
                          image: draft.image_src || null,
                          image_size: null,
                      },
            image_src: draft.type === 'image' ? draft.image_src || null : undefined,
            url_target: s.url_target,
            z: s.z,
            ...(draft.type === 'line'
                ? {
                      x2: _snap(Math.round(x)) + 150,
                      y2: _snap(Math.round(y)),
                      line_style: s.line_style ?? 'plain',
                  }
                : {}),
            ...(draft.type === 'graph'
                ? {
                      graph_url: draft.graph_url || null,
                      graph_width: 400,
                      graph_height: 200,
                      graph_embed_type: 'img',
                      graph_refresh_interval: 0,
                  }
                : {}),
        };
        try {
            const newConfig = await boardsApi.addObject(mapName.value, obj, auth.accessToken!);
            if (boardsStore.currentBoard) boardsStore.currentBoard.objects = newConfig.objects;
            selectedObjectId.value = id;
            resetDraft();
        } catch (e) {
            console.error('Failed to add object', e);
        }
    }

    async function placeAtLatLng(lat: number, lng: number) {
        if (!placing.value || !draft.type) return;
        placing.value = false;
        const s = useSettingsStore().settings;
        const id = `${draft.type}_${crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36)}`;
        const obj: BoardObject = {
            id,
            type: draft.type,
            x: 0,
            y: 0,
            lat,
            lng,
            host_name: draft.host_name || undefined,
            service_description: draft.service_description || undefined,
            group_name: draft.group_name || undefined,
            map_name: draft.board_name || undefined,
            aggregation_id: draft.aggregation_id || undefined,
            object_types: draft.type === 'dyngroup' ? draft.object_types : undefined,
            object_filter: draft.type === 'dyngroup' ? draft.object_filter || undefined : undefined,
            expand_depth: draft.expand_depth || undefined,
            label: {
                show: s.label_show,
                text: draft.label_text || null,
                x: 0,
                y: 0,
                size: s.label_size,
                color: s.label_color,
                background: s.label_background,
            },
            display: {
                mode: s.view_type as 'icon' | 'text' | 'gadget',
                image: draft.image_src || null,
                image_size: null,
            },
            url_target: s.url_target,
            z: s.z,
            ...(draft.type === 'line' ? { lat2: lat + 2, lng2: lng + 4 } : {}),
        };
        try {
            const newConfig = await boardsApi.addObject(mapName.value, obj, auth.accessToken!);
            if (boardsStore.currentBoard) boardsStore.currentBoard.objects = newConfig.objects;
            selectedObjectId.value = id;
            resetDraft();
        } catch (e) {
            console.error('Failed to add object', e);
        }
    }

    async function moveObjectToLatLng(id: string, lat: number, lng: number, endpoint: 1 | 2 = 1) {
        const keys = endpoint === 2 ? ({ lat2: lat, lng2: lng } as const) : ({ lat, lng } as const);
        try {
            await boardsApi.updateObject(mapName.value, id, keys, auth.accessToken!);
            const obj = boardsStore.currentBoard?.objects.find((o) => o.id === id);
            if (obj) Object.assign(obj, keys);
        } catch (e) {
            console.error('Failed to save lat/lng', e);
            await onMapChange();
        }
    }

    function moveObjectToLatLng2(id: string, lat: number, lng: number) {
        return moveObjectToLatLng(id, lat, lng, 2);
    }

    function resetForNewMap() {
        editMode.value = false;
        selectedObjectId.value = null;
        placing.value = false;
        dragTarget.value = null;
        draft.type = '';
        draft.host_name = '';
        draft.service_description = '';
        draft.group_name = '';
        draft.board_name = '';
        draft.object_types = 'host';
        draft.object_filter = '';
        draft.label_text = '';
        draft.image_src = '';
        draft.graph_url = '';
        Object.keys(toRaw(lineDragPositions)).forEach((k) => delete lineDragPositions[k]);
    }

    async function deleteSelected() {
        const id = selectedObjectId.value;
        if (!id) return;
        selectedObjectId.value = null;
        try {
            await boardsApi.deleteObject(mapName.value, id, auth.accessToken!);
            if (boardsStore.currentBoard)
                boardsStore.currentBoard.objects = boardsStore.currentBoard.objects.filter(
                    (o) => o.id !== id,
                );
        } catch (e) {
            console.error('Failed to delete object', e);
            await onMapChange();
        }
    }

    async function duplicateSelected() {
        const id = selectedObjectId.value;
        if (!id || !boardsStore.currentBoard) return;
        const src = boardsStore.currentBoard.objects.find((o) => o.id === id);
        if (!src) return;
        const newId = `${src.type}_${crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36)}`;
        const clone: BoardObject = {
            ...JSON.parse(JSON.stringify(src)),
            id: newId,
            x: _snap(src.x + 30),
            y: _snap(src.y + 30),
        };
        if (clone.x2 !== undefined && clone.x2 !== null) {
            clone.x2 = (clone.x2 as number) + 30;
            clone.y2 = (clone.y2 as number) + 30;
        }
        try {
            const newConfig = await boardsApi.addObject(mapName.value, clone, auth.accessToken!);
            if (boardsStore.currentBoard) boardsStore.currentBoard.objects = newConfig.objects;
            selectedObjectId.value = newId;
        } catch (e) {
            console.error('Failed to duplicate object', e);
        }
    }

    function cancelPlacing() {
        placing.value = false;
    }

    return {
        editMode,
        toggleEditMode,
        selectedObjectId,
        selectObject,
        snapGrid,
        setDragSavedCallback,
        lineDragPositions,
        saveObjectPosition,
        startLineDrag,
        updateObjectProperties,
        placing,
        draft,
        resetDraft,
        startPlacing,
        placeAt,
        placeAtLatLng,
        moveObjectToLatLng,
        moveObjectToLatLng2,
        deleteSelected,
        duplicateSelected,
        cancelPlacing,
        resetForNewMap,
    };
}
