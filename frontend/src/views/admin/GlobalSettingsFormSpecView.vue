<template>
    <div class="settings-page">
        <Transition
            enter-from-class="settings-page__savebar--enter-from"
            enter-active-class="settings-page__savebar--enter-active"
            leave-to-class="settings-page__savebar--leave-to"
            leave-active-class="settings-page__savebar--leave-active"
        >
            <CmkAlertBox
                v-if="!loading && schema && saveBarState !== 'clean'"
                class="settings-page__savebar"
                :variant="saveBarVariant"
                size="small"
                :heading="saveBarHeading"
            >
                <div v-if="saveBarHasActions" class="settings-page__savebar-actions">
                    <CmkButton variant="optional" :disabled="saving" @click="resetForm">
                        {{ t('common.cancel') }}
                    </CmkButton>
                    <CmkButton variant="primary" :disabled="saving" @click="handleSave">
                        {{ saving ? t('common.saving') : t('common.save') }}
                    </CmkButton>
                </div>
            </CmkAlertBox>
        </Transition>

        <header class="settings-page__header">
            <CmkHeading type="h2">{{ heading }}</CmkHeading>
            <CmkParagraph v-if="subtitle" class="admin-subtitle">{{ subtitle }}</CmkParagraph>
        </header>

        <div v-if="loading" class="flex items-center justify-center py-16">
            <CmkLoading />
        </div>

        <CmkAlertBox v-else-if="loadError" variant="error">{{ loadError }}</CmkAlertBox>

        <div v-else-if="schema" class="settings-page__layout">
            <nav class="settings-page__sidebar" aria-label="Settings sections">
                <button
                    v-for="g in sidebarGroups"
                    :key="g.key"
                    type="button"
                    class="settings-page__topic"
                    :class="{ 'settings-page__topic--active': g.key === activeGroup }"
                    @click="activeGroup = g.key"
                >
                    <span class="settings-page__topic-title">{{ g.title }}</span>
                    <span
                        v-if="g.modified > 0"
                        class="settings-page__topic-badge"
                        :title="t('settings.modifiedHint', { n: g.modified })"
                    >
                        {{ g.modified }}
                    </span>
                </button>
            </nav>

            <div class="settings-page__detail" :data-active="activeGroup">
                <FormEdit v-model:data="data" :spec="schema" :backend-validation="validation" />
            </div>
        </div>

        <OrbUnsavedChangesDialog
            :open="leaveDialogOpen"
            @confirm="confirmLeave"
            @cancel="cancelLeave"
        />
    </div>
</template>

<script setup lang="ts">
import FormEdit from '@cmk/form/FormEdit.vue';
import type { VueFormspecComponents } from 'cmk-shared-typing/typescript/vue_formspec_components';
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { ApiError, settingsApi } from '@/api/client';
import CmkAlertBox from '@/components/cmk/CmkAlertBox';
import CmkButton from '@/components/cmk/CmkButton';
import CmkLoading from '@/components/cmk/CmkLoading';
import CmkHeading from '@/components/cmk/typography/CmkHeading';
import CmkParagraph from '@/components/cmk/typography/CmkParagraph';
import OrbUnsavedChangesDialog from '@/components/OrbUnsavedChangesDialog.vue';
import { useFormSpecSchema } from '@/composables/useFormSpecSchema';
import { useSaveBarState } from '@/composables/useSaveBarState';
import { useUnsavedChangesGuard } from '@/composables/useUnsavedChangesGuard';
import { useAuthStore } from '@/stores/auth';

type Validation = NonNullable<VueFormspecComponents['validation_message']>[];

interface SchemaElement {
    name: string;
    required?: boolean;
    group?: { key?: string | null; title?: string | null } | null;
    default_value?: unknown;
    parameter_form?: { title?: string };
}
interface DictionarySchema {
    elements?: SchemaElement[];
    title?: string;
    help?: string;
}

