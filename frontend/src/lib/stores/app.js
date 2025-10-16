import { derived, writable } from 'svelte/store';

export const messages = writable([]);
export const graphData = writable({ nodes: [], links: [] });
export const stats = writable(null);
export const viewMode = writable('split');
export const isLoading = writable(false);
export const isIngesting = writable(false);
export const ingestStatus = writable(null);

export const currentEntities = derived(messages, ($messages) => {
  const last = $messages[$messages.length - 1];
  return last?.entities ?? [];
});

export const hasConversation = derived(messages, ($messages) => $messages.length > 0);
