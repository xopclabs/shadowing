<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import FileBrowser from '@/components/FileBrowser.vue'
import ClipSelector from '@/components/ClipSelector.vue'

const router = useRouter()
const sessionStore = useSessionStore()

const LAST_DIR_KEY = 'shadowing_last_directory'

// UI State
const mode = ref<'browse' | 'select'>('browse')

// Form data
const videoPath = ref('')
const lastDirectory = ref('/mnt')

// Loading state
const isLoading = ref(false)
const errorMessage = ref('')

// Load last directory from localStorage
onMounted(() => {
  const saved = localStorage.getItem(LAST_DIR_KEY)
  if (saved) {
    lastDirectory.value = saved
  }
})

const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const handleFileSelected = (path: string) => {
  videoPath.value = path
  
  // Save the directory of the selected file
  const lastSlash = path.lastIndexOf('/')
  if (lastSlash > 0) {
    const dir = path.substring(0, lastSlash)
    localStorage.setItem(LAST_DIR_KEY, dir)
    lastDirectory.value = dir
  }
  
  mode.value = 'select'
}

const handleClipSelected = async (start: number, end: number) => {
  if (!videoPath.value.trim()) {
    errorMessage.value = 'No video selected'
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
  mode.value = 'browse'
  videoPath.value = ''
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
        {{ mode === 'browse' ? 'Select a video file' : 'Select the clip to practice' }}
      </p>
    </div>

    <!-- Error Message -->
    <div v-if="errorMessage" class="p-4 bg-tierra-500/10 border border-tierra-500/30 rounded-xl">
      <p class="text-tierra-400 text-center">{{ errorMessage }}</p>
    </div>

    <!-- Back Button -->
    <button 
      v-if="mode === 'select'"
      @click="goBack"
      class="flex items-center gap-2 text-noche-400 hover:text-noche-200 transition-colors"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      Back to files
    </button>

    <!-- Mode: File Browser -->
    <template v-if="mode === 'browse'">
      <div class="card">
        <FileBrowser 
          :initial-path="lastDirectory"
          :videos-only="true"
          @file-selected="handleFileSelected"
        />
      </div>
      
      <!-- Quick Tips -->
      <div class="card bg-sol-500/10 border-sol-500/30">
        <h3 class="font-semibold text-sol-400 mb-2">Quick Tips</h3>
        <ul class="text-sm text-noche-300 space-y-1">
          <li>• Choose short clips (5-15 seconds) for better practice</li>
          <li>• Listen multiple times before recording</li>
          <li>• Focus on rhythm and intonation first, then accuracy</li>
        </ul>
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
