<script setup lang="ts">
import { computed, ref, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import { useSessionStore } from "@/stores/session";
import Spectrogram from "@/components/Spectrogram.vue";

const router = useRouter();
const sessionStore = useSessionStore();

const clipInfo = computed(() => sessionStore.currentClip);
const recordings = computed(() => sessionStore.recordings);

// Current recording index for navigation (0-indexed, shows most recent by default)
const currentRecordingIndex = ref(0);

// Current recording based on index (reversed so 0 = most recent)
const currentRecording = computed(() => {
  if (recordings.value.length === 0) return null;
  const reversed = [...recordings.value].reverse();
  return reversed[currentRecordingIndex.value] || null;
});

// Recording state
const isRecording = ref(false);
const recordingTime = ref(0);
let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];
let timerInterval: number | null = null;
let stream: MediaStream | null = null;

// Playback refs
const originalAudioRef = ref<HTMLAudioElement | null>(null);
const recordingAudioRef = ref<HTMLAudioElement | null>(null);
const isPlayingOriginal = ref(false);
const isPlayingRecording = ref(false);
const originalProgress = ref(0);
const recordingProgress = ref(0);
const pendingAutoPlay = ref(false);

// Audio element durations (fallback for seekhead when spectrogram hasn't loaded)
const originalAudioDuration = ref(0);
const recordingAudioDuration = ref(0);

// Animation frame for smooth seekhead
let animationFrameId: number | null = null;

const updateSeekhead = () => {
  if (originalAudioRef.value && isPlayingOriginal.value) {
    const duration = originalAudioRef.value.duration;
    if (duration && !isNaN(duration) && isFinite(duration)) {
      originalAudioDuration.value = duration;
      originalProgress.value = originalAudioRef.value.currentTime / duration;
    }
  }
  if (recordingAudioRef.value && isPlayingRecording.value) {
    // For WebM, audio.duration may be Infinity until fully loaded
    // Use spectrogram-provided duration instead
    const audioDuration = recordingAudioRef.value.duration;
    const knownDuration = currentRecordingDuration.value;
    const duration =
      knownDuration > 0
        ? knownDuration
        : audioDuration && !isNaN(audioDuration) && isFinite(audioDuration)
          ? audioDuration
          : 0;

    if (duration > 0) {
      recordingAudioDuration.value = duration;
      recordingProgress.value = recordingAudioRef.value.currentTime / duration;
    }
  }

  if (isPlayingOriginal.value || isPlayingRecording.value) {
    animationFrameId = requestAnimationFrame(updateSeekhead);
  } else {
    // Clear the ID when animation naturally stops
    animationFrameId = null;
  }
};

const startSeekheadAnimation = () => {
  if (!animationFrameId) {
    animationFrameId = requestAnimationFrame(updateSeekhead);
  }
};

const stopSeekheadAnimation = () => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
    animationFrameId = null;
  }
};

// Duration tracking for spectrogram scaling
const originalDuration = ref(0);
const recordingDurations = ref<Map<string, number>>(new Map());

const currentRecordingDuration = computed(() => {
  if (!currentRecording.value) return 0;
  // Use spectrogram duration if available, otherwise fall back to audio element duration
  return (
    recordingDurations.value.get(currentRecording.value.url) ||
    recordingAudioDuration.value ||
    0
  );
});

const maxDuration = computed(() => {
  // Use audio element durations as fallback
  const origDur = originalDuration.value || originalAudioDuration.value;
  const recDur = currentRecordingDuration.value;
  return Math.max(origDur, recDur) || 1; // Avoid division by zero
});

const onOriginalDuration = (duration: number) => {
  originalDuration.value = duration;
};

const onRecordingDuration = (duration: number) => {
  if (currentRecording.value) {
    // Create a new Map to ensure reactivity
    const newMap = new Map(recordingDurations.value);
    newMap.set(currentRecording.value.url, duration);
    recordingDurations.value = newMap;
  }
};

