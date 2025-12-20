import { defineStore } from "pinia";
import { ref, watch } from "vue";

export type DisplayMode = "spectrogram" | "waveform";

const STORAGE_KEY = "shadowing_settings";

interface StoredSettings {
  displayMode: DisplayMode;
}

function loadSettings(): StoredSettings {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (e) {
    console.warn("Failed to load settings from localStorage:", e);
  }
  return { displayMode: "spectrogram" };
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

  // Persist changes
  watch(displayMode, (newMode) => {
    saveSettings({ displayMode: newMode });
  });

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
    setDisplayMode,
    toggleDisplayMode,
  };
});
