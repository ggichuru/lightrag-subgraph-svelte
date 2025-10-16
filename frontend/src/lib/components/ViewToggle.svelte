<script>
  import { viewMode } from '../stores/app.js';

  const options = [
    { value: 'chat', label: 'Chat' },
    { value: 'split', label: 'Split' },
    { value: 'graph', label: 'Graph' }
  ];
</script>

<div class="toggle">
  {#each options as option}
    <button
      class:active={$viewMode === option.value}
      on:click={() => viewMode.set(option.value)}
      type="button"
    >
      {option.label}
    </button>
  {/each}
</div>

<style>
  .toggle {
    display: inline-flex;
    padding: 0.25rem;
    background: rgba(30, 41, 59, 0.8);
    border-radius: 9999px;
    border: 1px solid rgba(148, 163, 184, 0.2);
  }

  button {
    border: none;
    background: transparent;
    color: rgba(226, 232, 240, 0.8);
    padding: 0.4rem 1rem;
    border-radius: 9999px;
    cursor: pointer;
    font-weight: 600;
  }

  button.active {
    background: linear-gradient(135deg, #2563eb, #9333ea);
    color: white;
  }
</style>