// Recording navigation
const canGoPrev = computed(
  () => currentRecordingIndex.value < recordings.value.length - 1,
);
const canGoNext = computed(() => currentRecordingIndex.value > 0);

const goPrevRecording = () => {
  if (canGoPrev.value) {
    stopRecordingPlayback();
    pendingAutoPlay.value = true;
    currentRecordingIndex.value++;
  }
};

const goNextRecording = () => {
  if (canGoNext.value) {
    stopRecordingPlayback();
    pendingAutoPlay.value = true;
    currentRecordingIndex.value--;
  }
};

// Reset to latest when new recording is made
watch(
  () => recordings.value.length,
  () => {
    currentRecordingIndex.value = 0;
  },
);

// Reset audio duration when switching recordings (but not during auto-play)
watch(currentRecording, () => {
  if (!pendingAutoPlay.value) {
    recordingAudioDuration.value = 0;
    recordingProgress.value = 0;
  }
});

// Format time helper
const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

// Recording functions
const startRecording = async () => {
  // Stop any playback first
  if (isPlayingOriginal.value) stopOriginal();
  if (isPlayingRecording.value) stopRecordingPlayback();

  audioChunks = [];
  recordingTime.value = 0;

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/ogg";

    mediaRecorder = new MediaRecorder(stream, { mimeType });

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, {
        type: mediaRecorder?.mimeType || "audio/webm",
      });
      cleanup();
      pendingAutoPlay.value = true;
      await sessionStore.saveRecording(audioBlob);
    };

    mediaRecorder.start(100);
    isRecording.value = true;

    timerInterval = window.setInterval(() => {
      recordingTime.value++;
    }, 1000);
  } catch (e) {
    console.error("Failed to start recording:", e);
  }
};

const stopRecording = () => {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
  isRecording.value = false;
};

const cleanup = () => {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }
  mediaRecorder = null;
  isRecording.value = false;
};

// Playback functions
const playOriginal = () => {
  if (!originalAudioRef.value) return;

  // Stop recording playback if playing
  if (isPlayingRecording.value) {
    stopRecordingPlayback();
  }

  originalAudioRef.value.currentTime = 0;
  originalAudioRef.value.play();
  isPlayingOriginal.value = true;
  startSeekheadAnimation();
};

const stopOriginal = () => {
  if (!originalAudioRef.value) return;
  originalAudioRef.value.pause();
  originalAudioRef.value.currentTime = 0;
  isPlayingOriginal.value = false;
  originalProgress.value = 0;
  if (!isPlayingRecording.value) stopSeekheadAnimation();
};

const playRecording = () => {
  if (!recordingAudioRef.value || !currentRecording.value) return;

  // Stop original playback if playing
  if (isPlayingOriginal.value) {
    stopOriginal();
  }

  recordingAudioRef.value.currentTime = 0;
  recordingAudioRef.value.play();
  isPlayingRecording.value = true;
  startSeekheadAnimation();
};

const stopRecordingPlayback = () => {
  if (!recordingAudioRef.value) return;
  recordingAudioRef.value.pause();
  // For WebM, currentTime=0 may not work; use load() to force reset
  recordingAudioRef.value.load();
  isPlayingRecording.value = false;
  recordingProgress.value = 0;
  if (!isPlayingOriginal.value) stopSeekheadAnimation();
};

const onOriginalEnded = () => {
  isPlayingOriginal.value = false;
  originalProgress.value = 0;
  if (!isPlayingRecording.value) stopSeekheadAnimation();
};

const onRecordingEnded = () => {
  isPlayingRecording.value = false;
  recordingProgress.value = 0;
  if (!isPlayingOriginal.value) stopSeekheadAnimation();
};

// Capture duration as soon as metadata loads
const onRecordingLoadedMetadata = () => {
  if (recordingAudioRef.value) {
    const duration = recordingAudioRef.value.duration;
    // WebM often reports Infinity until fully loaded
    if (duration && !isNaN(duration) && isFinite(duration)) {
      recordingAudioDuration.value = duration;
    }
  }
};

