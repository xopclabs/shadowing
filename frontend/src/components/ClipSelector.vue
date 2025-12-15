<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'

const props = defineProps<{
  videoPath: string
}>()

const emit = defineEmits<{
  (e: 'clip-selected', start: number, end: number): void
}>()

// Refs
const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)

// State
const isLoading = ref(true)
const duration = ref(0)
const currentTime = ref(0)
const isPlaying = ref(false)
const selectionStart = ref<number | null>(null)
const selectionEnd = ref<number | null>(null)
const isDragging = ref(false)
const dragType = ref<'start' | 'end' | 'region' | null>(null)
const dragStartX = ref(0)
const dragStartTime = ref(0)

// Computed
const hasSelection = computed(() => 
  selectionStart.value !== null && selectionEnd.value !== null
)

const selectionDuration = computed(() => {
  if (!hasSelection.value) return 0
  return (selectionEnd.value! - selectionStart.value!).toFixed(1)
})

// Format time helper
const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 10)
  return `${mins}:${secs.toString().padStart(2, '0')}.${ms}`
}

// Get position from time
const timeToPosition = (time: number): number => {
  if (!containerRef.value || duration.value === 0) return 0
  return (time / duration.value) * containerRef.value.clientWidth
}

// Get time from position
const positionToTime = (x: number): number => {
  if (!containerRef.value || duration.value === 0) return 0
  const rect = containerRef.value.getBoundingClientRect()
  const relativeX = Math.max(0, Math.min(x - rect.left, rect.width))
  return (relativeX / rect.width) * duration.value
}

// Video event handlers
const onLoadedMetadata = () => {
  if (videoRef.value) {
    duration.value = videoRef.value.duration
    isLoading.value = false
    // Default selection: first 5 seconds or full duration if shorter
    selectionStart.value = 0
    selectionEnd.value = Math.min(5, duration.value)
  }
}

const onTimeUpdate = () => {
  if (videoRef.value) {
    currentTime.value = videoRef.value.currentTime
    
    // Loop within selection if playing
    if (isPlaying.value && hasSelection.value) {
      if (currentTime.value >= selectionEnd.value!) {
        videoRef.value.currentTime = selectionStart.value!
      }
    }
  }
}

const togglePlay = () => {
  if (!videoRef.value) return
  
  if (isPlaying.value) {
    videoRef.value.pause()
    isPlaying.value = false
  } else {
    // Start from selection start
    if (hasSelection.value) {
      videoRef.value.currentTime = selectionStart.value!
    }
    videoRef.value.play()
    isPlaying.value = true
  }
}

const seek = (time: number) => {
  if (videoRef.value) {
    videoRef.value.currentTime = time
    currentTime.value = time
  }
}

