<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  src: string
  label?: string
  variant?: 'primary' | 'secondary'
}>(), {
  label: 'Play',
  variant: 'primary',
})

// State
const isPlaying = ref(false)
const isLoading = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const error = ref<string | null>(null)

// Audio element reference
let audio: HTMLAudioElement | null = null

const formatTime = (seconds: number): string => {
  if (!isFinite(seconds) || isNaN(seconds)) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const progress = ref(0)

const initAudio = () => {
  if (audio) {
    audio.pause()
    audio.removeEventListener('timeupdate', onTimeUpdate)
    audio.removeEventListener('ended', onEnded)
    audio.removeEventListener('loadedmetadata', onLoadedMetadata)
    audio.removeEventListener('error', onError)
    audio.removeEventListener('canplay', onCanPlay)
  }

  audio = new Audio(props.src)
  audio.preload = 'metadata'

  audio.addEventListener('timeupdate', onTimeUpdate)
  audio.addEventListener('ended', onEnded)
  audio.addEventListener('loadedmetadata', onLoadedMetadata)
  audio.addEventListener('error', onError)
  audio.addEventListener('canplay', onCanPlay)
}

const onTimeUpdate = () => {
  if (audio) {
    currentTime.value = audio.currentTime
    progress.value = (audio.currentTime / audio.duration) * 100 || 0
  }
}

const onEnded = () => {
  isPlaying.value = false
  currentTime.value = 0
  progress.value = 0
}

const onLoadedMetadata = () => {
  if (audio) {
    duration.value = audio.duration
  }
}

const onCanPlay = () => {
  isLoading.value = false
}

const onError = () => {
  error.value = 'Failed to load audio'
  isPlaying.value = false
  isLoading.value = false
}

const togglePlay = async () => {
  if (!audio) return
  error.value = null

  try {
    if (isPlaying.value) {
      audio.pause()
      isPlaying.value = false
    } else {
      isLoading.value = true
      await audio.play()
      isPlaying.value = true
      isLoading.value = false
    }
  } catch (e) {
    console.error('Playback error:', e)
    error.value = 'Failed to play audio'
    isPlaying.value = false
    isLoading.value = false
  }
}

const seek = (event: MouseEvent) => {
  if (!audio || !duration.value) return

  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const percent = (event.clientX - rect.left) / rect.width
  audio.currentTime = percent * duration.value
}

// Initialize audio when src changes
watch(() => props.src, initAudio, { immediate: true })

onUnmounted(() => {
  if (audio) {
    audio.pause()
    audio.removeEventListener('timeupdate', onTimeUpdate)
    audio.removeEventListener('ended', onEnded)
    audio.removeEventListener('loadedmetadata', onLoadedMetadata)
    audio.removeEventListener('error', onError)
    audio.removeEventListener('canplay', onCanPlay)
    audio = null
  }
})
</script>

<template>
  <div class="space-y-3">
    <!-- Error Message -->
    <div v-if="error" class="text-sm text-tierra-400">
      {{ error }}
    </div>

    <!-- Player Controls -->
    <div class="flex items-center gap-3">
      <!-- Play/Pause Button -->
      <button
        @click="togglePlay"
        class="btn-icon flex-shrink-0"
        :class="variant === 'primary' 
          ? 'bg-sol-500 hover:bg-sol-400 text-noche-950' 
          : 'bg-noche-700 hover:bg-noche-600 text-noche-100'"
        :disabled="isLoading"
      >
        <!-- Loading Spinner -->
        <svg v-if="isLoading" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <!-- Play Icon -->
        <svg v-else-if="!isPlaying" class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M8 5v14l11-7z" />
        </svg>
        <!-- Pause Icon -->
        <svg v-else class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
          <rect x="6" y="4" width="4" height="16" rx="1" />
          <rect x="14" y="4" width="4" height="16" rx="1" />
        </svg>
      </button>

      <!-- Progress Bar -->
      <div class="flex-1 space-y-1">
        <div 
          class="h-2 bg-noche-800 rounded-full cursor-pointer overflow-hidden"
          @click="seek"
        >
          <div 
            class="h-full rounded-full transition-all duration-100"
            :class="variant === 'primary' ? 'bg-sol-500' : 'bg-noche-500'"
            :style="{ width: `${progress}%` }"
          ></div>
        </div>
        
        <!-- Time Display -->
        <div class="flex justify-between text-xs text-noche-500">
          <span>{{ formatTime(currentTime) }}</span>
          <span>{{ formatTime(duration) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

