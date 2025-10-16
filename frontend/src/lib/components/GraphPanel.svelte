<script>
  import { onDestroy, onMount } from 'svelte';
  import { graphData, currentEntities } from '../stores/app.js';
  import { createGraph, destroyGraph, updateGraph } from '../graph/d3-graph.js';

  let svgElement;
  let instance;

  onMount(() => {
    instance = createGraph(svgElement, $graphData ?? { nodes: [], links: [] });
  });

  onDestroy(() => {
    destroyGraph(instance);
  });

  $: if (instance && $graphData) {
    updateGraph(instance, $graphData);
  }
</script>

<div class="graph-panel">
  <div class="graph-header">
    <h2>Knowledge Graph</h2>
    {#if $currentEntities.length}
      <div class="focal-entities">
        <span>Focus:</span>
        {#each $currentEntities as entity}
          <span class="badge">{entity}</span>
        {/each}
      </div>
    {/if}
  </div>
  <svg bind:this={svgElement} class="graph-canvas"></svg>
</div>

<style>
  .graph-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: rgba(15, 23, 42, 0.6);
    border-radius: 1rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    overflow: hidden;
    position: relative;
  }

  .graph-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid rgba(148, 163, 184, 0.1);
    background: rgba(15, 23, 42, 0.8);
  }

  .graph-header h2 {
    margin: 0;
    font-size: 1.1rem;
    font-weight: 600;
  }

  .focal-entities {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    font-size: 0.8rem;
    color: rgba(226, 232, 240, 0.8);
  }

  .badge {
    background: rgba(14, 165, 233, 0.2);
    border: 1px solid rgba(14, 165, 233, 0.6);
    color: #bae6fd;
    padding: 0.2rem 0.5rem;
    border-radius: 9999px;
    font-size: 0.7rem;
  }

  .graph-canvas {
    flex: 1;
    width: 100%;
    height: 100%;
    background: radial-gradient(circle at top, rgba(15, 118, 110, 0.12), transparent 60%);
  }
</style>
