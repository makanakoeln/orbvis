import { describe, expect, it } from 'vitest';

import type { BoardObject } from '@/types/api';

import { objectMatchesFilter } from './objectFilter';

function obj(over: Partial<BoardObject>): BoardObject {
    return {
        id: 'h1',
        type: 'host',
        x: 0,
        y: 0,
        z: 0,
        url_target: '_blank',
        ...over,
    } as BoardObject;
}

describe('objectMatchesFilter', () => {
    it('treats empty needle as a wildcard match', () => {
        expect(objectMatchesFilter(obj({}), '')).toBe(true);
        expect(objectMatchesFilter(obj({}), '   ')).toBe(true);
    });

    it('matches case-insensitively across host_name, service_description, group_name', () => {
        expect(objectMatchesFilter(obj({ host_name: 'WebSrv-01' }), 'websrv')).toBe(true);
        expect(
            objectMatchesFilter(obj({ type: 'service', service_description: 'CPU load' }), 'cpu'),
        ).toBe(true);
        expect(objectMatchesFilter(obj({ type: 'hostgroup', group_name: 'linux' }), 'LIN')).toBe(
            true,
        );
    });

    it('falls through to label.text when other fields are empty', () => {
        const o = obj({
            type: 'textbox',
            host_name: undefined,
            label: {
                show: true,
                text: 'Datacenter A',
                x: 0,
                y: 0,
                size: 11,
                color: '#fff',
                background: 'transparent',
            },
        });
        expect(objectMatchesFilter(o, 'datacenter')).toBe(true);
    });

    it('returns false when no field contains the needle', () => {
        expect(objectMatchesFilter(obj({ host_name: 'srv1' }), 'web')).toBe(false);
    });
});
