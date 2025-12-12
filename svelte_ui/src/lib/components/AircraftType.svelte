<script lang="ts">
  let aircraftTypes = ['Multirotor', 'Fixed Wing', 'Hybrid'];
  let selectedAircraftType = '';
</script>

<div class="aircraft-type-container">
  <h3>Select Aircraft Type</h3>
  <div class="options">
    {#each aircraftTypes as type}
      <button
        class:selected={selectedAircraftType === type}
        on:click={() => (selectedAircraftType = type)}
      >
        {type}
      </button>
    {/each}
  </div>
</div>

<style>
  .aircraft-type-container {
    padding: 1rem;
  }

  .options button {
    margin: 0.5rem;
  }

  .options button.selected {
    background-color: #ccc;
  }
</style>
