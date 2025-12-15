<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import AudioRecorder from '@/components/AudioRecorder.vue'
import AudioPlayer from '@/components/AudioPlayer.vue'
import Spectrogram from '@/components/Spectrogram.vue'

const router = useRouter()
const sessionStore = useSessionStore()

const clipInfo = computed(() => sessionStore.currentClip)
const lastRecording = computed(() => sessionStore.lastRecording)
const recordings = computed(() => sessionStore.recordings)
const isLoading = computed(() => sessionStore.isLoading)

// UI State
const showSpectrograms = ref(true)
const showFinishDialog = ref(false)

const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const handleRecordingComplete = async (audioBlob: Blob) => {
  await sessionStore.saveRecording(audioBlob)
}

const confirmFinish = () => {
  showFinishDialog.value = true
}

const finishClip = () => {
  sessionStore.endSession()
  router.push('/')
}

const cancelFinish = () => {
  showFinishDialog.value = false
}

// Redirect if no session is active
if (!clipInfo.value) {
  router.push('/')
}
</script>

<template>
  <div v-if="clipInfo" class="space-y-6 pb-24">
    <!-- Clip Info Header -->
    <div class="card">
      <div class="flex items-center justify-between mb-2">
        <h2 class="font-display text-xl font-bold text-noche-100">
          Current Clip
        </h2>
        <span class="text-sm text-noche-400 bg-noche-800 px-3 py-1 rounded-full">
          {{ formatTime(clipInfo.startTime) }} - {{ formatTime(clipInfo.endTime) }}
        </span>
      </div>
      <p class="text-sm text-noche-500 truncate font-mono">
        {{ clipInfo.videoPath.split('/').pop() }}
      </p>
      <div class="mt-3 flex items-center gap-4">
        <span class="text-sm text-noche-400">
          Attempts: <span class="text-sol-400 font-semibold">{{ recordings.length }}</span>
        </span>
        <button
          @click="showSpectrograms = !showSpectrograms"
          class="text-sm text-noche-400 hover:text-noche-200 transition-colors flex items-center gap-1"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          {{ showSpectrograms ? 'Hide' : 'Show' }} Spectrograms
        </button>
      </div>
    </div>

    <!-- Original Audio Section -->
    <div class="card">
      <h3 class="font-semibold text-noche-200 mb-4 flex items-center gap-2">
        <svg class="w-5 h-5 text-sol-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
            d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
        </svg>
        Original Audio
      </h3>
      
      <AudioPlayer
        v-if="clipInfo.audioUrl"
        :src="clipInfo.audioUrl"
        label="Play Original"
      />
      
      <div v-else class="text-center py-8 text-noche-500">
        <div class="inline-block w-6 h-6 border-2 border-sol-500 border-t-transparent rounded-full animate-spin mb-2"></div>
        <p>Extracting audio...</p>
      </div>

      <!-- Original Spectrogram -->
      <div v-if="showSpectrograms && clipInfo.audioUrl" class="mt-4 pt-4 border-t border-noche-700">
        <Spectrogram
          :audio-url="clipInfo.audioUrl"
          label="Original Spectrogram"
        />
      </div>
    </div>

    <!-- Recording Section -->
    <div class="card">
      <h3 class="font-semibold text-noche-200 mb-4 flex items-center gap-2">
        <svg class="w-5 h-5 text-tierra-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
        Your Recording
      </h3>
      
      <AudioRecorder @recording-complete="handleRecordingComplete" />
      
      <!-- Last Recording Playback -->
      <div v-if="lastRecording" class="mt-6 pt-4 border-t border-noche-700">
        <div class="flex items-center justify-between mb-3">
          <p class="text-sm text-noche-400">Last Recording (Attempt #{{ recordings.length }})</p>
        </div>
        
        <AudioPlayer
          :src="lastRecording.url"
          label="Play Your Recording"
          variant="secondary"
        />

        <!-- Recording Spectrogram -->
        <div v-if="showSpectrograms" class="mt-4 pt-4 border-t border-noche-700">
          <Spectrogram
            :audio-url="lastRecording.url"
            label="Your Spectrogram"
          />
        </div>
      </div>
    </div>

    <!-- Recording History -->
    <div v-if="recordings.length > 1" class="card">
      <h3 class="font-semibold text-noche-200 mb-4">Previous Attempts</h3>
      <div class="space-y-3 max-h-48 overflow-y-auto">
        <div
          v-for="(recording, index) in recordings.slice(0, -1).reverse()"
          :key="recording.id"
          class="flex items-center gap-3 p-3 bg-noche-800 rounded-lg"
        >
          <span class="text-xs text-noche-500 w-16">
            Attempt {{ recordings.length - 1 - index }}
          </span>
          <div class="flex-1">
            <AudioPlayer
              :src="recording.url"
              variant="secondary"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Fixed Bottom Actions -->
    <div class="fixed bottom-0 left-0 right-0 p-4 bg-noche-950/95 backdrop-blur-sm border-t border-noche-800 safe-bottom">
      <div class="max-w-2xl mx-auto flex gap-3">
        <button @click="router.push('/')" class="btn btn-secondary flex-1">
          Cancel
        </button>
        <button @click="confirmFinish" class="btn btn-primary flex-1">
          Finish Clip
        </button>
      </div>
    </div>

    <!-- Finish Dialog -->
    <Teleport to="body">
      <div 
        v-if="showFinishDialog"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70"
        @click.self="cancelFinish"
      >
        <div class="card max-w-sm w-full space-y-4 animate-in fade-in zoom-in duration-200">
          <h3 class="font-display text-xl font-bold text-noche-100">
            Finish This Clip?
          </h3>
          <p class="text-noche-400">
            You made <span class="text-sol-400 font-semibold">{{ recordings.length }}</span> recording{{ recordings.length !== 1 ? 's' : '' }}.
            All recordings have been saved and can be reviewed later.
          </p>
          <div class="flex gap-3 pt-2">
            <button @click="cancelFinish" class="btn btn-secondary flex-1">
              Keep Practicing
            </button>
            <button @click="finishClip" class="btn btn-primary flex-1">
              Finish
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>

  <!-- No Session State -->
  <div v-else class="text-center py-12">
    <p class="text-noche-400 mb-4">No active session</p>
    <button @click="router.push('/')" class="btn btn-primary">
      Start New Session
    </button>
  </div>
</template>

<style scoped>
@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes zoom-in {
  from { transform: scale(0.95); }
  to { transform: scale(1); }
}

.animate-in {
  animation: fade-in 0.2s ease-out, zoom-in 0.2s ease-out;
}
</style>
