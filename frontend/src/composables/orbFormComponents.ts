/**
 * OrbVis-specific FormSpec widgets, registered alongside the vendored
 * CMK component set. Passing this map to ``initializeComponentRegistry``
 * keeps the vendored ``dispatch.ts`` file identical to upstream CMK,
 * so the drift-check stays clean and CMK updates merge without
 * conflicts.
 *
 * Type tags here must match the ``type`` field emitted by the matching
 * Python visitor in ``backend/app/form_specs/_visitors.py``.
 */
import FormOrbColor from '@cmk/form/private/forms/FormOrbColor.vue';
import { type Component } from 'vue';

export const orbFormComponents: Record<string, Component> = {
    // type tag emitted by ``OrbColorStringVisitor`` — a String with a
    // native color picker swap in the frontend.
    orb_color: FormOrbColor,
};
