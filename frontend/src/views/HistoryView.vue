<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { api } from "@/api/client";
import AudioPlayer from "@/components/AudioPlayer.vue";

interface Recording {
  id: number;
  filename: string;
  created_at: string;
  clip_id?: number;
  session_id?: number;
  attempt_number: number;
}

interface Stats {
  total_recordings: number;
  total_sessions: number;
  total_clips: number;
  total_practice_minutes: number;
  recordings_this_week: number;
  average_recordings_per_session: number;
}

// State
const recordings = ref<Recording[]>([]);
const stats = ref<Stats | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const activeTab = ref<"recordings" | "stats">("recordings");

const loadData = async () => {
  try {
    loading.value = true;
    error.value = null;

    const [recordingsData, statsData] = await Promise.all([
      api.listRecordings(),
      fetch("/api/stats").then((r) => r.json()),
    ]);

    recordings.value = recordingsData.recordings;
    stats.value = statsData;
  } catch (e) {
    error.value = "Failed to load data";
    console.error(e);
  } finally {
    loading.value = false;
  }
};

const deleteRecording = async (filename: string) => {
  if (!confirm("Delete this recording?")) return;

  try {
    await api.deleteRecording(filename);
    recordings.value = recordings.value.filter((r) => r.filename !== filename);
    if (stats.value) {
      stats.value.total_recordings--;
    }
  } catch (e) {
    console.error("Failed to delete recording:", e);
  }
};

const getRecordingUrl = (filename: string): string => {
  return api.getRecordingUrl(filename);
};

const formatDate = (dateStr: string): string => {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
};