// Mouse event handlers for selection
const onMouseDown = (e: MouseEvent) => {
  if (!containerRef.value) return
  
  const time = positionToTime(e.clientX)
  const startPos = selectionStart.value !== null ? timeToPosition(selectionStart.value) : null
  const endPos = selectionEnd.value !== null ? timeToPosition(selectionEnd.value) : null
  
  // Check if clicking on handles
  const handleThreshold = 15 // pixels
  
  if (startPos !== null && Math.abs(e.clientX - containerRef.value.getBoundingClientRect().left - startPos) < handleThreshold) {
    dragType.value = 'start'
  } else if (endPos !== null && Math.abs(e.clientX - containerRef.value.getBoundingClientRect().left - endPos) < handleThreshold) {
    dragType.value = 'end'
  } else if (hasSelection.value && time >= selectionStart.value! && time <= selectionEnd.value!) {
    dragType.value = 'region'
    dragStartX.value = e.clientX
    dragStartTime.value = selectionStart.value!
  } else {
    // Start new selection
    selectionStart.value = time
    selectionEnd.value = time
    dragType.value = 'end'
  }
  
  isDragging.value = true
  
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

const onMouseMove = (e: MouseEvent) => {
  if (!isDragging.value || !containerRef.value) return
  
  const time = positionToTime(e.clientX)
  
  if (dragType.value === 'start') {
    selectionStart.value = Math.max(0, Math.min(time, selectionEnd.value! - 0.5))
  } else if (dragType.value === 'end') {
    selectionEnd.value = Math.min(duration.value, Math.max(time, selectionStart.value! + 0.5))
  } else if (dragType.value === 'region') {
    const delta = positionToTime(e.clientX) - positionToTime(dragStartX.value)
    const selectionDur = selectionEnd.value! - selectionStart.value!
    
    let newStart = dragStartTime.value + delta
    newStart = Math.max(0, Math.min(newStart, duration.value - selectionDur))
    
    selectionStart.value = newStart
    selectionEnd.value = newStart + selectionDur
  }
}

const onMouseUp = () => {
  isDragging.value = false
  dragType.value = null
  
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
}

// Touch event handlers for mobile
const onTouchStart = (e: TouchEvent) => {
  if (e.touches.length === 1) {
    const touch = e.touches[0]
    onMouseDown({ clientX: touch.clientX } as MouseEvent)
  }
}

const onTouchMove = (e: TouchEvent) => {
  if (e.touches.length === 1 && isDragging.value) {
    e.preventDefault()
    const touch = e.touches[0]
    onMouseMove({ clientX: touch.clientX } as MouseEvent)
  }
}

const onTouchEnd = () => {
  onMouseUp()
}

// Confirm selection
const confirmSelection = () => {
  if (hasSelection.value) {
    emit('clip-selected', selectionStart.value!, selectionEnd.value!)
  }
}

// Preview selection
const previewSelection = () => {
  if (hasSelection.value && videoRef.value) {
    videoRef.value.currentTime = selectionStart.value!
    videoRef.value.play()
    isPlaying.value = true
  }
}

// Draw simple waveform visualization (placeholder - real waveform would need audio analysis)
const drawWaveform = () => {
  if (!canvasRef.value) return
  
  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  const width = canvas.width
  const height = canvas.height
  
  // Clear canvas
  ctx.fillStyle = '#394053'
  ctx.fillRect(0, 0, width, height)
  
  // Draw fake waveform (for now - actual waveform would need Web Audio API analysis)
  ctx.fillStyle = '#657392'
  const barWidth = 3
  const barGap = 2
  
  for (let i = 0; i < width; i += barWidth + barGap) {
    const barHeight = Math.random() * (height * 0.7) + height * 0.15
    const y = (height - barHeight) / 2
    ctx.fillRect(i, y, barWidth, barHeight)
  }
}

onMounted(() => {
  if (canvasRef.value && containerRef.value) {
    canvasRef.value.width = containerRef.value.clientWidth
    canvasRef.value.height = 60
    drawWaveform()
  }
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
})

// Redraw waveform on resize
watch(() => containerRef.value?.clientWidth, () => {
  if (canvasRef.value && containerRef.value) {
    canvasRef.value.width = containerRef.value.clientWidth
    drawWaveform()
  }
})
</script>

<template>
  <div class="space-y-4">
    <!-- Video Player (hidden but needed for duration/preview) -->
    <div class="relative bg-noche-900 rounded-xl overflow-hidden">
      <video
        ref="videoRef"
        :src="`/api/files/stream?path=${encodeURIComponent(videoPath)}`"
        class="w-full aspect-video"
        @loadedmetadata="onLoadedMetadata"
        @timeupdate="onTimeUpdate"
        @ended="isPlaying = false"
        preload="metadata"
      />
      
      <!-- Loading overlay -->
      <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center bg-noche-900/80">
        <div class="w-8 h-8 border-4 border-sol-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
      
      <!-- Play/Pause overlay -->
      <button
        v-if="!isLoading"
        @click="togglePlay"
        class="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/30 transition-colors"
      >
        <div class="w-16 h-16 rounded-full bg-sol-500/90 flex items-center justify-center">
          <svg v-if="!isPlaying" class="w-8 h-8 text-noche-950 ml-1" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
          <svg v-else class="w-8 h-8 text-noche-950" fill="currentColor" viewBox="0 0 24 24">
            <rect x="6" y="4" width="4" height="16" rx="1" />
            <rect x="14" y="4" width="4" height="16" rx="1" />
          </svg>
        </div>
      </button>
    </div>
    
    <!-- Timeline with Selection -->
    <div 
      ref="containerRef"
      class="relative cursor-crosshair select-none touch-none"
      @mousedown="onMouseDown"
      @touchstart="onTouchStart"
      @touchmove="onTouchMove"
      @touchend="onTouchEnd"
    >
      <!-- Waveform Canvas -->
      <canvas 
        ref="canvasRef" 
        class="w-full h-[60px] rounded-lg"
      />
      
      <!-- Selection Overlay -->
      <div
        v-if="hasSelection"
        class="absolute top-0 bottom-0 bg-sol-500/30 border-l-2 border-r-2 border-sol-500"
        :style="{
          left: `${timeToPosition(selectionStart!)}px`,
          width: `${timeToPosition(selectionEnd!) - timeToPosition(selectionStart!)}px`,
        }"
      >
        <!-- Start Handle -->
        <div 
          class="absolute left-0 top-0 bottom-0 w-3 -ml-1.5 bg-sol-500 cursor-ew-resize flex items-center justify-center"
        >
          <div class="w-0.5 h-4 bg-noche-950 rounded-full"></div>
        </div>
        
        <!-- End Handle -->
        <div 
          class="absolute right-0 top-0 bottom-0 w-3 -mr-1.5 bg-sol-500 cursor-ew-resize flex items-center justify-center"
        >
          <div class="w-0.5 h-4 bg-noche-950 rounded-full"></div>
        </div>
      </div>
      
      <!-- Playhead -->
      <div
        class="absolute top-0 bottom-0 w-0.5 bg-tierra-400 pointer-events-none"
        :style="{ left: `${timeToPosition(currentTime)}px` }"
      />
    </div>
    
    <!-- Time Display -->
    <div class="flex items-center justify-between text-sm">
      <span class="text-noche-400">{{ formatTime(currentTime) }}</span>
      <span v-if="hasSelection" class="text-sol-400 font-medium">
        Selection: {{ formatTime(selectionStart!) }} - {{ formatTime(selectionEnd!) }} 
        ({{ selectionDuration }}s)
      </span>
      <span class="text-noche-400">{{ formatTime(duration) }}</span>
    </div>
    
    <!-- Quick Time Inputs -->
    <div class="grid grid-cols-2 gap-4">
      <div class="space-y-1">
        <label class="text-xs text-noche-500">Start Time</label>
        <input
          type="text"
          :value="selectionStart !== null ? formatTime(selectionStart) : ''"
          @change="(e) => { const t = parseFloat((e.target as HTMLInputElement).value) || 0; selectionStart = t }"
          class="input text-sm py-2"
          placeholder="0:00.0"
        />
      </div>
      <div class="space-y-1">
        <label class="text-xs text-noche-500">End Time</label>
        <input
          type="text"
          :value="selectionEnd !== null ? formatTime(selectionEnd) : ''"
          @change="(e) => { const t = parseFloat((e.target as HTMLInputElement).value) || 0; selectionEnd = t }"
          class="input text-sm py-2"
          placeholder="0:10.0"
        />
      </div>
    </div>
    
    <!-- Actions -->
    <div class="flex gap-3">
      <button
        @click="previewSelection"
        :disabled="!hasSelection"
        class="btn btn-secondary flex-1"
      >
        <svg class="w-4 h-4 mr-2 inline" fill="currentColor" viewBox="0 0 24 24">
          <path d="M8 5v14l11-7z" />
        </svg>
        Preview
      </button>
      <button
        @click="confirmSelection"
        :disabled="!hasSelection"
        class="btn btn-primary flex-1"
      >
        Use This Clip
      </button>
    </div>
  </div>
</template>

