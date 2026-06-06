/**
 * OrbVis-specific FormSpec widgets, registered alongside the vendored
 * CMK component set. Passing this map to ``initializeComponentRegistry``
 * gives downstream consumers two extension points without touching the
 * vendored tree:
 *
 *   * **New types** — the entry's key is a fresh ``type`` tag emitted by
 *     an OrbVis Python visitor (e.g. ``orb_color``).
 *   * **Overrides** — re-using an upstream tag (e.g. ``boolean_choice``)
 *     swaps the default component for an OrbVis re-implementation. The
 *     dispatcher's ``{ ...components, ...extra }`` order makes the
 *     override win.
 */
import FormOrbColor from '@/cmk-additions/form/private/forms/FormOrbColor.vue'
import FormOrbHostAutocomplete from '@/cmk-additions/form/private/forms/FormOrbHostAutocomplete.vue'
import { type Component } from 'vue'

import FormBooleanChoice from '@/cmk-stubs/FormBooleanChoice.vue'
import FormMultilineText from '@/cmk-stubs/FormMultilineText.vue'

export const orbFormComponents: Record<string, Component> = {
  // type tag emitted by ``OrbColorStringVisitor`` — a String with a
  // native color picker swap in the frontend.
  orb_color: FormOrbColor,
  // type tag emitted by ``OrbHostStringVisitor`` — a String that
  // pulls host-name suggestions from the parent modal's connection_id
  // (provided via inject('orbConnectionId')).
  orb_host_autocomplete: FormOrbHostAutocomplete,
  // Override upstream's CmkCheckbox-based boolean form with a
  // CmkSwitch-based one — OrbVis BooleanChoices are always state
  // toggles, not accept/confirm checkboxes.
  boolean_choice: FormBooleanChoice,
  // Override upstream's bare-<textarea> multiline-text form so the
  // OrbVis dark theme renders it legibly — the upstream component
  // picks up no theme background/border.
  multiline_text: FormMultilineText
}