const formatDuration = (minutes: number): string => {
  if (minutes < 60) {
    return `${Math.round(minutes)} min`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  return `${hours}h ${mins}m`;
};

onMounted(loadData);
</script>

<template>
  <div class="space-y-6 max-w-2xl mx-auto">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="font-display text-2xl font-bold text-noche-100">History</h1>
      <button @click="loadData" class="btn btn-secondary text-sm py-2">
        <svg
          class="w-4 h-4 mr-1 inline"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
        Refresh
      </button>
    </div>

    <!-- Tabs -->
    <div class="flex gap-2 p-1 bg-noche-900 rounded-xl">
      <button
        @click="activeTab = 'recordings'"
        class="flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors"
        :class="
          activeTab === 'recordings'
            ? 'bg-sol-500 text-noche-950'
            : 'text-noche-400 hover:text-noche-200'
        "
      >
        Recordings
      </button>
      <button
        @click="activeTab = 'stats'"
        class="flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors"
        :class="
          activeTab === 'stats'
            ? 'bg-sol-500 text-noche-950'
            : 'text-noche-400 hover:text-noche-200'
        "
      >
        Statistics
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div
        class="inline-block w-8 h-8 border-4 border-sol-500 border-t-transparent rounded-full animate-spin"
      ></div>
      <p class="text-noche-400 mt-4">Loading...</p>
    </div>

    <!-- Error State -->
    <div
      v-else-if="error"
      class="card bg-tierra-500/10 border-tierra-500/30 text-center"
    >
      <p class="text-tierra-400">{{ error }}</p>
      <button @click="loadData" class="btn btn-secondary mt-4">
        Try Again
      </button>
    </div>

    <!-- Recordings Tab -->
    <template v-else-if="activeTab === 'recordings'">
      <!-- Empty State -->
      <div v-if="recordings.length === 0" class="text-center py-12">
        <svg
          class="w-16 h-16 mx-auto text-noche-700"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
          />
        </svg>
        <p class="text-noche-400 mt-4">No recordings yet</p>
        <p class="text-noche-500 text-sm">
          Start a practice session to create your first recording
        </p>
      </div>

      <!-- Recordings List -->
      <div v-else class="space-y-3">
        <div v-for="recording in recordings" :key="recording.id" class="card">
          <div class="flex items-start justify-between mb-3">
            <div>
              <p class="text-sm text-noche-300">
                {{ formatDate(recording.created_at) }}
              </p>
              <div class="flex items-center gap-2 mt-1">
                <span
                  class="text-xs text-noche-500 bg-noche-800 px-2 py-0.5 rounded"
                >
                  Attempt #{{ recording.attempt_number }}
                </span>
                <span
                  v-if="recording.clip_id"
                  class="text-xs text-sol-500 bg-sol-500/10 px-2 py-0.5 rounded"
                >
                  Clip #{{ recording.clip_id }}
                </span>
              </div>
            </div>
            <button
              @click="deleteRecording(recording.filename)"
              class="text-noche-500 hover:text-tierra-400 transition-colors p-1"
              title="Delete recording"
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
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          </div>

          <AudioPlayer
            :src="getRecordingUrl(recording.filename)"
            label="Play"
            variant="secondary"
          />
        </div>
      </div>
    </template>

    <!-- Stats Tab -->
    <template v-else-if="activeTab === 'stats' && stats">
      <div class="grid grid-cols-2 gap-4">
        <!-- Total Recordings -->
        <div class="card text-center">
          <div class="text-3xl font-display font-bold text-sol-400">
            {{ stats.total_recordings }}
          </div>
          <div class="text-sm text-noche-400 mt-1">Total Recordings</div>
        </div>

        <!-- This Week -->
        <div class="card text-center">
          <div class="text-3xl font-display font-bold text-tierra-400">
            {{ stats.recordings_this_week }}
          </div>
          <div class="text-sm text-noche-400 mt-1">This Week</div>
        </div>

        <!-- Total Sessions -->
        <div class="card text-center">
          <div class="text-3xl font-display font-bold text-noche-200">
            {{ stats.total_sessions }}
          </div>
          <div class="text-sm text-noche-400 mt-1">Sessions</div>
        </div>

        <!-- Total Clips -->
        <div class="card text-center">
          <div class="text-3xl font-display font-bold text-noche-200">
            {{ stats.total_clips }}
          </div>
          <div class="text-sm text-noche-400 mt-1">Clips Practiced</div>
        </div>
      </div>

      <!-- Additional Stats -->
      <div class="card space-y-4">
        <h3 class="font-semibold text-noche-200">Practice Summary</h3>

        <div
          class="flex items-center justify-between py-2 border-b border-noche-800"
        >
          <span class="text-noche-400">Total Practice Time</span>
          <span class="text-noche-100 font-semibold">
            {{ formatDuration(stats.total_practice_minutes) }}
          </span>
        </div>

        <div
          class="flex items-center justify-between py-2 border-b border-noche-800"
        >
          <span class="text-noche-400">Avg Recordings per Session</span>
          <span class="text-noche-100 font-semibold">
            {{ stats.average_recordings_per_session }}
          </span>
        </div>

        <div class="pt-2">
          <p class="text-sm text-noche-500 text-center">
            Keep practicing! Consistency is key to improving pronunciation.
          </p>
        </div>
      </div>

      <!-- Motivational Card -->
      <div
        class="card bg-gradient-to-br from-sol-500/20 to-tierra-500/20 border-sol-500/30"
      >
        <div class="text-center">
          <p class="text-lg font-display font-semibold text-sol-300">
            {{
              stats.recordings_this_week >= 7
                ? "🔥 On Fire!"
                : stats.recordings_this_week >= 3
                  ? "👍 Good Progress!"
                  : "💪 Keep Going!"
            }}
          </p>
          <p class="text-sm text-noche-300 mt-2">
            {{
              stats.recordings_this_week >= 7
                ? "Amazing consistency this week! Your pronunciation is definitely improving."
                : stats.recordings_this_week >= 3
                  ? "Nice work! Try to practice a little every day."
                  : "Every recording counts. Try to practice at least once a day!"
            }}
          </p>
        </div>
      </div>
    </template>
  </div>
</template>