// Backend emits one DictGroup per section. Object-related sub-groups are
// rolled up into a single sidebar entry "Object defaults" so the operator
// sees one entry instead of three; the FormDictionary still renders the
// three sub-headings underneath for visual hierarchy.
const OBJECT_SUB_GROUPS = new Set(['object_appearance', 'object_labels', 'object_templates']);
const OBJECT_VIRTUAL_KEY = 'object_defaults';

// structuredClone fails on Vue's reactive proxies. Settings payloads are
// pure JSON (string/number/boolean/array/object), so a stringify round-trip
// is both safe and works on the proxied refs.
function deepClone<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T;
}

const { t } = useI18n();
const auth = useAuthStore();

const {
    schema,
    error: schemaError,
    load: loadSchema,
} = useFormSpecSchema('settings', () => settingsApi.getSchema(auth.accessToken ?? ''));

const loading = ref(true);
const loadError = ref('');
const saving = ref(false);
const saveError = ref('');
const savedOk = ref(false);
const data = ref<unknown>({});
const initialData = ref<unknown>({});
const validation = ref<Validation>([]);
const activeGroup = ref<string>('');

let savedOkTimer: ReturnType<typeof setTimeout> | null = null;
let saveErrorTimer: ReturnType<typeof setTimeout> | null = null;

const dirty = computed(() => JSON.stringify(data.value) !== JSON.stringify(initialData.value));

const heading = computed(
    () => (schema.value as DictionarySchema | null)?.title ?? t('settings.title'),
);
const subtitle = computed(
    () => (schema.value as DictionarySchema | null)?.help || t('settings.subtitle'),
);

function sidebarKey(rawKey: string): string {
    return OBJECT_SUB_GROUPS.has(rawKey) ? OBJECT_VIRTUAL_KEY : rawKey;
}

const sidebarGroups = computed<{ key: string; title: string; modified: number }[]>(() => {
    const dict = schema.value as DictionarySchema | null;
    if (!dict?.elements) return [];
    const cur = (data.value ?? {}) as Record<string, unknown>;
    const orig = (initialData.value ?? {}) as Record<string, unknown>;
    const acc = new Map<string, { title: string; modified: number }>();
    for (const el of dict.elements) {
        const rawKey = el.group?.key ?? '-ungrouped-';
        const key = sidebarKey(rawKey);
        const title =
            key === OBJECT_VIRTUAL_KEY ? t('settings.objectDefaults') : el.group?.title || rawKey;
        const entry = acc.get(key) ?? { title, modified: 0 };
        const here = el.name in cur;
        const before = el.name in orig;
        if (
            here !== before ||
            (here && JSON.stringify(cur[el.name]) !== JSON.stringify(orig[el.name]))
        ) {
            entry.modified += 1;
        }
        acc.set(key, entry);
    }
    return Array.from(acc.entries()).map(([key, v]) => ({
        key,
        title: v.title,
        modified: v.modified,
    }));
});

async function load() {
    const token = auth.accessToken;
    if (!token) {
        loadError.value = 'Not authenticated';
        loading.value = false;
        return;
    }
    try {
        const [, values] = await Promise.all([loadSchema(), settingsApi.getForm(token)]);
        if (schemaError.value) {
            loadError.value = schemaError.value;
            return;
        }
        initialData.value = deepClone(values);
        data.value = deepClone(values);
        // pre-select first group so the detail panel is never empty
        activeGroup.value = sidebarGroups.value[0]?.key ?? '';
    } catch (e: unknown) {
        loadError.value = e instanceof Error ? e.message : 'Failed to load settings';
    } finally {
        loading.value = false;
    }
}

function resetForm() {
    data.value = deepClone(initialData.value);
    savedOk.value = false;
    saveError.value = '';
}

/* ── Factory defaults ───────────────────────────────────────────────────── */
/*  Compute which top-level fields currently differ from the FormSpec
    ``prefill`` (i.e. the factory default). Used to render a small dot beside
    the field title and a per-field reset button next to it. Per-field reset
    is wired DOM-side (rather than via the vendored FormDictionary template)
    to keep the cmk-frontend-vue vendor copy untouched. */
