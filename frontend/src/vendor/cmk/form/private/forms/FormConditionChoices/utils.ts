/**
 * OrbVis stub — FormConditionChoices isn't part of the Pilot vocabulary.
 * FormReadonly imports these symbols but the `condition_choices` case is
 * never hit at runtime because OrbVis backends don't emit that type.
 */
import type { ConditionChoicesValue } from 'cmk-shared-typing/typescript/vue_formspec_components';

type KeysOfUnion<T> = T extends T ? keyof T : never;

export type Operator = KeysOfUnion<ConditionChoicesValue['value']>;

export type OperatorI18n = Record<string, string>;

export function translateOperator(_i18n: OperatorI18n, operator: Operator): string {
    return String(operator);
}
