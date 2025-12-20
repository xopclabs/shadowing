<script setup lang="ts">
import { useSettingsStore, type DisplayMode } from "@/stores/settings";

const settingsStore = useSettingsStore();

const displayModeOptions: {
  value: DisplayMode;
  label: string;
  description: string;
}[] = [
  {
    value: "spectrogram",
    label: "Spectrogram",
    description: "Detailed frequency visualization (slower on mobile)",
  },
  {
    value: "waveform",
    label: "Waveform",
    description: "Simple amplitude visualization (faster)",
  },
];
</script>

<template>
  <div class="space-y-6 max-w-2xl mx-auto">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="font-display text-2xl font-bold text-noche-100">Settings</h1>
    </div>

    <!-- Display Mode Setting -->
    <div class="card">
      <h2 class="text-lg font-semibold text-noche-100 mb-2">
        Audio Visualization
      </h2>
      <p class="text-sm text-noche-400 mb-4">
        Choose how audio is displayed. Waveform is recommended for mobile
        devices.
      </p>

      <div class="space-y-3">
        <button
          v-for="option in displayModeOptions"
          :key="option.value"
          @click="settingsStore.setDisplayMode(option.value)"
          class="w-full flex items-start gap-4 p-4 rounded-xl border-2 transition-all text-left"
          :class="
            settingsStore.displayMode === option.value
              ? 'border-sol-500 bg-sol-500/10'
              : 'border-noche-700 bg-noche-800/50 hover:border-noche-600'
          "
        >
          <!-- Radio indicator -->
          <div
            class="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-0.5"
            :class="
              settingsStore.displayMode === option.value
                ? 'border-sol-500'
                : 'border-noche-600'
            "
          >
            <div
              v-if="settingsStore.displayMode === option.value"
              class="w-2.5 h-2.5 rounded-full bg-sol-500"
            />
          </div>

          <!-- Label and description -->
          <div>
            <div
              class="font-medium"
              :class="
                settingsStore.displayMode === option.value
                  ? 'text-sol-400'
                  : 'text-noche-200'
              "
            >
              {{ option.label }}
            </div>
            <div class="text-sm text-noche-500 mt-0.5">
              {{ option.description }}
            </div>
          </div>
        </button>
      </div>
    </div>

    <!-- Info Card -->
    <div class="card bg-noche-800/30 border-noche-700">
      <div class="flex items-start gap-3">
        <svg
          class="w-5 h-5 text-sol-500 flex-shrink-0 mt-0.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <p class="text-sm text-noche-400">
          Your settings are saved automatically and will be remembered the next
          time you visit.
        </p>
      </div>
    </div>
  </div>
</template>