const factoryDefaults = computed<Record<string, unknown>>(() => {
    const dict = schema.value as DictionarySchema | null;
    const out: Record<string, unknown> = {};
    for (const el of dict?.elements ?? []) {
        if ('default_value' in el) out[el.name] = el.default_value;
    }
    return out;
});

const factoryDiffByTitle = computed<Map<string, string>>(() => {
    const cur = (data.value ?? {}) as Record<string, unknown>;
    const dict = schema.value as DictionarySchema | null;
    const m = new Map<string, string>();
    for (const el of dict?.elements ?? []) {
        if (!('default_value' in el)) continue;
        // Optional DictElements (no ``required=True``, prefilled with
        // ``InputHint``) ship with the checkbox off — the live payload
        // simply omits the key. The schema still emits ``default_value: ""``
        // as the hint placeholder, so a present key with empty value would
        // wrongly compare equal. Drive the comparison off key-presence
        // instead: factory state is "key absent" for these fields, so
        // enabling the checkbox at all counts as a modification.
        const optionalUnset = el.required === false;
        const here = cur[el.name];
        const factory = factoryDefaults.value[el.name];
        if (optionalUnset) {
            if (!(el.name in cur)) continue; // checkbox stayed off → unchanged
            // checkbox on (even with empty value) → modified
        } else if (JSON.stringify(here) === JSON.stringify(factory)) {
            continue;
        }
        const title = el.parameter_form?.title;
        if (title) m.set(title, el.name);
    }
    return m;
});

function resetFieldToFactory(name: string) {
    const dict = schema.value as DictionarySchema | null;
    const el = dict?.elements?.find((e) => e.name === name);
    const factory = factoryDefaults.value[name];
    const next = { ...(data.value as Record<string, unknown>) };
    // Optional fields reset to "checkbox off" (key absent), not to the empty
    // InputHint placeholder.
    if (factory === undefined || el?.required === false) {
        delete next[name];
    } else {
        next[name] = deepClone(factory);
    }
    data.value = next;
}

async function syncFactoryDecorations() {
    await nextTick();
    const root = document.querySelector('.settings-page__detail');
    if (!root) return;
    const diff = factoryDiffByTitle.value;
    for (const el of root.querySelectorAll<HTMLElement>('.form-dictionary__group_elem')) {
        const title = el.getAttribute('aria-label') ?? '';
        const fieldName = diff.get(title);
        const labelHost = el.querySelector<HTMLElement>('.cmk-label__container .cmk-label--nowrap');
        const existing = el.querySelector('.orb-factory-reset');
        if (fieldName && labelHost) {
            el.classList.add('orb-factory-modified');
            if (!existing) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'orb-factory-reset';
                btn.dataset.name = fieldName;
                btn.title = t('settings.resetToFactory');
                btn.textContent = '↺';
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const n = (e.currentTarget as HTMLElement).dataset.name;
                    if (n) resetFieldToFactory(n);
                });
                labelHost.appendChild(btn);
            } else if (existing.parentElement !== labelHost) {
                labelHost.appendChild(existing);
            }
        } else {
            el.classList.remove('orb-factory-modified');
            existing?.remove();
        }
    }
}

watch([factoryDiffByTitle, activeGroup, () => loading.value], () => {
    void syncFactoryDecorations();
});

// FastAPI 422 returns `{ detail: [{ loc: ["body", "<field>", ...], msg, type, input, ctx }] }`.
// FormEdit expects `{ location: [<field>, ...], message, replacement_value }` and uses the
// location array to highlight the matching nested dict element. Strip the leading "body"
// segment and pull the input back through as the replacement value so the field re-renders
// with the rejected text instead of snapping back to the previous saved value.
interface PydanticError {
    loc: (string | number)[];
    msg: string;
    type?: string;
    input?: unknown;
    ctx?: Record<string, unknown>;
}
function toFormValidation(detail: unknown): { messages: Validation; summary: string } | null {
    if (!Array.isArray(detail)) return null;
    const errs = detail as PydanticError[];
    if (!errs.length || !errs.every((e) => Array.isArray(e?.loc) && typeof e?.msg === 'string')) {
        return null;
    }
    // Pydantic's BeforeValidator wraps the raised ValueError as
    // "Value error, <our message>" — strip that prefix so the field-level
    // hint matches what the FormSpec MatchRegex shows server-side.
    const clean = (m: string): string => m.replace(/^Value error,\s*/, '');
    const messages: Validation = errs.map((e) => ({
        location: e.loc.filter((s) => s !== 'body').map((s) => String(s)),
        message: clean(e.msg),
        replacement_value: e.input ?? null,
    }));
    const first = errs[0];
    const field = first.loc.filter((s) => s !== 'body').join('.') || 'value';
    return { messages, summary: t('settings.validationFailed', { field, msg: clean(first.msg) }) };
}

