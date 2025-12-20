import { defineStore } from "pinia";
import { ref, watch } from "vue";

export type DisplayMode = "spectrogram" | "waveform" | "backend";

const STORAGE_KEY = "shadowing_settings";

interface StoredSettings {
  displayMode: DisplayMode;
  speedModifier: number;
  silenceAtStart: number;
  repetitions: number;
  silenceBetweenReps: number;
}

const DEFAULT_SETTINGS: StoredSettings = {
  displayMode: "spectrogram",
  speedModifier: 1,
  silenceAtStart: 500,
  repetitions: 5,
  silenceBetweenReps: 600,
};

function loadSettings(): StoredSettings {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
    }
  } catch (e) {
    console.warn("Failed to load settings from localStorage:", e);
  }
  return { ...DEFAULT_SETTINGS };
}

function saveSettings(settings: StoredSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch (e) {
    console.warn("Failed to save settings to localStorage:", e);
  }
}

export const useSettingsStore = defineStore("settings", () => {
  const stored = loadSettings();

  // State
  const displayMode = ref<DisplayMode>(stored.displayMode);
  const speedModifier = ref<number>(stored.speedModifier);
  const silenceAtStart = ref<number>(stored.silenceAtStart);
  const repetitions = ref<number>(stored.repetitions);
  const silenceBetweenReps = ref<number>(stored.silenceBetweenReps);

  // Persist changes
  const persistSettings = () => {
    saveSettings({
      displayMode: displayMode.value,
      speedModifier: speedModifier.value,
      silenceAtStart: silenceAtStart.value,
      repetitions: repetitions.value,
      silenceBetweenReps: silenceBetweenReps.value,
    });
  };

  watch(displayMode, persistSettings);
  watch(speedModifier, persistSettings);
  watch(silenceAtStart, persistSettings);
  watch(repetitions, persistSettings);
  watch(silenceBetweenReps, persistSettings);

  // Actions
  const setDisplayMode = (mode: DisplayMode) => {
    displayMode.value = mode;
  };

  const toggleDisplayMode = () => {
    displayMode.value =
      displayMode.value === "spectrogram" ? "waveform" : "spectrogram";
  };

  return {
    displayMode,
    speedModifier,
    silenceAtStart,
    repetitions,
    silenceBetweenReps,
    setDisplayMode,
    toggleDisplayMode,
  };
});
