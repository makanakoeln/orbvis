import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import NumberInput from './NumberInput.vue';

describe('NumberInput', () => {
    it('emits the raw value during typing without clamping', async () => {
        // A partial value like "1" must survive while the user is still
        // typing — clamping mid-keystroke caused values to jump to min/max
        // before the operator could finish (e.g. typing "11" → became "81"
        // → clamped to max).
        const wrapper = mount(NumberInput, {
            props: { modelValue: 50, min: 8, max: 72 },
        });
        const input = wrapper.find('input');
        (input.element as HTMLInputElement).value = '1';
        await input.trigger('input');
        const events = wrapper.emitted('update:modelValue')!;
        expect(events.at(-1)).toEqual([1]);
    });

    it('clamps to max on commit (blur/change)', async () => {
        const wrapper = mount(NumberInput, {
            props: { modelValue: 5, max: 20 },
        });
        const input = wrapper.find('input');
        await input.setValue('200');
        await input.trigger('blur');
        const events = wrapper.emitted('update:modelValue')!;
        expect(events.at(-1)).toEqual([20]);
    });

    it('clamps to min on commit (blur/change)', async () => {
        const wrapper = mount(NumberInput, {
            props: { modelValue: 5, min: 1 },
        });
        const input = wrapper.find('input');
        await input.setValue('-50');
        await input.trigger('blur');
        const events = wrapper.emitted('update:modelValue')!;
        expect(events.at(-1)).toEqual([1]);
    });

    it('passes through valid values within range', async () => {
        const wrapper = mount(NumberInput, {
            props: { modelValue: 5, min: 1, max: 20 },
        });
        await wrapper.find('input').setValue('12');
        const events = wrapper.emitted('update:modelValue')!;
        expect(events.at(-1)).toEqual([12]);
    });

    it('emits null on empty input', async () => {
        const wrapper = mount(NumberInput, {
            props: { modelValue: 5 },
        });
        await wrapper.find('input').setValue('');
        const events = wrapper.emitted('update:modelValue')!;
        expect(events.at(-1)).toEqual([null]);
    });
});
