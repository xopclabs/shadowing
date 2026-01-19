import { defineStore } from "pinia";
import { ref, watch } from "vue";
import { api, type ServerSettings } from "@/api/client";

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

  // Server settings (fetched from backend)
  const serverSettings = ref<ServerSettings | null>(null);
  const serverSettingsLoading = ref(false);
  const serverSettingsError = ref<string | null>(null);

  const fetchServerSettings = async () => {
    serverSettingsLoading.value = true;
    serverSettingsError.value = null;
    try {
      serverSettings.value = await api.getServerSettings();
    } catch (e) {
      console.error("Failed to load server settings:", e);
      serverSettingsError.value =
        e instanceof Error ? e.message : "Failed to load settings";
    } finally {
      serverSettingsLoading.value = false;
    }
  };

  const updateServerSettings = async (settings: Partial<ServerSettings>) => {
    serverSettingsLoading.value = true;
    serverSettingsError.value = null;
    try {
      serverSettings.value = await api.updateServerSettings(settings);
    } catch (e) {
      console.error("Failed to update server settings:", e);
      serverSettingsError.value =
        e instanceof Error ? e.message : "Failed to update settings";
      throw e;
    } finally {
      serverSettingsLoading.value = false;
    }
  };

  return {
    displayMode,
    speedModifier,
    silenceAtStart,
    repetitions,
    silenceBetweenReps,
    setDisplayMode,
    toggleDisplayMode,
    // Server settings
    serverSettings,
    serverSettingsLoading,
    serverSettingsError,
    fetchServerSettings,
    updateServerSettings,
  };
});
