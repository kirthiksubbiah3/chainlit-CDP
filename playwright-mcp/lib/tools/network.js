/**
 * Copyright (c) Microsoft Corporation.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 */
import { z } from 'zod';
import { defineTool } from './tool.js';
const requests = defineTool({
    capability: 'core',
    schema: {
        name: 'browser_network_requests',
        title: 'List network requests',
        description: 'Returns all network requests since loading the page. If headers are provided, returns only matching response headers like content-type, x-rid, etc.',
        inputSchema: z.object({
            headers: z.array(z.string()).optional(), // <-- This enables dynamic header filtering
        }),
        type: 'readOnly',
    },
    handle: async (context, input) => {
        const headerKeys = input.headers?.map(h => h.toLowerCase()) || [];
        const requests = context.currentTabOrDie().requests();
        const log = [...requests.entries()]
            .map(([request, response]) => renderRequest(request, response, headerKeys))
            .filter(Boolean)
            .join('\n\n');
        return {
            code: [`// Filtered network requests`],
            action: async () => ({
                content: [{ type: 'text', text: log || 'No matching API requests or headers found.' }],
            }),
            captureSnapshot: false,
            waitForNetwork: false,
        };
    },
});
function renderRequest(request, response, headerKeys) {
    if (!response)
        return '';
    const url = response.url();
    const headers = response.headers();
    // Only process API calls
    if (!url.includes('/api/'))
        return '';
    const matchedHeaders = headerKeys
        .map(key => {
        const val = headers[key];
        return val ? `${key}: ${val}` : null;
    })
        .filter(Boolean);
    if (headerKeys.length > 0 && matchedHeaders.length === 0)
        return ''; // skip if user asked for specific headers but none matched
    const result = [];
    result.push(`[${request.method().toUpperCase()}] ${url}`);
    result.push(`=> [${response.status()}] ${response.statusText()}`);
    if (matchedHeaders.length > 0) {
        result.push('Matching Headers:\n' + matchedHeaders.join('\n'));
    }
    else {
        // If no specific headers requested, show all
        result.push('No Headers in the input');
    }
    return result.join('\n');
}
export default [requests];
