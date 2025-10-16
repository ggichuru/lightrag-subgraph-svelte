<script>
  import { onDestroy } from 'svelte';
  import { getIngestionStatus, startIngestion, uploadDocument } from '../utils/api.js';
  import { ingestStatus, isIngesting } from '../stores/app.js';

  let files = [];
  let error = '';
  let pollingHandle;

  function handleDrop(event) {
    event.preventDefault();
    const dropped = Array.from(event.dataTransfer.files ?? []);
    files = [...files, ...dropped];
  }

  function handleBrowse(event) {
    const selected = Array.from(event.target.files ?? []);
    files = [...files, ...selected];
  }

  function removeFile(index) {
    files = files.filter((_, idx) => idx !== index);
  }

  async function upload() {
    if (!files.length) return;
    error = '';

    try {
      for (const file of files) {
        await uploadDocument(file);
      }
      files = [];
    } catch (err) {
      error = err.message;
    }
  }

  async function triggerIngestion() {
    try {
      const status = await startIngestion();
      ingestStatus.set(status);
      isIngesting.set(true);
      pollStatus();
    } catch (err) {
      error = err.message;
    }
  }

  function pollStatus() {
    clearInterval(pollingHandle);
    pollingHandle = setInterval(async () => {
      try {
        const status = await getIngestionStatus();
        ingestStatus.set(status);
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(pollingHandle);
          isIngesting.set(false);
        }
      } catch (err) {
        clearInterval(pollingHandle);
        isIngesting.set(false);
        error = err.message;
      }
    }, 2000);
  }

  onDestroy(() => {
    clearInterval(pollingHandle);
  });
</script>

<div class="upload-card">
  <h3>Document Upload</h3>
  <div
    class="dropzone"
    role="button"
    tabindex="0"
    aria-label="Upload documents by drag and drop"
    on:dragover|preventDefault
    on:drop={handleDrop}
  >
    <p>Drag & drop documents here or</p>
    <label class="browse">
      Browse
      <input type="file" multiple on:change={handleBrowse} />
    </label>
  </div>

  {#if files.length}
    <ul class="file-list">
      {#each files as file, index}
        <li>
          <span>{file.name}</span>
          <button type="button" on:click={() => removeFile(index)}>×</button>
        </li>
      {/each}
    </ul>
    <button class="primary" on:click={upload}>Upload {files.length} file(s)</button>
  {/if}

  <button class="secondary" on:click={triggerIngestion} disabled={$isIngesting}>
    {$isIngesting ? 'Ingesting…' : 'Start Ingestion'}
  </button>

  {#if $ingestStatus}
    <div class="status">
      <span>Status: {$ingestStatus.status}</span>
      <span>Processed: {$ingestStatus.documents_processed} / {$ingestStatus.total_documents}</span>
      {#if $ingestStatus.current_file}
        <span>Current: {$ingestStatus.current_file}</span>
      {/if}
      {#if $ingestStatus.error}
        <span class="error">Error: {$ingestStatus.error}</span>
      {/if}
    </div>
  {/if}

  {#if error}
    <div class="error">{error}</div>
  {/if}
</div>

<style>
  .upload-card {
    margin-top: 1.5rem;
    padding: 1.25rem;
    border-radius: 1rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: rgba(15, 23, 42, 0.7);
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  h3 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
  }

  .dropzone {
    border: 2px dashed rgba(148, 163, 184, 0.4);
    border-radius: 1rem;
    padding: 1.5rem;
    text-align: center;
    color: rgba(226, 232, 240, 0.8);
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .browse {
    cursor: pointer;
    color: #38bdf8;
    font-weight: 600;
  }

  .browse input {
    display: none;
  }

  .file-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.5rem;
  }

  .file-list li {
    display: flex;
    justify-content: space-between;
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 0.75rem;
    padding: 0.5rem 0.75rem;
    font-size: 0.85rem;
  }

  .file-list button {
    all: unset;
    cursor: pointer;
    color: rgba(248, 113, 113, 0.9);
    font-size: 1rem;
    padding: 0 0.25rem;
  }

  .primary,
  .secondary {
    border: none;
    border-radius: 0.75rem;
    padding: 0.75rem 1rem;
    font-weight: 600;
    cursor: pointer;
  }

  .primary {
    background: linear-gradient(135deg, #2563eb, #9333ea);
    color: white;
  }

  .secondary {
    background: rgba(30, 41, 59, 0.8);
    border: 1px solid rgba(148, 163, 184, 0.4);
    color: rgba(226, 232, 240, 0.9);
  }

  .secondary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .status {
    display: grid;
    gap: 0.25rem;
    font-size: 0.85rem;
    color: rgba(226, 232, 240, 0.85);
  }

  .error {
    color: #f87171;
    font-size: 0.85rem;
  }
</style>
