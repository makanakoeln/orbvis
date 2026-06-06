/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fetchRestAPI } from '@cmk/lib/cmkFetch';

import { API_ROOT } from '@cmk/lib/rest-api-client/constants';

const DISMISS_WARNING_API = `${API_ROOT}/domain-types/user_config/actions/dismiss-warning/invoke`;

export async function persistWarningDismissal(warning: string) {
    await fetchRestAPI(DISMISS_WARNING_API, 'POST', { warning: warning });
}
