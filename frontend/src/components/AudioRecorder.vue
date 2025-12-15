<script setup lang="ts">
import { ref, onUnmounted } from 'vue'

const emit = defineEmits<{
  (e: 'recording-complete', blob: Blob): void
}>()

// State
const isRecording = ref(false)
const isPaused = ref(false)
const recordingTime = ref(0)
const error = ref<string | null>(null)

// MediaRecorder references
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []
let timerInterval: number | null = null
let stream: MediaStream | null = null

const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const startRecording = async () => {
  error.value = null
  audioChunks = []
  recordingTime.value = 0

  try {
    // Request microphone permission
    stream = await navigator.mediaDevices.getUserMedia({ 
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      } 
    })

    // Determine supported MIME type
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/ogg'

    mediaRecorder = new MediaRecorder(stream, { mimeType })

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: mediaRecorder?.mimeType || 'audio/webm' })
      emit('recording-complete', audioBlob)
      cleanup()
    }

    mediaRecorder.onerror = (event) => {
      console.error('MediaRecorder error:', event)
      error.value = 'Recording error occurred'
      cleanup()
    }

    // Start recording
    mediaRecorder.start(100) // Collect data every 100ms
    isRecording.value = true
    isPaused.value = false

    // Start timer
    timerInterval = window.setInterval(() => {
      if (!isPaused.value) {
        recordingTime.value++
      }
    }, 1000)
  } catch (e) {
    console.error('Failed to start recording:', e)
    if (e instanceof DOMException && e.name === 'NotAllowedError') {
      error.value = 'Microphone access denied. Please allow microphone access.'
    } else {
      error.value = 'Failed to start recording. Please check your microphone.'
    }
  }
}

const stopRecording = () => {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  isRecording.value = false
  isPaused.value = false
}

const togglePause = () => {
  if (!mediaRecorder) return

  if (isPaused.value) {
    mediaRecorder.resume()
    isPaused.value = false
  } else {
    mediaRecorder.pause()
    isPaused.value = true
  }
}

const cleanup = () => {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
  if (stream) {
    stream.getTracks().forEach(track => track.stop())
    stream = null
  }
  mediaRecorder = null
  isRecording.value = false
  isPaused.value = false
}

onUnmounted(cleanup)
</script>

<template>
  <div class="space-y-4">
    <!-- Error Message -->
    <div v-if="error" class="p-3 rounded-lg bg-tierra-500/20 border border-tierra-500/30 text-tierra-300 text-sm">
      {{ error }}
    </div>

    <!-- Recording Controls -->
    <div class="flex items-center justify-center gap-4">
      <!-- Record/Stop Button -->
      <button
        @click="isRecording ? stopRecording() : startRecording()"
        class="btn-icon relative"
        :class="isRecording ? 'bg-tierra-600 hover:bg-tierra-500' : 'bg-tierra-500 hover:bg-tierra-400'"
      >
        <!-- Pulse animation when recording -->
        <span
          v-if="isRecording && !isPaused"
          class="absolute inset-0 rounded-full bg-tierra-500 animate-ping opacity-25"
        ></span>
        
        <!-- Icon -->
        <svg v-if="!isRecording" class="w-8 h-8 text-white relative z-10" fill="currentColor" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="6" />
        </svg>
        <svg v-else class="w-8 h-8 text-white relative z-10" fill="currentColor" viewBox="0 0 24 24">
          <rect x="6" y="6" width="12" height="12" rx="2" />
        </svg>
      </button>

      <!-- Pause/Resume Button (only when recording) -->
      <button
        v-if="isRecording"
        @click="togglePause"
        class="btn-icon bg-noche-700 hover:bg-noche-600"
      >
        <svg v-if="isPaused" class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
          <path d="M8 5v14l11-7z" />
        </svg>
        <svg v-else class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
          <rect x="6" y="4" width="4" height="16" rx="1" />
          <rect x="14" y="4" width="4" height="16" rx="1" />
        </svg>
      </button>
    </div>

    <!-- Timer Display -->
    <div class="text-center">
      <span 
        class="font-mono text-2xl"
        :class="isRecording ? 'text-tierra-400' : 'text-noche-500'"
      >
        {{ formatTime(recordingTime) }}
      </span>
      <p class="text-sm text-noche-500 mt-1">
        <template v-if="!isRecording">Tap to start recording</template>
        <template v-else-if="isPaused">Paused - tap play to resume</template>
        <template v-else>Recording... tap square to stop</template>
      </p>
    </div>
  </div>
</template>

