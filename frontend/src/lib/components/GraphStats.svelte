<script>
  import { stats } from '../stores/app.js';
  import { writable } from 'svelte/store';

  const expanded = writable(true);
</script>

<div class="stats-card" class:collapsed={!$expanded}>
  <button class="toggle" on:click={() => expanded.update((value) => !value)}>
    <span>Graph Insights</span>
    <span>{$expanded ? '−' : '+'}</span>
  </button>

  {#if $expanded}
    <div class="grid">
      <div>
        <span class="label">Queries</span>
        <span class="value">{$stats?.total_queries ?? 0}</span>
      </div>
      <div>
        <span class="label">Unique Entities</span>
        <span class="value">{$stats?.unique_entities ?? 0}</span>
      </div>
      <div>
        <span class="label">Avg Response (s)</span>
        <span class="value">{($stats?.avg_response_time ?? 0).toFixed(2)}</span>
      </div>
      <div>
        <span class="label">Graph Size</span>
        <span class="value">{$stats?.graph_node_count ?? 0} nodes</span>
      </div>
    </div>

    {#if $stats?.most_discussed?.length}
      <div class="top-entities">
        <span class="label">Most Discussed</span>
        <ul>
          {#each $stats.most_discussed as [entity, count]}
            <li>{entity} · {count}</li>
          {/each}
        </ul>
      </div>
    {/if}
  {/if}
</div>

<style>
  .stats-card {
    position: absolute;
    right: 1.5rem;
    top: 1.5rem;
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 1rem;
    padding: 1rem;
    min-width: 220px;
    color: #e2e8f0;
    box-shadow: 0 20px 40px rgba(15, 23, 42, 0.4);
  }

  .toggle {
    all: unset;
    display: flex;
    width: 100%;
    justify-content: space-between;
    font-weight: 600;
    letter-spacing: 0.02em;
    cursor: pointer;
  }

  .grid {
    margin-top: 1rem;
    display: grid;
    gap: 0.75rem;
  }

  .label {
    display: block;
    font-size: 0.75rem;
    color: rgba(148, 163, 184, 0.8);
  }

  .value {
    font-size: 1.1rem;
    font-weight: 600;
  }

  .top-entities {
    margin-top: 1rem;
  }

  ul {
    margin: 0.5rem 0 0;
    padding: 0;
    list-style: none;
    display: grid;
    gap: 0.4rem;
    font-size: 0.85rem;
  }
</style>
