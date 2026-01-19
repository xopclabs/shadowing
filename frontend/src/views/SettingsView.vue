<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useSettingsStore, type DisplayMode } from "@/stores/settings";
import { api, type StorageInfo } from "@/api/client";

const settingsStore = useSettingsStore();

// YouTube settings form state
const proxyUrl = ref("");
const downloadDir = ref("");
const savingYouTubeSettings = ref(false);

const displayModeOptions: {
  value: DisplayMode;
  label: string;
  description: string;
}[] = [
  {
    value: "spectrogram",
    label: "Spectrogram (local)",
    description:
      "Detailed frequency visualization computed on device (slower on mobile)",
  },
  {
    value: "backend",
    label: "Spectrogram (server)",
    description:
      "Detailed frequency visualization computed on server (recommended for mobile)",
  },
  {
    value: "waveform",
    label: "Waveform",
    description: "Simple amplitude visualization (fastest)",
  },
];

// Storage management
const storageInfo = ref<StorageInfo | null>(null);
const loadingStorage = ref(false);

// Dialogs
const showClearDbDialog = ref(false);
const showClearFilesDialog = ref(false);
const clearingDb = ref(false);
const clearingFiles = ref(false);

// Toast notifications
interface Toast {
  id: number;
  message: string;
  type: "success" | "error";
}
const toasts = ref<Toast[]>([]);
let toastId = 0;

const showToast = (message: string, type: "success" | "error" = "success") => {
  const id = ++toastId;
  toasts.value.push({ id, message, type });
  setTimeout(() => {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  }, 4000);
};

// Clear files options
const deleteClips = ref(true);
const deleteRecordings = ref(true);

const loadStorageInfo = async () => {
  loadingStorage.value = true;
  try {
    storageInfo.value = await api.getStorageInfo();
  } catch (e) {
    console.error("Failed to load storage info:", e);
  } finally {
    loadingStorage.value = false;
  }
};

onMounted(() => {
  loadStorageInfo();
  settingsStore.fetchServerSettings();
});

// Sync form fields when server settings load
watch(
  () => settingsStore.serverSettings,
  (settings) => {
    if (settings) {
      proxyUrl.value = settings.socks5_proxy || "";
      downloadDir.value = settings.youtube_download_dir || "";
    }
  },
  { immediate: true },
);

const handleSaveYouTubeSettings = async () => {
  savingYouTubeSettings.value = true;
  try {
    await settingsStore.updateServerSettings({
      socks5_proxy: proxyUrl.value || null,
      youtube_download_dir: downloadDir.value || null,
    });
    showToast("YouTube settings saved!", "success");
  } catch (e) {
    showToast("Failed to save YouTube settings.", "error");
  } finally {
    savingYouTubeSettings.value = false;
  }
};

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
};

const handleClearDatabase = async () => {
  clearingDb.value = true;
  try {
    await api.clearDatabase();
    showClearDbDialog.value = false;
    await loadStorageInfo();
    showToast("Database cleared successfully!", "success");
  } catch (e) {
    console.error("Failed to clear database:", e);
    showToast("Failed to clear database. Please try again.", "error");
  } finally {
    clearingDb.value = false;
  }
};

const handleClearFiles = async () => {
  if (!deleteClips.value && !deleteRecordings.value) {
    showToast("Please select at least one option.", "error");
    return;
  }

  clearingFiles.value = true;
  try {
    const result = await api.deleteFiles(
      deleteClips.value,
      deleteRecordings.value,
    );
    showClearFilesDialog.value = false;
    await loadStorageInfo();
    showToast(
      `Deleted ${result.deleted_clips + result.deleted_recordings} files. Freed ${formatBytes(result.freed_bytes)}.`,
      "success",
    );
  } catch (e) {
    console.error("Failed to clear files:", e);
    showToast("Failed to clear files. Please try again.", "error");
  } finally {
    clearingFiles.value = false;
  }
};

// Calculate what would be deleted
const selectedDeletionSize = (): number => {
  if (!storageInfo.value) return 0;
  let size = 0;
  if (deleteClips.value) size += storageInfo.value.clips_size_bytes;
  if (deleteRecordings.value) size += storageInfo.value.recordings_size_bytes;
  return size;
};

