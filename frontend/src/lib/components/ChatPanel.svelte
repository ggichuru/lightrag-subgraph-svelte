<script>
  import { onDestroy, onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { graphData, isLoading, messages, stats } from '../stores/app.js';
  import { createWebSocket, loadStats, sendQuery } from '../utils/api.js';

  let input = '';
  let mode = 'hybrid';
  let connectionStatus = 'connecting';
  let socket;

  const modes = ['naive', 'local', 'global', 'hybrid', 'mix'];

  const buildHistoryPayload = () =>
    $messages.map(({ role, content, entities }) => ({ role, content, entities })).slice(-10);

  function appendMessage(message) {
    messages.update((current) => [...current, message]);
  }

  function updateLastAssistant(updater) {
    messages.update((current) => {
      const clone = [...current];
      const index = clone.map((msg) => msg.role).lastIndexOf('assistant');
      const previous = index >= 0 ? clone[index] : { role: 'assistant', content: '', entities: [] };
      const next = typeof updater === 'function' ? updater(previous) : { ...previous, ...updater };
      if (index >= 0) {
        clone[index] = next;
      } else {
        clone.push({ role: 'assistant', ...next });
      }
      return clone;
    });
  }

  async function refreshStats() {
    try {
      const payload = await loadStats();
      stats.set(payload);
    } catch (error) {
      console.error('Failed to load stats', error);
    }
  }

  function handleSocketMessage(event) {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === 'response') {
        updateLastAssistant({ content: payload.response, entities: payload.entities ?? [] });
        if (payload.graph) {
          graphData.set(payload.graph);
        }
        refreshStats();
        isLoading.set(false);
      } else if (payload.type === 'response_chunk') {
        updateLastAssistant((prev) => ({ ...prev, content: `${prev.content}${payload.chunk}` }));
        if (payload.done) {
          isLoading.set(false);
        }
      } else if (payload.type === 'error') {
        updateLastAssistant({ content: `Error: ${payload.error}`, entities: [] });
        isLoading.set(false);
      }
    } catch (error) {
      console.error('Unable to parse websocket payload', error);
    }
  }

  function connectSocket() {
    try {
      socket = createWebSocket();
      socket.addEventListener('open', () => {
        connectionStatus = 'connected';
      });
      socket.addEventListener('close', () => {
        connectionStatus = 'disconnected';
      });
      socket.addEventListener('error', () => {
        connectionStatus = 'error';
      });
      socket.addEventListener('message', handleSocketMessage);
    } catch (error) {
      console.error('WebSocket connection failed', error);
      connectionStatus = 'error';
    }
  }

  onMount(() => {
    connectSocket();
  });

  onDestroy(() => {
    socket?.close();
  });

  async function handleSubmit() {
    const trimmed = input.trim();
    if (!trimmed) return;

    const timestamp = new Date().toISOString();
    appendMessage({ role: 'user', content: trimmed, entities: [], timestamp });
    appendMessage({ role: 'assistant', content: '...', entities: [], timestamp });
    isLoading.set(true);

    const historyPayload = buildHistoryPayload().slice(0, -1); // exclude placeholder

    input = '';

    if (socket && connectionStatus === 'connected') {
      socket.send(
        JSON.stringify({
          type: 'query',
          query: trimmed,
          mode,
          conversation_history: historyPayload
        })
      );
    } else {
      try {
        const response = await sendQuery(trimmed, historyPayload, mode);
        updateLastAssistant({ content: response.response, entities: response.entities ?? [] });
        if (response.graph) {
          graphData.set(response.graph);
        }
        await refreshStats();
      } catch (error) {
        updateLastAssistant({ content: `Error: ${error.message}`, entities: [] });
      } finally {
        isLoading.set(false);
      }
    }
  }
</script>

<div class="chat-panel">
  <header class="chat-header">
    <h2>Conversation</h2>
    <div class="mode-select">
      <label for="mode">Mode</label>
      <select id="mode" bind:value={mode}>
        {#each modes as option}
          <option value={option}>{option}</option>
        {/each}
      </select>
    </div>
    <span class={`status ${connectionStatus}`}>{connectionStatus}</span>
  </header>

  <section class="messages" transition:fade>
    {#if $messages.length === 0}
      <div class="placeholder">Ask anything about your documents to start exploring the graph.</div>
    {:else}
      {#each $messages as message, index (index)}
        <article class={`message ${message.role}`}>
          <div class="bubble">
            <p>{message.content}</p>
          </div>
          {#if message.entities?.length}
            <div class="entities">
              {#each message.entities as entity}
                <span class="entity">{entity}</span>
              {/each}
            </div>
          {/if}
        </article>
      {/each}
    {/if}
  </section>

  <form class="input-row" on:submit|preventDefault={handleSubmit}>
    <textarea
      bind:value={input}
      placeholder="Ask a question..."
      rows="2"
      on:keydown={(event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
          event.preventDefault();
          handleSubmit();
        }
      }}
    />
    <button class="send" disabled={!input.trim() || $isLoading}>
      {$isLoading ? 'Thinking…' : 'Send'}
    </button>
  </form>
</div>

<style>
  .chat-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: rgba(15, 23, 42, 0.6);
    border-radius: 1rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    overflow: hidden;
  }

  .chat-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid rgba(148, 163, 184, 0.1);
    background: rgba(15, 23, 42, 0.8);
  }

  .chat-header h2 {
    margin: 0;
    font-size: 1.1rem;
    font-weight: 600;
  }

  .mode-select {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
  }

  .mode-select select {
    background: rgba(30, 41, 59, 0.9);
    border: 1px solid rgba(148, 163, 184, 0.2);
    color: #f8fafc;
    padding: 0.25rem 0.5rem;
    border-radius: 0.5rem;
  }

  .status {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .status.connected {
    color: #34d399;
  }

  .status.error,
  .status.disconnected {
    color: #f87171;
  }

  .messages {
    padding: 1.5rem;
    overflow-y: auto;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .placeholder {
    margin: auto;
    text-align: center;
    color: rgba(148, 163, 184, 0.8);
  }

  .message {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .message.user {
    align-items: flex-end;
  }

  .message.assistant {
    align-items: flex-start;
  }

  .bubble {
    max-width: 80%;
    padding: 0.75rem 1rem;
    border-radius: 1rem;
    line-height: 1.5;
    backdrop-filter: blur(6px);
  }

  .message.user .bubble {
    background: linear-gradient(135deg, #2563eb, #7c3aed);
    color: white;
  }

  .message.assistant .bubble {
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(148, 163, 184, 0.2);
  }

  .entities {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
  }

  .entity {
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.4);
    color: #bfdbfe;
    padding: 0.2rem 0.5rem;
    border-radius: 9999px;
    font-size: 0.7rem;
    letter-spacing: 0.02em;
  }

  .input-row {
    padding: 1rem 1.5rem;
    border-top: 1px solid rgba(148, 163, 184, 0.1);
    background: rgba(15, 23, 42, 0.8);
    display: flex;
    gap: 1rem;
  }

  textarea {
    flex: 1;
    background: rgba(30, 41, 59, 0.7);
    border-radius: 0.75rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    color: #e2e8f0;
    padding: 0.75rem 1rem;
    resize: none;
    font-size: 0.95rem;
  }

  .send {
    background: linear-gradient(135deg, #22c55e, #14b8a6);
    border: none;
    color: white;
    padding: 0 1.5rem;
    border-radius: 9999px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s ease;
  }

  .send:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }
</style>