const onOriginalLoadedMetadata = () => {
  if (originalAudioRef.value) {
    const duration = originalAudioRef.value.duration;
    if (duration && !isNaN(duration) && isFinite(duration)) {
      originalAudioDuration.value = duration;
    }
  }
};

// Backup progress tracking via timeupdate event
const onRecordingTimeUpdate = () => {
  if (recordingAudioRef.value && isPlayingRecording.value) {
    const currentTime = recordingAudioRef.value.currentTime;
    const duration =
      currentRecordingDuration.value || recordingAudioDuration.value;
    if (duration > 0) {
      recordingProgress.value = currentTime / duration;
    }
  }
};

// Auto-play after recording
const onRecordingCanPlay = () => {
  if (pendingAutoPlay.value) {
    pendingAutoPlay.value = false;
    playRecording();
  }
};

// Navigation
const goBack = () => {
  sessionStore.endSession();
  router.push("/");
};

const finishClip = () => {
  sessionStore.endSession();
  router.push("/");
};

// Redirect if no session
if (!clipInfo.value) {
  router.push("/");
}
</script>

<template>
  <div
    v-if="clipInfo"
    class="grid grid-rows-2 gap-3 px-2 max-w-2xl lg:max-w-5xl mx-auto overflow-hidden"
    style="height: calc(100dvh - 11.5rem)"
  >
    <!-- Hidden audio elements -->
    <audio
      ref="originalAudioRef"
      :src="clipInfo.audioUrl"
      @ended="onOriginalEnded"
      @loadedmetadata="onOriginalLoadedMetadata"
      preload="auto"
    />
    <audio
      ref="recordingAudioRef"
      :src="currentRecording?.url"
      @ended="onRecordingEnded"
      @loadedmetadata="onRecordingLoadedMetadata"
      @timeupdate="onRecordingTimeUpdate"
      @canplaythrough="onRecordingCanPlay"
      preload="auto"
    />

    <!-- Original Audio Section -->
    <div class="relative rounded-xl overflow-hidden bg-noche-900">
      <Spectrogram
        v-if="clipInfo.audioUrl"
        :audio-url="clipInfo.audioUrl"
        :max-duration="maxDuration || undefined"
        class="w-full h-full"
        @duration="onOriginalDuration"
      />
      <!-- Seekhead -->
      <div
        v-if="isPlayingOriginal && maxDuration > 0"
        class="absolute top-0 w-0.5 h-full bg-sol-400 pointer-events-none"
        :style="{
          left: `${((originalProgress * originalDuration) / maxDuration) * 100}%`,
        }"
      />
      <!-- Label -->
      <div
        class="absolute top-2 left-2 text-xs text-white/70 bg-black/40 px-2 py-0.5 rounded"
      >
        Original
      </div>
      <!-- Play button overlay -->
      <button
        @click="isPlayingOriginal ? stopOriginal() : playOriginal()"
        class="absolute right-2 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full flex items-center justify-center transition-all"
        :class="
          isPlayingOriginal
            ? 'bg-sol-500 text-noche-950 scale-110'
            : 'bg-black/50 hover:bg-black/70 text-sol-400'
        "
      >
        <svg
          v-if="!isPlayingOriginal"
          class="w-6 h-6 ml-0.5"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path d="M8 5v14l11-7z" />
        </svg>
        <svg v-else class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
          <rect x="6" y="6" width="12" height="12" rx="2" />
        </svg>
      </button>
    </div>

    <!-- Recording Section -->
    <div class="relative rounded-xl overflow-hidden bg-noche-900">
      <template v-if="currentRecording">
        <Spectrogram
          :key="currentRecording.url"
          :audio-url="currentRecording.url"
          :max-duration="maxDuration || undefined"
          class="w-full h-full"
          @duration="onRecordingDuration"
        />
        <!-- Seekhead -->
        <div
          v-if="isPlayingRecording"
          class="absolute top-0 w-0.5 h-full bg-tierra-400 pointer-events-none"
          :style="{ left: `${recordingProgress * 100}%` }"
        />
      </template>
      <div
        v-else
        class="w-full h-full bg-noche-800 flex items-center justify-center"
      >
        <span class="text-noche-500 text-sm">Tap record to start</span>
      </div>
      <!-- Label -->
      <div
        class="absolute top-2 left-2 text-xs text-white/70 bg-black/40 px-2 py-0.5 rounded"
      >
        Recording
        <span v-if="recordings.length > 0" class="ml-1 text-white/90">
          {{ recordings.length - currentRecordingIndex }}/{{
            recordings.length
          }}
        </span>
      </div>
      <!-- Play button overlay -->
      <button
        v-if="currentRecording"
        @click="isPlayingRecording ? stopRecordingPlayback() : playRecording()"
        class="absolute right-2 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full flex items-center justify-center transition-all"
        :class="
          isPlayingRecording
            ? 'bg-tierra-500 text-noche-950 scale-110'
            : 'bg-black/50 hover:bg-black/70 text-tierra-400'
        "
      >
        <svg
          v-if="!isPlayingRecording"
          class="w-6 h-6 ml-0.5"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path d="M8 5v14l11-7z" />
        </svg>
        <svg v-else class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
          <rect x="6" y="6" width="12" height="12" rx="2" />
        </svg>
      </button>
    </div>

    <!-- Footer -->
    <div
      class="fixed bottom-0 left-0 right-0 bg-noche-950/95 backdrop-blur-sm border-t border-noche-800 safe-bottom z-50"
    >
      <div
        class="max-w-2xl lg:max-w-5xl mx-auto flex items-center gap-2 px-3 py-4"
      >
        <button
          @click="goBack"
          class="w-16 h-10 rounded-lg flex items-center justify-center bg-noche-800 hover:bg-noche-700 text-noche-300 text-sm"
        >
          Cancel
        </button>

        <button
          @click="goPrevRecording"
          :disabled="!canGoPrev"
          class="w-10 h-10 rounded-lg flex items-center justify-center"
          :class="
            canGoPrev ? 'text-noche-300 hover:bg-noche-800' : 'text-noche-700'
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
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>

        <button
          @click="isRecording ? stopRecording() : startRecording()"
          class="relative flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl"
          :class="
            isRecording ? 'bg-tierra-600' : 'bg-tierra-500 hover:bg-tierra-400'
          "
        >
          <span
            v-if="isRecording"
            class="absolute inset-0 rounded-xl bg-tierra-500 animate-ping opacity-25"
          />
          <svg
            v-if="!isRecording"
            class="w-5 h-5 text-white"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <circle cx="12" cy="12" r="6" />
          </svg>
          <svg
            v-else
            class="w-5 h-5 text-white"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <rect x="6" y="6" width="12" height="12" rx="2" />
          </svg>
          <span v-if="isRecording" class="font-mono text-white">{{
            formatTime(recordingTime)
          }}</span>
          <span v-else class="text-white text-sm font-medium">Record</span>
        </button>

        <button
          @click="goNextRecording"
          :disabled="!canGoNext"
          class="w-10 h-10 rounded-lg flex items-center justify-center"
          :class="
            canGoNext ? 'text-noche-300 hover:bg-noche-800' : 'text-noche-700'
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
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>

        <button
          @click="finishClip"
          class="w-16 h-10 rounded-lg flex items-center justify-center bg-sol-500 hover:bg-sol-400 text-noche-950 text-sm font-medium"
        >
          Next
        </button>
      </div>
    </div>
  </div>

  <!-- No Session State -->
  <div v-else class="text-center py-12">
    <p class="text-noche-400 mb-4">No active session</p>
    <button @click="router.push('/')" class="btn btn-primary">
      Start New Session
    </button>
  </div>
</template>