const selectedDeletionCount = (): number => {
  if (!storageInfo.value) return 0;
  let count = 0;
  if (deleteClips.value) count += storageInfo.value.clips_count;
  if (deleteRecordings.value) count += storageInfo.value.recordings_count;
  return count;
};
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

    <!-- YouTube Download Settings -->
    <div class="card">
      <h2 class="text-lg font-semibold text-noche-100 mb-2">
        YouTube Downloads
      </h2>
      <p class="text-sm text-noche-400 mb-4">
        Configure YouTube video downloading with yt-dlp.
      </p>

      <div
        v-if="settingsStore.serverSettingsLoading && !settingsStore.serverSettings"
        class="flex items-center justify-center py-4"
      >
        <div
          class="w-5 h-5 border-2 border-sol-500 border-t-transparent rounded-full animate-spin"
        ></div>
      </div>

      <div v-else class="space-y-4">
        <!-- SOCKS5 Proxy -->
        <div>
          <label
            for="proxy-url"
            class="block text-sm font-medium text-noche-200 mb-1"
          >
            SOCKS5 Proxy URL
          </label>
          <input
            id="proxy-url"
            v-model="proxyUrl"
            type="text"
            placeholder="socks5://127.0.0.1:1080"
            class="w-full px-4 py-2 bg-noche-800 border border-noche-700 rounded-lg text-noche-100 placeholder-noche-500 focus:outline-none focus:border-sol-500 focus:ring-1 focus:ring-sol-500"
          />
          <p class="text-xs text-noche-500 mt-1">
            Optional. Used for downloading videos through a proxy.
          </p>
        </div>

        <!-- Download Directory -->
        <div>
          <label
            for="download-dir"
            class="block text-sm font-medium text-noche-200 mb-1"
          >
            Download Directory
          </label>
          <input
            id="download-dir"
            v-model="downloadDir"
            type="text"
            placeholder="/path/to/downloads (defaults to data/youtube)"
            class="w-full px-4 py-2 bg-noche-800 border border-noche-700 rounded-lg text-noche-100 placeholder-noche-500 focus:outline-none focus:border-sol-500 focus:ring-1 focus:ring-sol-500"
          />
          <p class="text-xs text-noche-500 mt-1">
            Optional. Leave empty to use the default location.
          </p>
        </div>

        <!-- Save Button -->
        <button
          @click="handleSaveYouTubeSettings"
          :disabled="savingYouTubeSettings"
          class="btn btn-primary w-full"
        >
          <span v-if="savingYouTubeSettings">Saving...</span>
          <span v-else>Save YouTube Settings</span>
        </button>

        <div
          v-if="settingsStore.serverSettingsError"
          class="p-3 bg-tierra-500/10 border border-tierra-500/30 rounded-lg"
        >
          <p class="text-sm text-tierra-400">
            {{ settingsStore.serverSettingsError }}
          </p>
        </div>
      </div>
    </div>

    <!-- Storage Management -->
    <div class="card">
      <h2 class="text-lg font-semibold text-noche-100 mb-2">
        Storage Management
      </h2>
      <p class="text-sm text-noche-400 mb-4">
        Manage your practice data and free up disk space.
      </p>

      <!-- Storage Info -->
      <div v-if="loadingStorage" class="flex items-center justify-center py-4">
        <div
          class="w-5 h-5 border-2 border-sol-500 border-t-transparent rounded-full animate-spin"
        ></div>
      </div>
      <div v-else-if="storageInfo" class="space-y-4">
        <!-- Storage stats -->
        <div class="grid grid-cols-2 gap-3">
          <div class="p-3 bg-noche-800 rounded-lg">
            <div class="text-lg font-bold text-noche-100">
              {{ storageInfo.clips_count }}
            </div>
            <div class="text-xs text-noche-500">
              Clips ({{ formatBytes(storageInfo.clips_size_bytes) }})
            </div>
          </div>
          <div class="p-3 bg-noche-800 rounded-lg">
            <div class="text-lg font-bold text-noche-100">
              {{ storageInfo.recordings_count }}
            </div>
            <div class="text-xs text-noche-500">
              Recordings ({{ formatBytes(storageInfo.recordings_size_bytes) }})
            </div>
          </div>
        </div>

        <div class="text-sm text-noche-400 text-center">
          Total: {{ formatBytes(storageInfo.total_size_bytes) }}
        </div>

        <!-- Action buttons -->
        <div class="flex gap-3 pt-2">
          <button
            @click="showClearFilesDialog = true"
            class="flex-1 btn btn-secondary text-sm"
            :disabled="storageInfo.total_size_bytes === 0"
          >
            <svg
              class="w-4 h-4 mr-2 inline"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
            Clear Files
          </button>
          <button
            @click="showClearDbDialog = true"
            class="flex-1 btn btn-danger text-sm"
          >
            <svg
              class="w-4 h-4 mr-2 inline"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
              />
            </svg>
            Clear Database
          </button>
        </div>
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
          Your display settings are saved locally. Statistics and recent files
          are synced across devices.
        </p>
      </div>
    </div>
  </div>

  <!-- Toast Notifications -->
  <Teleport to="body">
    <div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="px-4 py-3 rounded-xl shadow-lg backdrop-blur-sm max-w-sm"
          :class="
            toast.type === 'success'
              ? 'bg-sol-500/90 text-noche-950'
              : 'bg-tierra-500/90 text-white'
          "
        >
          <div class="flex items-center gap-2">
            <svg
              v-if="toast.type === 'success'"
              class="w-5 h-5 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 13l4 4L19 7"
              />
            </svg>
            <svg
              v-else
              class="w-5 h-5 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span class="text-sm font-medium">{{ toast.message }}</span>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>

  <!-- Clear Database Dialog -->
  <Teleport to="body">
    <div
      v-if="showClearDbDialog"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <!-- Backdrop -->
      <div
        class="absolute inset-0 bg-black/70 backdrop-blur-sm"
        @click="showClearDbDialog = false"
      ></div>

      <!-- Dialog -->
      <div
        class="relative bg-noche-900 border border-noche-700 rounded-2xl p-6 max-w-sm w-full shadow-xl"
      >
        <h3 class="text-lg font-semibold text-noche-100 mb-2">
          Clear Database?
        </h3>
        <p class="text-sm text-noche-400 mb-4">
          This will delete all practice data including statistics, recent files,
          and recording metadata.
          <span class="text-tierra-400 font-medium"
            >This action cannot be undone.</span
          >
        </p>
        <p class="text-xs text-noche-500 mb-6">
          Note: Audio files on disk will not be deleted. Use "Clear Files" to
          remove those.
        </p>

        <div class="flex gap-3">
          <button
            @click="showClearDbDialog = false"
            class="flex-1 btn btn-secondary"
            :disabled="clearingDb"
          >
            Cancel
          </button>
          <button
            @click="handleClearDatabase"
            class="flex-1 btn btn-danger"
            :disabled="clearingDb"
          >
            <span v-if="clearingDb">Clearing...</span>
            <span v-else>Clear All Data</span>
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- Clear Files Dialog -->
  <Teleport to="body">
    <div
      v-if="showClearFilesDialog"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <!-- Backdrop -->
      <div
        class="absolute inset-0 bg-black/70 backdrop-blur-sm"
        @click="showClearFilesDialog = false"
      ></div>

      <!-- Dialog -->
      <div
        class="relative bg-noche-900 border border-noche-700 rounded-2xl p-6 max-w-sm w-full shadow-xl"
      >
        <h3 class="text-lg font-semibold text-noche-100 mb-2">
          Delete Audio Files?
        </h3>
        <p class="text-sm text-noche-400 mb-4">
          Select which files to delete.
          <span class="text-tierra-400 font-medium"
            >This action cannot be undone.</span
          >
        </p>

        <!-- Checkboxes -->
        <div class="space-y-3 mb-4">
          <label
            class="flex items-center gap-3 p-3 bg-noche-800 rounded-lg cursor-pointer hover:bg-noche-750 transition-colors"
          >
            <input
              type="checkbox"
              v-model="deleteClips"
              class="w-5 h-5 rounded border-noche-600 bg-noche-700 text-sol-500 focus:ring-sol-500"
            />
            <div>
              <div class="text-noche-200">Clip audio files</div>
              <div v-if="storageInfo" class="text-xs text-noche-500">
                {{ storageInfo.clips_count }} files ({{
                  formatBytes(storageInfo.clips_size_bytes)
                }})
              </div>
            </div>
          </label>

          <label
            class="flex items-center gap-3 p-3 bg-noche-800 rounded-lg cursor-pointer hover:bg-noche-750 transition-colors"
          >
            <input
              type="checkbox"
              v-model="deleteRecordings"
              class="w-5 h-5 rounded border-noche-600 bg-noche-700 text-sol-500 focus:ring-sol-500"
            />
            <div>
              <div class="text-noche-200">Your recordings</div>
              <div v-if="storageInfo" class="text-xs text-noche-500">
                {{ storageInfo.recordings_count }} files ({{
                  formatBytes(storageInfo.recordings_size_bytes)
                }})
              </div>
            </div>
          </label>
        </div>

        <!-- Summary -->
        <div
          v-if="storageInfo && (deleteClips || deleteRecordings)"
          class="p-3 bg-tierra-500/10 border border-tierra-500/30 rounded-lg mb-4"
        >
          <p class="text-sm text-tierra-400">
            Will delete
            <span class="font-bold">{{ selectedDeletionCount() }} files</span>
            and free up
            <span class="font-bold">{{
              formatBytes(selectedDeletionSize())
            }}</span>
          </p>
        </div>

        <div class="flex gap-3">
          <button
            @click="showClearFilesDialog = false"
            class="flex-1 btn btn-secondary"
            :disabled="clearingFiles"
          >
            Cancel
          </button>
          <button
            @click="handleClearFiles"
            class="flex-1 btn btn-danger"
            :disabled="clearingFiles || (!deleteClips && !deleteRecordings)"
          >
            <span v-if="clearingFiles">Deleting...</span>
            <span v-else>Delete Files</span>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active {
  transition: all 0.3s ease-out;
}
.toast-leave-active {
  transition: all 0.2s ease-in;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(100px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(100px);
}
</style>
