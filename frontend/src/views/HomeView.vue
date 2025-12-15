<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import FileBrowser from '@/components/FileBrowser.vue'
import ClipSelector from '@/components/ClipSelector.vue'

const router = useRouter()
const sessionStore = useSessionStore()

// UI State
const mode = ref<'input' | 'browse' | 'select'>('input')

// Form data
const videoPath = ref('')
const startTime = ref('0:00')
const endTime = ref('0:10')

// Loading state
const isLoading = ref(false)
const errorMessage = ref('')

const parseTime = (timeStr: string): number => {
  const parts = timeStr.split(':').map(Number)
  if (parts.length === 3) {
    // HH:MM:SS
    return parts[0] * 3600 + parts[1] * 60 + parts[2]
  } else if (parts.length === 2) {
    // MM:SS or M:SS.s
    const seconds = parts[1]
    return parts[0] * 60 + seconds
  }
  return parseFloat(timeStr) || 0
}

const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const handleFileSelected = (path: string) => {
  videoPath.value = path
  mode.value = 'select'
}

const handleClipSelected = (start: number, end: number) => {
  startTime.value = formatTime(start)
  endTime.value = formatTime(end)
  startSession()
}

const startSession = async () => {
  if (!videoPath.value.trim()) {
    errorMessage.value = 'Please enter a video path'
    return
  }

  const start = parseTime(startTime.value)
  const end = parseTime(endTime.value)

  if (end <= start) {
    errorMessage.value = 'End time must be after start time'
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    await sessionStore.startSession({
      videoPath: videoPath.value.trim(),
      startTime: start,
      endTime: end,
    })
    router.push('/session')
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : 'Failed to start session'
  } finally {
    isLoading.value = false
  }
}

const goBack = () => {
  if (mode.value === 'select') {
    mode.value = 'browse'
  } else if (mode.value === 'browse') {
    mode.value = 'input'
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="text-center space-y-2">
      <h1 class="font-display text-3xl font-bold text-noche-100">
        Practice Your Spanish
      </h1>
      <p class="text-noche-400">
        {{ mode === 'input' ? 'Enter a video path or browse files' : 
           mode === 'browse' ? 'Select a video file' : 
           'Select the clip to practice' }}
      </p>
    </div>

    <!-- Error Message -->
    <div v-if="errorMessage" class="p-4 bg-tierra-500/10 border border-tierra-500/30 rounded-xl">
      <p class="text-tierra-400 text-center">{{ errorMessage }}</p>
    </div>

    <!-- Back Button -->
    <button 
      v-if="mode !== 'input'"
      @click="goBack"
      class="flex items-center gap-2 text-noche-400 hover:text-noche-200 transition-colors"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      Back
    </button>

    <!-- Mode: Manual Input -->
    <template v-if="mode === 'input'">
      <div class="card space-y-6">
        <div class="space-y-2">
          <label for="videoPath" class="block text-sm font-medium text-noche-300">
            Video File Path
          </label>
          <input
            id="videoPath"
            v-model="videoPath"
            type="text"
            class="input"
            placeholder="/media/videos/spanish_lesson.mp4"
          />
          <p class="text-xs text-noche-500">
            Full path to the video file on the server
          </p>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <label for="startTime" class="block text-sm font-medium text-noche-300">
              Start Time
            </label>
            <input
              id="startTime"
              v-model="startTime"
              type="text"
              class="input"
              placeholder="0:00"
            />
          </div>
          <div class="space-y-2">
            <label for="endTime" class="block text-sm font-medium text-noche-300">
              End Time
            </label>
            <input
              id="endTime"
              v-model="endTime"
              type="text"
              class="input"
              placeholder="0:10"
            />
          </div>
        </div>

        <div class="flex gap-3">
          <button 
            @click="mode = 'browse'"
            class="btn btn-secondary flex-1"
          >
            <svg class="w-5 h-5 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            Browse Files
          </button>
          <button 
            @click="startSession"
            :disabled="isLoading"
            class="btn btn-primary flex-1"
          >
            <span v-if="isLoading" class="inline-block w-4 h-4 border-2 border-noche-950 border-t-transparent rounded-full animate-spin mr-2"></span>
            Start Practice
          </button>
        </div>
      </div>

      <!-- Quick Tips -->
      <div class="card bg-sol-500/10 border-sol-500/30">
        <h3 class="font-semibold text-sol-400 mb-2">Quick Tips</h3>
        <ul class="text-sm text-noche-300 space-y-1">
          <li>• Choose short clips (5-15 seconds) for better practice</li>
          <li>• Time format: MM:SS or HH:MM:SS</li>
          <li>• Listen multiple times before recording</li>
          <li>• Focus on rhythm and intonation first, then accuracy</li>
        </ul>
      </div>
    </template>

    <!-- Mode: File Browser -->
    <template v-else-if="mode === 'browse'">
      <div class="card">
        <FileBrowser 
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
          <p class="text-noche-200 font-mono text-sm truncate">{{ videoPath }}</p>
        </div>
        
        <ClipSelector
          :video-path="videoPath"
          @clip-selected="handleClipSelected"
        />
      </div>
    </template>
  </div>
</template>
