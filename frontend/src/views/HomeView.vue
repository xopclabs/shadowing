<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useSessionStore } from "@/stores/session";
import { api, type RecentFile } from "@/api/client";
import FileBrowser from "@/components/FileBrowser.vue";
import ClipSelector from "@/components/ClipSelector.vue";

const router = useRouter();
const sessionStore = useSessionStore();

const LAST_DIR_KEY = "shadowing_last_directory";

// UI State
const mode = ref<"browse" | "select">("browse");

// Form data
const videoPath = ref("");
const initialTime = ref<number | undefined>(undefined);
const lastDirectory = ref("/mnt");

// Recent files (from API)
const recentFiles = ref<RecentFile[]>([]);
const loadingRecent = ref(false);

// Loading state
const isLoading = ref(false);
const errorMessage = ref("");

// Load data
onMounted(async () => {
  const savedDir = localStorage.getItem(LAST_DIR_KEY);
  if (savedDir) {
    lastDirectory.value = savedDir;
  }

  // Load recent files from API
  loadingRecent.value = true;
  try {
    recentFiles.value = await api.listRecentFiles();
  } catch (e) {
    console.warn("Failed to load recent files:", e);
  } finally {
    loadingRecent.value = false;
  }
});

// Format time for display
const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

const handleFileSelected = (path: string) => {
  videoPath.value = path;
  initialTime.value = undefined; // Fresh file, start from beginning

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
  initialTime.value = file.last_timestamp; // Resume from last position
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
    // Save to recent files via API
    await api.addRecentFile(videoPath.value, start);

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
</script>

<template>
  <div class="space-y-6 max-w-2xl mx-auto">
    <!-- Header -->
    <div class="text-center space-y-2">
      <h1 class="font-display text-3xl font-bold text-noche-100">
        Practice Your Spanish
      </h1>
      <p class="text-noche-400">
        {{
          mode === "browse"
            ? "Select a video file"
            : "Select the clip to practice"
        }}
      </p>
    </div>

    <!-- Error Message -->
    <div
      v-if="errorMessage"
      class="p-4 bg-tierra-500/10 border border-tierra-500/30 rounded-xl"
    >
      <p class="text-tierra-400 text-center">{{ errorMessage }}</p>
    </div>

    <!-- Back Button -->
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
      Back to files
    </button>

    <!-- Mode: File Browser -->
    <template v-if="mode === 'browse'">
      <!-- Recent Files Carousel -->
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
              <!-- Fallback icon (behind thumbnail) -->
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

              <!-- Thumbnail (on top of fallback) -->
              <img
                :src="api.getThumbnailUrl(file.video_path, file.last_timestamp)"
                :alt="file.filename"
                class="absolute inset-0 w-full h-full object-cover z-10"
                loading="lazy"
              />

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

      <!-- File Browser -->
      <div class="card">
        <FileBrowser
          :initial-path="lastDirectory"
          :videos-only="true"
          @file-selected="handleFileSelected"
        />
      </div>
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