async function handleSave() {
    const token = auth.accessToken;
    if (!token) return;
    saving.value = true;
    saveError.value = '';
    savedOk.value = false;
    validation.value = [];
    try {
        const updated = await settingsApi.updateForm(data.value as Record<string, unknown>, token);
        initialData.value = deepClone(updated);
        data.value = deepClone(updated);
        savedOk.value = true;
        if (savedOkTimer) clearTimeout(savedOkTimer);
        savedOkTimer = setTimeout(() => {
            savedOk.value = false;
        }, 3000);
    } catch (e: unknown) {
        if (e instanceof ApiError && e.status === 422) {
            // ApiError.detail is the raw body { detail: PydanticError[] | string }
            const body = (e.detail as { detail?: unknown } | null)?.detail;
            const parsed = toFormValidation(body);
            if (parsed) {
                validation.value = parsed.messages;
                saveError.value = parsed.summary;
                // jump to the first sidebar group that contains the invalid field
                const dict = schema.value as DictionarySchema | null;
                const firstField = parsed.messages[0]?.location[0];
                if (dict?.elements && firstField) {
                    const el = dict.elements.find((x) => x.name === firstField);
                    const rawKey = el?.group?.key ?? '';
                    if (rawKey) activeGroup.value = sidebarKey(rawKey);
                }
            } else {
                saveError.value = e.message;
            }
        } else {
            saveError.value = e instanceof Error ? e.message : t('admin.saveFailed');
        }
        if (saveErrorTimer) clearTimeout(saveErrorTimer);
        saveErrorTimer = setTimeout(() => {
            saveError.value = '';
        }, 8000);
    } finally {
        saving.value = false;
    }
}

const { dialogOpen: leaveDialogOpen, confirmLeave, cancelLeave } = useUnsavedChangesGuard(dirty);

const {
    state: saveBarState,
    variant: saveBarVariant,
    hasActions: saveBarHasActions,
    heading: saveBarHeading,
} = useSaveBarState({ dirty, saving, savedOk, error: saveError });

onMounted(load);

onUnmounted(() => {
    if (savedOkTimer) clearTimeout(savedOkTimer);
    if (saveErrorTimer) clearTimeout(saveErrorTimer);
});
</script>

<style scoped>
.settings-page {
    display: flex;
    flex-direction: column;
    min-height: 100%;
}

.settings-page__header {
    padding: var(--dimension-7) var(--dimension-8) var(--dimension-6);
}

/* `.settings-page__savebar` is added directly onto the CmkAlertBox root
   via Vue's class-fallthrough — turns the box into a sticky page-top
   notification and flips its heading+body stack to a row so action
   buttons sit inline right of the heading. */
.settings-page__savebar {
    position: sticky;
    top: 0;
    z-index: 6;
    margin: 0;
}

/* CmkAlertBox renders each variant's tint at 25-50 % alpha (mixed onto
   ``transparent``), which lets scrolled page content show through the sticky
   bar. Re-flatten every variant onto the page background so the hue stays
   visible while the bar becomes fully opaque. */
.settings-page__savebar.cmk-alert-box--warning {
    background-color: color-mix(in srgb, var(--color-yellow-50) 25%, var(--bg));
}

.settings-page__savebar.cmk-alert-box--error {
    background: color-mix(in srgb, var(--color-dark-red-50) 50%, var(--bg));
}

