<script>
  import { onMount } from 'svelte';
  import ChatPanel from '../lib/components/ChatPanel.svelte';
  import DocumentUpload from '../lib/components/DocumentUpload.svelte';
  import GraphPanel from '../lib/components/GraphPanel.svelte';
  import GraphStats from '../lib/components/GraphStats.svelte';
  import ViewToggle from '../lib/components/ViewToggle.svelte';
  import { graphData, stats, viewMode } from '../lib/stores/app.js';
  import { checkHealth, loadFullGraph, loadStats } from '../lib/utils/api.js';

  let ready = false;
  let error = '';

  async function initialise() {
    try {
      await checkHealth();
      const [graph, analytics] = await Promise.all([loadFullGraph(), loadStats()]);
      graphData.set(graph);
      stats.set(analytics);
      ready = true;
    } catch (err) {
      error = err.message;
    }
  }

  onMount(() => {
    initialise();
  });
</script>

<div class="app">
  <header class="top-bar">
    <div>
      <h1>Conversational Knowledge Graph</h1>
      <p>Chat with your knowledge base and watch the graph adapt in real-time.</p>
    </div>
    <ViewToggle />
  </header>

  {#if error}
    <div class="error">{error}</div>
  {:else if !ready}
    <div class="loading">Loading graph…</div>
  {:else}
    <main class={`layout ${$viewMode}`}>
      {#if $viewMode !== 'graph'}
        <section class="chat-column">
          <ChatPanel />
          <DocumentUpload />
        </section>
      {/if}

      {#if $viewMode !== 'chat'}
        <section class="graph-column">
          <GraphPanel />
          <GraphStats />
        </section>
      {/if}
    </main>
  {/if}
</div>

<style>
  .app {
    min-height: 100vh;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .top-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
  }

  h1 {
    margin: 0 0 0.4rem;
    font-size: 2rem;
    font-weight: 700;
  }

  p {
    margin: 0;
    color: rgba(226, 232, 240, 0.7);
    max-width: 640px;
  }

  .layout {
    display: grid;
    gap: 1.5rem;
    flex: 1;
  }

  .layout.split {
    grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  }

  .layout.chat {
    grid-template-columns: minmax(0, 1fr);
  }

  .layout.graph {
    grid-template-columns: minmax(0, 1fr);
  }

  .chat-column,
  .graph-column {
    min-height: 70vh;
  }

  .graph-column {
    position: relative;
  }

  .loading,
  .error {
    padding: 2rem;
    border-radius: 1rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: rgba(15, 23, 42, 0.7);
    text-align: center;
    font-size: 1.1rem;
  }

  .error {
    color: #fca5a5;
  }
</style>
