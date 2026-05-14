import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import NumberInput from './NumberInput.vue';

describe('NumberInput', () => {
    it('clamps direct user input to max', async () => {
        const wrapper = mount(NumberInput, {
            props: { modelValue: 5, max: 20 },
        });
        const input = wrapper.find('input');
        await input.setValue('200');
        const events = wrapper.emitted('update:modelValue');
        expect(events).toBeTruthy();
        expect(events!.at(-1)).toEqual([20]);
    });

    it('clamps direct user input to min', async () => {
        const wrapper = mount(NumberInput, {
            props: { modelValue: 5, min: 1 },
        });
        await wrapper.find('input').setValue('-50');
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