.settings-page__savebar.cmk-alert-box--success {
    background: color-mix(in srgb, var(--color-corporate-green-50) 25%, var(--bg));
}

.settings-page__savebar.cmk-alert-box--info,
.settings-page__savebar.cmk-alert-box--loading {
    background-color: color-mix(in srgb, var(--color-dark-blue-50) 25%, var(--bg));
}

.settings-page__savebar :deep(.cmk-alert-box__text) {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: var(--dimension-5);
}

.settings-page__savebar :deep(.cmk-alert-box__body) {
    margin-left: auto;
}

.settings-page__savebar-actions {
    display: flex;
    align-items: center;
    gap: var(--dimension-3);
}

/* Shrink the buttons one notch (32 → 28 px) so they don't crowd the
   compact alert bar — keeps Cancel/Save visually below the heading line. */
.settings-page__savebar :deep(.cmk-button) {
    height: var(--dimension-9);
}

.settings-page__savebar--enter-from,
.settings-page__savebar--leave-to {
    opacity: 0;
    transform: translateY(-6px);
}

.settings-page__savebar--enter-active,
.settings-page__savebar--leave-active {
    transition:
        opacity 180ms ease-out,
        transform 180ms ease-out;
}

.settings-page__layout {
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: var(--dimension-7);
    padding: 0 var(--dimension-8);
    flex: 1;
    align-items: start;
    min-height: 0;
}

/* Factory-default decorations — applied via DOM by syncFactoryDecorations().
   The dot sits before the field title so the operator can spot which fields
   they've moved away from the shipped defaults at a glance; the small ↺
   button next to the label reverts that single field. */
.settings-page__detail
    :deep(.form-dictionary__group_elem.orb-factory-modified > .cmk-label__container),
.settings-page__detail
    :deep(.form-dictionary__group_elem.orb-factory-modified > .cmk-checkbox__container) {
    display: inline-flex;
    align-items: center;
}

.settings-page__detail
    :deep(.form-dictionary__group_elem.orb-factory-modified > .cmk-label__container::before),
.settings-page__detail
    :deep(.form-dictionary__group_elem.orb-factory-modified > .cmk-checkbox__container::before) {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--color-warning, #ffd000);
    margin-right: 5px;
    flex-shrink: 0;
}

