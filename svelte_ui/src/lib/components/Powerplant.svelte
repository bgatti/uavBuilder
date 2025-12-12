<script lang="ts">
  let powerplants = ['Fuel', 'Electric', 'Hybrid'];
  let selectedPowerplant = '';
</script>

<div class="powerplant-container">
  <h3>Select Powerplant</h3>
  <div class="options">
    {#each powerplants as powerplant}
      <button
        class:selected={selectedPowerplant === powerplant}
        on:click={() => (selectedPowerplant = powerplant)}
      >
        {powerplant}
      </button>
    {/each}
  </div>
</div>

<style>
  .powerplant-container {
    padding: 1rem;
  }

  .options button {
    margin: 0.5rem;
  }

  .options button.selected {
    background-color: #ccc;
  }
</style>
