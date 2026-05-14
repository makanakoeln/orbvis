/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * Vendored from cmk-frontend-vue; OrbVis Pilot subset (no autocompleter,
 * no levels, no Catalog/DualList/etc.). When new FormSpec types are added
 * to OrbVis, also add the matching import and registry entry here.
 */
import { type Component } from 'vue';

import FormBooleanChoice from '@/form/private/forms/FormBooleanChoice.vue';
import FormDictionary from '@/form/private/forms/FormDictionary/FormDictionary.vue';
import FormFloat from '@/form/private/forms/FormFloat.vue';
import FormInteger from '@/form/private/forms/FormInteger.vue';
import FormSingleChoice from '@/form/private/forms/FormSingleChoice.vue';
import FormString from '@/form/private/forms/FormString.vue';

import { setComponentRegistry } from './componentRegistry';

const components: Record<string, Component> = {
    boolean_choice: FormBooleanChoice,
    dictionary: FormDictionary,
    float: FormFloat,
    integer: FormInteger,
    single_choice: FormSingleChoice,
    string: FormString,
};

export function initializeComponentRegistry() {
    setComponentRegistry(components);
}

export { getComponent } from './componentRegistry';