.settings-page__detail :deep(.orb-factory-reset) {
    margin-left: 6px;
    width: 18px;
    height: 18px;
    padding: 0;
    border: 1px solid transparent;
    border-radius: 4px;
    background: transparent;
    color: var(--font-color, #fff);
    font-size: 14px;
    line-height: 1;
    cursor: pointer;
    vertical-align: middle;
}

.settings-page__detail :deep(.orb-factory-reset:hover) {
    color: var(--color-warning, #ffd000);
    border-color: var(--color-warning, #ffd000);
}

/* Topic sidebar — WATO-style vertical nav with active-state highlight. */
.settings-page__sidebar {
    display: flex;
    flex-direction: column;
    gap: 2px;
    position: sticky;
    top: 0;
    align-self: start;
}

.settings-page__topic {
    text-align: left;
    background: none;
    border: 0;
    border-left: 3px solid transparent;
    padding: var(--dimension-3) var(--dimension-5);
    font-size: 14px;

    /* CMK's theme-aware dimmed-text token — readable on both the dark
       surface and the white light-theme sidebar. */
    color: var(--font-color-dimmed, var(--text-muted));
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--dimension-3);
    transition:
        background-color 120ms,
        color 120ms,
        border-color 120ms;
}

.settings-page__topic-title {
    flex: 1;
    min-width: 0;
}

.settings-page__topic-badge {
    flex-shrink: 0;
    min-width: 20px;
    height: 18px;
    padding: 0 6px;
    border-radius: 9px;
    font-size: 11px;
    font-weight: 600;
    line-height: 18px;
    text-align: center;
    background: var(--color-corporate-green-50);
    color: var(--bg-surface);
}

.settings-page__topic:hover {
    background: var(--bg-hover, rgb(127 127 127 / 8%));
    color: var(--font-color, var(--text));
}

.settings-page__topic--active {
    border-left-color: var(--color-corporate-green-50);
    background: rgb(21 209 160 / 12%);
    color: var(--font-color, var(--text));
    font-weight: 600;
}

/* Hide every TOP-level group <tr> by default, then re-show the active
   sidebar group's row(s). Match by exact group key — the nested
   FormDictionary inside ``labels.shown`` would otherwise also be hit
   (it uses ``-ungrouped-N`` keys for its inner fields) and its rows
   would vanish. Vue's :deep() weakens specificity, so we hoist this
   rule with !important; the alternative (v-show inside the vendored
   FormDictionary) would require a bigger vendor patch. */
.settings-page__detail :deep(tr[data-group='board_defaults']),
.settings-page__detail :deep(tr[data-group='object_appearance']),
.settings-page__detail :deep(tr[data-group='object_labels']),
.settings-page__detail :deep(tr[data-group='object_templates']) {
    display: none !important;
}

.settings-page__detail[data-active='board_defaults'] :deep(tr[data-group='board_defaults']),
.settings-page__detail[data-active='object_defaults'] :deep(tr[data-group='object_appearance']),
.settings-page__detail[data-active='object_defaults'] :deep(tr[data-group='object_labels']),
.settings-page__detail[data-active='object_defaults'] :deep(tr[data-group='object_templates']) {
    display: table-row !important;
}

/* Visual divider between Object-defaults sub-sections (Appearance,
   Labels, Templates). CMK upstream's FormDictionary separates groups
   with whitespace only — fine for one or two short groups, but the
   three sub-sections in Object defaults are noticeably different
   lengths and benefit from an explicit hairline. Matches the WATO
   look (border-top + padding) without introducing a new container
   component. The nested FormDictionary inside ``labels.shown`` uses
   ``-ungrouped-N`` keys and is excluded by the exact-match selectors.
   Vue's :deep() doesn't accept comma-separated selectors as a single
   argument, so each :deep(...) wraps exactly one selector. */
.settings-page__detail[data-active='object_defaults'] :deep(tr[data-group='object_labels'] > td),
.settings-page__detail[data-active='object_defaults']
    :deep(tr[data-group='object_templates'] > td) {
    border-top: 1px solid rgb(255 255 255 / 12%);
    padding-top: var(--dimension-6);
}

/* Pad each section's bottom so subsequent dividers don't sit flush
   against the last input row. */
.settings-page__detail[data-active='object_defaults']
    :deep(tr[data-group='object_appearance'] > td),
.settings-page__detail[data-active='object_defaults'] :deep(tr[data-group='object_labels'] > td),
.settings-page__detail[data-active='object_defaults']
    :deep(tr[data-group='object_templates'] > td) {
    padding-bottom: var(--dimension-6);
}

/* When a sidebar entry maps 1:1 to a single group, hide the inline
   title — the sidebar already shows "Board defaults". For "Object
   defaults" the inline titles ("Appearance", "Labels", "Templates")
   stay because they're distinct sub-headings within one sidebar entry. */
.settings-page__detail[data-active='board_defaults']
    :deep(tr[data-group='board_defaults'] .form-dictionary__group-title) {
    display: none;
}

/* Bigger group title (h3-ish) and visible help line under it, since the
   sidebar already establishes the section context. */
.settings-page__detail :deep(.form-dictionary__group-title) {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: var(--dimension-2);
    padding: 0;
    border: 0;
}

.settings-page__detail :deep(.form-help) {
    color: var(--text-muted);
    margin-bottom: var(--dimension-6);
}

/* Consistent input width — kills the "60px Integer next to 432px String" mix. */
.settings-page__detail :deep(.cmk-input--text),
.settings-page__detail :deep(.cmk-dropdown__choice-button),
.settings-page__detail :deep(input[type='text']) {
    min-width: 320px;
    max-width: 100%;
}

.settings-page__error-msg {
    font-size: 13px;
    color: var(--color-light-red-40);
}
</style>
