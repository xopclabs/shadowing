<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { useSessionStore } from "@/stores/session";
import {
  api,
  type RecentFile,
  type YouTubeVideoInfo,
  type YouTubeDownloadResult,
  type YouTubeDownloadRecord,
} from "@/api/client";
import FileBrowser from "@/components/FileBrowser.vue";
import ClipSelector from "@/components/ClipSelector.vue";

const router = useRouter();
const sessionStore = useSessionStore();

const LAST_DIR_KEY = "shadowing_last_directory";

// Category tabs
type Category = "youtube" | "media";
const activeCategory = ref<Category>("youtube");

// UI State
const mode = ref<"browse" | "select">("browse");

// Form data
const videoPath = ref("");
const initialTime = ref<number | undefined>(undefined);
const lastDirectory = ref("/mnt");

// Recent files (from API) - mixed
const recentFiles = ref<RecentFile[]>([]);
const loadingRecent = ref(false);

// YouTube downloads list
const youtubeDownloads = ref<YouTubeDownloadRecord[]>([]);
const loadingDownloads = ref(false);

// YouTube download form state
const youtubeUrl = ref("");
const youtubeAudioOnly = ref(false);
const youtubeInfo = ref<YouTubeVideoInfo | null>(null);
const youtubeLoading = ref(false);
const youtubeDownloading = ref(false);
const youtubeError = ref("");
const youtubeSuccess = ref<YouTubeDownloadResult | null>(null);

// Loading state
const isLoading = ref(false);
const errorMessage = ref("");

// Filtered recent files based on active category
const filteredRecentFiles = computed(() => {
  if (mode.value === "select") {
    // When in select mode, show only files from active category
    return recentFiles.value.filter((f) => f.source === activeCategory.value);
  }
  // In browse mode, show all recent files
  return recentFiles.value;
});

// Load data
onMounted(async () => {
  const savedDir = localStorage.getItem(LAST_DIR_KEY);
  if (savedDir) {
    lastDirectory.value = savedDir;
  }

  // Load recent files from API
  await loadRecentFiles();
  // Load YouTube downloads
  await loadYouTubeDownloads();
});

const loadRecentFiles = async () => {
  loadingRecent.value = true;
  try {
    recentFiles.value = await api.listRecentFiles();
  } catch (e) {
    console.warn("Failed to load recent files:", e);
  } finally {
    loadingRecent.value = false;
  }
};

const loadYouTubeDownloads = async () => {
  loadingDownloads.value = true;
  try {
    youtubeDownloads.value = await api.listYouTubeDownloads();
  } catch (e) {
    console.warn("Failed to load YouTube downloads:", e);
  } finally {
    loadingDownloads.value = false;
  }
};

// Format time for display
const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

