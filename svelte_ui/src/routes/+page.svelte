<script lang="ts">
  import LeftPanel from '$lib/components/LeftPanel.svelte';
  let leftPanelMinimized = false;
  let rightPanelMinimized = false;
</script>

<main>
  <div class="app-container">
    <!-- Left Panel -->
    <div class="panel left-panel" class:minimized={leftPanelMinimized}>
      <button on:click={() => (leftPanelMinimized = !leftPanelMinimized)}>
        {leftPanelMinimized ? '>' : '<'}
      </button>
      <div class="panel-content">
        <LeftPanel />
      </div>
    </div>

    <!-- Main Display Area -->
    <div class="main-display">
      <h1>UAV Builder</h1>
      <!-- Main content -->
    </div>

    <!-- Right Panel -->
    <div class="panel right-panel" class:minimized={rightPanelMinimized}>
      <button on:click={() => (rightPanelMinimized = !rightPanelMinimized)}>
        {rightPanelMinimized ? '<' : '>'}
      </button>
      <div class="panel-content">
        <h2>Attributes & Properties</h2>
        <!-- Content for attributes and properties -->
      </div>
    </div>
  </div>
</main>

<style>
  .app-container {
    display: flex;
    height: 100vh;
  }

  .panel {
    width: 250px;
    transition: width 0.3s;
    border: 1px solid #ccc;
    display: flex;
    flex-direction: column;
  }

  .panel.minimized {
    width: 40px;
  }

  .panel button {
    width: 100%;
  }

  .panel-content {
    padding: 1rem;
    overflow: hidden;
  }

  .panel.minimized .panel-content {
    display: none;
  }

  .main-display {
    flex-grow: 1;
    padding: 1rem;
    border: 1px solid #ccc;
  }
</style>
