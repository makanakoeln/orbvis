/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * Vendored from cmk-frontend-vue; OrbVis Pilot subset (no autocompleter,
 * no levels, no Catalog/DualList/etc.).
 *
 * The OrbVis-only extension is opt-in via the ``extra`` parameter of
 * ``initializeComponentRegistry`` — downstream consumers pass their own
 * type→component map without editing this vendored file. See
 * ``frontend/src/composables/orbFormComponents.ts`` for the OrbVis map.
 */
import { type Component } from 'vue';

import FormBooleanChoice from '@cmk/form/private/forms/FormBooleanChoice.vue';
import FormCascadingSingleChoice from '@cmk/form/private/forms/FormCascadingSingleChoice.vue';
import FormDictionary from '@cmk/form/private/forms/FormDictionary/FormDictionary.vue';
import FormFixedValue from '@cmk/form/private/forms/FormFixedValue.vue';
import FormFloat from '@cmk/form/private/forms/FormFloat.vue';
import FormInteger from '@cmk/form/private/forms/FormInteger.vue';
import FormMultilineText from '@cmk/form/private/forms/FormMultilineText.vue';
import FormPassword from '@cmk/form/private/forms/FormPassword.vue';
import FormSingleChoice from '@cmk/form/private/forms/FormSingleChoice.vue';
import FormString from '@cmk/form/private/forms/FormString.vue';

import { setComponentRegistry } from '@cmk/form/private/FormEditDispatcher/componentRegistry';

const components: Record<string, Component> = {
    boolean_choice: FormBooleanChoice,
    cascading_single_choice: FormCascadingSingleChoice,
    dictionary: FormDictionary,
    fixed_value: FormFixedValue,
    float: FormFloat,
    integer: FormInteger,
    multiline_text: FormMultilineText,
    password: FormPassword,
    single_choice: FormSingleChoice,
    string: FormString,
};

export function initializeComponentRegistry(extra: Record<string, Component> = {}) {
    setComponentRegistry({ ...components, ...extra });
}

export { getComponent } from '@cmk/form/private/FormEditDispatcher/componentRegistry';