const formatDuration = (seconds: number | null): string => {
  if (!seconds) return "";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (mins >= 60) {
    const hours = Math.floor(mins / 60);
    const remainingMins = mins % 60;
    return `${hours}:${remainingMins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

const handleFileSelected = (path: string) => {
  videoPath.value = path;
  initialTime.value = undefined;

  // Save the directory of the selected file
  const lastSlash = path.lastIndexOf("/");
  if (lastSlash > 0) {
    const dir = path.substring(0, lastSlash);
    localStorage.setItem(LAST_DIR_KEY, dir);
    lastDirectory.value = dir;
  }

  mode.value = "select";
};

const handleRecentFileSelected = (file: RecentFile) => {
  videoPath.value = file.video_path;
  initialTime.value = file.last_timestamp;
  // Switch to the category of the selected file
  activeCategory.value = file.source;
  mode.value = "select";
};

const handleYouTubeDownloadSelected = (download: YouTubeDownloadRecord) => {
  videoPath.value = download.file_path;
  initialTime.value = undefined;
  activeCategory.value = "youtube";
  mode.value = "select";
};

const handleClipSelected = async (start: number, end: number) => {
  if (!videoPath.value.trim()) {
    errorMessage.value = "No video selected";
    return;
  }

  isLoading.value = true;
  errorMessage.value = "";

  try {
    // Determine thumbnail URL for YouTube videos
    let thumbnailUrl: string | undefined;
    if (activeCategory.value === "youtube") {
      // Find the download record to get thumbnail
      const download = youtubeDownloads.value.find(
        (d) => d.file_path === videoPath.value,
      );
      thumbnailUrl = download?.thumbnail_url || undefined;
    }

    // Save to recent files via API with source
    await api.addRecentFile(
      videoPath.value,
      start,
      activeCategory.value,
      thumbnailUrl,
    );

    // Refresh recent files list
    recentFiles.value = await api.listRecentFiles();

    await sessionStore.startSession({
      videoPath: videoPath.value.trim(),
      startTime: start,
      endTime: end,
    });
    router.push("/session");
  } catch (e) {
    errorMessage.value =
      e instanceof Error ? e.message : "Failed to start session";
  } finally {
    isLoading.value = false;
  }
};

const goBack = () => {
  mode.value = "browse";
  videoPath.value = "";
  initialTime.value = undefined;
};

// YouTube download functions
const fetchYouTubeInfo = async () => {
  if (!youtubeUrl.value.trim()) return;

  youtubeLoading.value = true;
  youtubeError.value = "";
  youtubeInfo.value = null;
  youtubeSuccess.value = null;

  try {
    youtubeInfo.value = await api.getYouTubeVideoInfo(youtubeUrl.value.trim());
  } catch (e) {
    youtubeError.value =
      e instanceof Error ? e.message : "Failed to fetch video info";
  } finally {
    youtubeLoading.value = false;
  }
};

const downloadYouTube = async () => {
  if (!youtubeUrl.value.trim()) return;

  youtubeDownloading.value = true;
  youtubeError.value = "";
  youtubeSuccess.value = null;

  try {
    const result = await api.downloadYouTubeVideo(
      youtubeUrl.value.trim(),
      youtubeAudioOnly.value,
    );

    if (result.success) {
      youtubeSuccess.value = result;
      // Reset form after successful download
      youtubeUrl.value = "";
      youtubeInfo.value = null;
      // Refresh downloads list
      await loadYouTubeDownloads();
    } else {
      youtubeError.value = result.error || "Download failed";
    }
  } catch (e) {
    youtubeError.value =
      e instanceof Error ? e.message : "Failed to download video";
  } finally {
    youtubeDownloading.value = false;
  }
};

const resetYouTubeForm = () => {
  youtubeUrl.value = "";
  youtubeInfo.value = null;
  youtubeError.value = "";
  youtubeSuccess.value = null;
};

// Carousel scroll
const carouselRef = ref<HTMLDivElement | null>(null);

const scrollCarousel = (direction: "left" | "right") => {
  if (!carouselRef.value) return;
  const scrollAmount = 200;
  carouselRef.value.scrollBy({
    left: direction === "left" ? -scrollAmount : scrollAmount,
    behavior: "smooth",
  });
};

// Get thumbnail URL for a recent file
const getRecentFileThumbnail = (file: RecentFile): string => {
  if (file.source === "youtube" && file.thumbnail_url) {
    return file.thumbnail_url;
  }
  // For media files, use the backend thumbnail endpoint
  return api.getThumbnailUrl(file.video_path, file.last_timestamp);
};
</script>

<template>
  <div class="space-y-4 max-w-2xl mx-auto">
    <!-- Error Message -->
    <div
      v-if="errorMessage"
      class="p-4 bg-tierra-500/10 border border-tierra-500/30 rounded-xl"
    >
      <p class="text-tierra-400 text-center">{{ errorMessage }}</p>
    </div>

    <!-- Back Button (when selecting clip) -->
    <button
      v-if="mode === 'select'"
      @click="goBack"
      class="flex items-center gap-2 text-noche-400 hover:text-noche-200 transition-colors"
    >
      <svg
        class="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M15 19l-7-7 7-7"
        />
      </svg>
      Back to {{ activeCategory === "youtube" ? "YouTube" : "Media" }}
    </button>

    <!-- Main Content -->
    <template v-if="mode === 'browse'">
      <!-- Recent Files Carousel (shows all) -->
      <div v-if="recentFiles.length > 0" class="space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-medium text-noche-400">Recent Files</h2>
          <div class="flex gap-1">
            <button
              @click="scrollCarousel('left')"
              class="p-1.5 rounded-lg bg-noche-800 hover:bg-noche-700 text-noche-400 transition-colors"
            >
              <svg
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>
            <button
              @click="scrollCarousel('right')"
              class="p-1.5 rounded-lg bg-noche-800 hover:bg-noche-700 text-noche-400 transition-colors"
            >
              <svg
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          </div>
        </div>

        <div
          ref="carouselRef"
          class="flex gap-3 overflow-x-auto pb-2 scrollbar-hide snap-x snap-mandatory"
          style="scrollbar-width: none; -ms-overflow-style: none"
        >
          <button
            v-for="file in recentFiles"
            :key="file.id"
            @click="handleRecentFileSelected(file)"
            class="flex-shrink-0 w-40 snap-start group"
          >
            <div
              class="relative h-24 rounded-xl bg-noche-800 border border-noche-700 overflow-hidden transition-all group-hover:border-sol-500/50"
            >
              <!-- Fallback icon -->
              <div
                class="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-noche-700 to-noche-800 z-0"
              >
                <svg
                  class="w-10 h-10 text-noche-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="1.5"
                    d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
              </div>

              <!-- Thumbnail -->
              <img
                :src="getRecentFileThumbnail(file)"
                :alt="file.filename"
                class="absolute inset-0 w-full h-full object-cover z-10"
                loading="lazy"
                @error="($event.target as HTMLImageElement).style.display = 'none'"
              />

              <!-- Source badge -->
              <div
                class="absolute top-2 left-2 px-1.5 py-0.5 rounded text-[10px] font-medium z-20"
                :class="
                  file.source === 'youtube'
                    ? 'bg-tierra-500/90 text-white'
                    : 'bg-noche-700/90 text-noche-300'
                "
              >
                {{ file.source === "youtube" ? "YT" : "Media" }}
              </div>

              <!-- Resume indicator -->
              <div
                class="absolute bottom-2 left-2 flex items-center gap-1 px-2 py-0.5 bg-sol-500/90 rounded text-xs text-noche-950 font-medium shadow-lg z-20"
              >
                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
                {{ formatTime(file.last_timestamp) }}
              </div>
            </div>

            <!-- Filename -->
            <p
              class="mt-2 text-xs text-noche-300 truncate group-hover:text-noche-100 transition-colors"
              :title="file.filename"
            >
              {{ file.filename }}
            </p>
          </button>
        </div>
      </div>

      <!-- Loading indicator for recent files -->
      <div
        v-else-if="loadingRecent"
        class="h-32 flex items-center justify-center"
      >
        <div
          class="w-6 h-6 border-2 border-sol-500 border-t-transparent rounded-full animate-spin"
        ></div>
      </div>

      <!-- Category Tabs -->
      <div class="flex gap-2 p-1 bg-noche-800/50 rounded-xl">
        <button
          @click="activeCategory = 'youtube'"
          class="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg font-medium transition-all"
          :class="
            activeCategory === 'youtube'
              ? 'bg-tierra-500 text-white'
              : 'text-noche-400 hover:text-noche-200 hover:bg-noche-700/50'
          "
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path
              d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"
            />
          </svg>
          YouTube
        </button>
        <button
          @click="activeCategory = 'media'"
          class="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg font-medium transition-all"
          :class="
            activeCategory === 'media'
              ? 'bg-sol-500 text-noche-950'
              : 'text-noche-400 hover:text-noche-200 hover:bg-noche-700/50'
          "
        >
          <svg
            class="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
            />
          </svg>
          Media
        </button>
      </div>

      <!-- YouTube Tab Content -->
      <template v-if="activeCategory === 'youtube'">
        <!-- YouTube Downloader -->
        <div class="card space-y-4">
          <h3 class="font-medium text-noche-100">Download from YouTube</h3>

          <!-- URL Input -->
          <div>
            <div class="flex gap-2">
              <input
                v-model="youtubeUrl"
                type="text"
                placeholder="https://www.youtube.com/watch?v=..."
                class="input flex-1"
                @keydown.enter="fetchYouTubeInfo"
              />
              <button
                @click="fetchYouTubeInfo"
                :disabled="!youtubeUrl.trim() || youtubeLoading"
                class="btn btn-secondary px-4"
              >
                <span v-if="youtubeLoading">...</span>
                <span v-else>Check</span>
              </button>
            </div>
          </div>

          <!-- Error Message -->
          <div
            v-if="youtubeError"
            class="p-3 bg-tierra-500/10 border border-tierra-500/30 rounded-lg"
          >
            <p class="text-sm text-tierra-400">{{ youtubeError }}</p>
          </div>

          <!-- Success Message -->
          <div
            v-if="youtubeSuccess"
            class="p-3 bg-sol-500/10 border border-sol-500/30 rounded-lg"
          >
            <p class="text-sm text-sol-400 font-medium">Download complete!</p>
            <p class="text-xs text-noche-400 mt-1 font-mono truncate">
              {{ youtubeSuccess.file_path }}
            </p>
            <button
              @click="resetYouTubeForm"
              class="mt-2 text-xs text-sol-400 hover:text-sol-300"
            >
              Download another
            </button>
          </div>

          <!-- Video Info Preview -->
          <div
            v-if="youtubeInfo && !youtubeSuccess"
            class="p-3 bg-noche-800 rounded-lg space-y-3"
          >
            <div class="flex gap-3">
              <img
                v-if="youtubeInfo.thumbnail"
                :src="youtubeInfo.thumbnail"
                :alt="youtubeInfo.title"
                class="w-24 h-auto rounded flex-shrink-0"
              />
              <div class="flex-1 min-w-0">
                <h4 class="text-noche-100 font-medium line-clamp-2">
                  {{ youtubeInfo.title }}
                </h4>
                <p v-if="youtubeInfo.uploader" class="text-xs text-noche-500">
                  {{ youtubeInfo.uploader }}
                </p>
                <p
                  v-if="youtubeInfo.duration"
                  class="text-xs text-noche-500 mt-1"
                >
                  Duration: {{ formatDuration(youtubeInfo.duration) }}
                </p>
              </div>
            </div>

            <!-- Download Options -->
            <div class="flex items-center gap-4">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  v-model="youtubeAudioOnly"
                  class="w-4 h-4 rounded border-noche-600 bg-noche-700 text-sol-500"
                />
                <span class="text-sm text-noche-300">Audio only (MP3)</span>
              </label>
            </div>

            <!-- Download Button -->
            <button
              @click="downloadYouTube"
              :disabled="youtubeDownloading"
              class="btn btn-primary w-full"
            >
              <span v-if="youtubeDownloading" class="flex items-center gap-2">
                <div
                  class="w-4 h-4 border-2 border-noche-950 border-t-transparent rounded-full animate-spin"
                ></div>
                Downloading...
              </span>
              <span v-else>
                Download {{ youtubeAudioOnly ? "Audio" : "Video" }}
              </span>
            </button>
          </div>
        </div>

        <!-- Downloaded Videos List -->
        <div class="card">
          <h3 class="font-medium text-noche-100 mb-4">Downloaded Videos</h3>

          <div v-if="loadingDownloads" class="flex justify-center py-8">
            <div
              class="w-6 h-6 border-2 border-sol-500 border-t-transparent rounded-full animate-spin"
            ></div>
          </div>

          <div
            v-else-if="youtubeDownloads.length === 0"
            class="text-center py-8 text-noche-500"
          >
            <svg
              class="w-12 h-12 mx-auto mb-3 text-noche-700"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"
              />
            </svg>
            <p>No downloaded videos yet</p>
            <p class="text-xs mt-1">Use the form above to download</p>
          </div>

          <div v-else class="space-y-2 max-h-[40vh] overflow-y-auto">
            <button
              v-for="download in youtubeDownloads"
              :key="download.id"
              @click="handleYouTubeDownloadSelected(download)"
              class="w-full flex items-center gap-3 p-3 rounded-xl bg-noche-800/50 hover:bg-noche-800 transition-colors text-left group"
            >
              <!-- Thumbnail -->
              <div
                class="w-20 h-12 rounded-lg overflow-hidden flex-shrink-0 bg-noche-700"
              >
                <img
                  v-if="download.thumbnail_url"
                  :src="download.thumbnail_url"
                  :alt="download.title"
                  class="w-full h-full object-cover"
                />
                <div
                  v-else
                  class="w-full h-full flex items-center justify-center"
                >
                  <svg
                    class="w-6 h-6 text-noche-600"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M8 5v14l11-7z" />
                  </svg>
                </div>
              </div>

              <!-- Info -->
              <div class="flex-1 min-w-0">
                <p
                  class="text-noche-100 truncate group-hover:text-white transition-colors"
                >
                  {{ download.title }}
                </p>
                <div class="flex items-center gap-2 text-xs text-noche-500">
                  <span v-if="download.duration">{{
                    formatDuration(download.duration)
                  }}</span>
                  <span v-if="download.is_audio_only" class="text-tierra-400"
                    >Audio</span
                  >
                </div>
              </div>

              <!-- Arrow -->
              <svg
                class="w-5 h-5 text-noche-600 group-hover:text-noche-400 transition-colors flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          </div>
        </div>
      </template>

      <!-- Media Tab Content -->
      <template v-else-if="activeCategory === 'media'">
        <div class="card">
          <FileBrowser
            :initial-path="lastDirectory"
            :videos-only="true"
            @file-selected="handleFileSelected"
          />
        </div>
      </template>
    </template>

    <!-- Mode: Clip Selection -->
    <template v-else-if="mode === 'select'">
      <div class="card">
        <div class="mb-4 p-3 bg-noche-800 rounded-lg">
          <p class="text-sm text-noche-400">Selected file:</p>
          <p class="text-noche-200 font-mono text-sm truncate">
            {{ videoPath }}
          </p>
        </div>

        <ClipSelector
          :video-path="videoPath"
          :initial-time="initialTime"
          @clip-selected="handleClipSelected"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
</style>
