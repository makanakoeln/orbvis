// Maps a FastAPI 422 `detail` array to CMK FormSpec's
// `ValidationMessage` shape so per-field errors land on the right inputs.
import type { ValidationMessage } from 'cmk-shared-typing/typescript/vue_formspec_components';

interface PydanticError {
    loc: (string | number)[];
    msg: string;
    type?: string;
    input?: unknown;
    ctx?: Record<string, unknown>;
}

// Pydantic's BeforeValidator wraps raised ValueErrors as
// "Value error, <our message>" — strip so the field hint matches the FormSpec
// MatchRegex shown server-side.
function cleanMsg(m: string): string {
    return m.replace(/^Value error,\s*/, '');
}

export interface FormValidationResult {
    messages: ValidationMessage[];
    /** Errors whose top-level field is not in ``knownFields`` (or any error when
     *  ``knownFields`` is omitted, in which case nothing routes to FormEdit). */
    stray: ValidationMessage[];
    summary: string;
}

export function toFormValidation(
    detail: unknown,
    knownFields?: Set<string>,
): FormValidationResult | null {
    if (!Array.isArray(detail)) return null;
    const errs = detail as PydanticError[];
    const first = errs[0];
    if (
        first === undefined ||
        !errs.every((e) => Array.isArray(e?.loc) && typeof e?.msg === 'string')
    ) {
        return null;
    }
    const messages: ValidationMessage[] = [];
    const stray: ValidationMessage[] = [];
    for (const e of errs) {
        const location = e.loc.filter((s) => s !== 'body').map((s) => String(s));
        const item: ValidationMessage = {
            location,
            message: cleanMsg(e.msg),
            replacement_value: e.input ?? null,
        };
        const head = location[0];
        if (knownFields && (typeof head !== 'string' || !knownFields.has(head))) {
            stray.push(item);
        } else {
            messages.push(item);
        }
    }
    const field = first.loc.filter((s) => s !== 'body').join('.') || 'value';
    const summary = `${field}: ${cleanMsg(first.msg)}`;
    return { messages, stray, summary };
}
