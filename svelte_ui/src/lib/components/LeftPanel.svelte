<script lang="ts">
  import AircraftType from '$lib/components/AircraftType.svelte';
  import Powerplant from '$lib/components/Powerplant.svelte';
  let steps = [
    'Aircraft Type',
    'Powerplant',
    'Fuel/Battery',
    'Payload',
    'Controller',
    'Link',
    'Configuration',
  ];
  let currentStep = 0;

  function nextStep() {
    if (currentStep < steps.length - 1) {
      currentStep++;
      console.log('Next button clicked, new step:', currentStep);
    }
  }

  function prevStep() {
    if (currentStep > 0) {
      currentStep--;
    }
  }
</script>

<div class="left-panel-container">
  <div class="progress-bar">
    {#each steps as step, i}
      <div class="step" class:active={i === currentStep} class:completed={i < currentStep}>
        {step}
      </div>
    {/each}
  </div>
  <div class="tabs">
    {#if currentStep === 0}
      <AircraftType />
    {:else if currentStep === 1}
      <Powerplant />
    {/if}
  </div>
  <div class="navigation">
    <button on:click={prevStep} disabled={currentStep === 0}>Previous</button>
    <button on:click={() => alert('Next button clicked!')}>Next</button>
  </div>
</div>

<style>
  .left-panel-container {
    padding: 1rem;
  }

  .progress-bar {
    display: flex;
    flex-direction: column;
  }

  .step {
    padding: 0.5rem;
    border-left: 2px solid #ccc;
  }

  .step.active {
    border-left: 2px solid #333;
    font-weight: bold;
  }

  .step.completed {
    border-left: 2px solid #0f0;
  }
</style>
