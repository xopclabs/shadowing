<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'

const props = defineProps<{
  audioUrl: string
  label?: string
}>()

// Canvas refs
const canvasRef = ref<HTMLCanvasElement | null>(null)

// State
const isAnalyzing = ref(false)
const error = ref<string | null>(null)
const spectrogramData = ref<ImageData | null>(null)

// Audio context and analyser
let audioContext: AudioContext | null = null
let analyserNode: AnalyserNode | null = null

// Configuration
const FFT_SIZE = 2048
const SMOOTHING = 0.8

// Color map for spectrogram (dark theme friendly)
const getColorForValue = (value: number): [number, number, number] => {
  // Normalize value (0-255)
  const normalized = value / 255
  
  // Color gradient: dark blue -> cyan -> yellow -> red
  if (normalized < 0.2) {
    // Dark blue to blue
    const t = normalized / 0.2
    return [
      Math.floor(30 * t),
      Math.floor(30 + 70 * t),
      Math.floor(50 + 100 * t)
    ]
  } else if (normalized < 0.4) {
    // Blue to cyan
    const t = (normalized - 0.2) / 0.2
    return [
      Math.floor(30),
      Math.floor(100 + 155 * t),
      Math.floor(150 + 50 * t)
    ]
  } else if (normalized < 0.6) {
    // Cyan to yellow
    const t = (normalized - 0.4) / 0.2
    return [
      Math.floor(30 + 195 * t),
      Math.floor(255),
      Math.floor(200 - 200 * t)
    ]
  } else if (normalized < 0.8) {
    // Yellow to orange
    const t = (normalized - 0.6) / 0.2
    return [
      Math.floor(225 + 30 * t),
      Math.floor(255 - 100 * t),
      Math.floor(0)
    ]
  } else {
    // Orange to red
    const t = (normalized - 0.8) / 0.2
    return [
      Math.floor(255),
      Math.floor(155 - 100 * t),
      Math.floor(0)
    ]
  }
}

// Generate spectrogram from audio URL
const generateSpectrogram = async () => {
  if (!canvasRef.value) return
  
  isAnalyzing.value = true
  error.value = null
  
  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  try {
    // Fetch audio file
    const response = await fetch(props.audioUrl)
    if (!response.ok) throw new Error('Failed to load audio')
    
    const arrayBuffer = await response.arrayBuffer()
    
    // Create audio context
    audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
    
    // Decode audio
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
    
    // Create offline context for analysis
    const offlineContext = new OfflineAudioContext(
      audioBuffer.numberOfChannels,
      audioBuffer.length,
      audioBuffer.sampleRate
    )
    
    // Create analyser
    analyserNode = offlineContext.createAnalyser()
    analyserNode.fftSize = FFT_SIZE
    analyserNode.smoothingTimeConstant = SMOOTHING
    
    const frequencyBinCount = analyserNode.frequencyBinCount
    const frequencyData = new Uint8Array(frequencyBinCount)
    
    // Create source
    const source = offlineContext.createBufferSource()
    source.buffer = audioBuffer
    source.connect(analyserNode)
    analyserNode.connect(offlineContext.destination)
    
    // Calculate dimensions
    const duration = audioBuffer.duration
    const sampleRate = audioBuffer.sampleRate
    const samplesPerColumn = Math.floor(sampleRate / 60) // ~60 columns per second
    const numColumns = Math.ceil(audioBuffer.length / samplesPerColumn)
    
    canvas.width = Math.min(numColumns, 800) // Cap width
    canvas.height = Math.min(frequencyBinCount / 2, 200) // Use lower half of spectrum
    
    // Create image data
    const imageData = ctx.createImageData(canvas.width, canvas.height)
    
    // Analyze audio in chunks using the raw audio data
    const channelData = audioBuffer.getChannelData(0)
    
    for (let col = 0; col < canvas.width; col++) {
      // Get the audio chunk for this column
      const startSample = Math.floor((col / canvas.width) * audioBuffer.length)
      const endSample = Math.min(startSample + FFT_SIZE, audioBuffer.length)
      
      // Simple FFT approximation using the audio samples
      // (Real FFT would be more accurate but this gives a visual approximation)
      const chunkSize = Math.min(FFT_SIZE, endSample - startSample)
      const frequencies = new Float32Array(canvas.height)
      
      // Calculate frequency magnitudes (simplified)
      for (let freq = 0; freq < canvas.height; freq++) {
        let magnitude = 0
        const freqRatio = freq / canvas.height
        
        for (let i = 0; i < chunkSize; i++) {
          const sample = channelData[startSample + i] || 0
          magnitude += Math.abs(sample) * Math.sin(2 * Math.PI * freqRatio * i / chunkSize)
        }
        
        frequencies[freq] = Math.min(255, Math.abs(magnitude) * 50)
      }
      
      // Draw column (bottom to top for frequency)
      for (let row = 0; row < canvas.height; row++) {
        const freqIndex = canvas.height - 1 - row
        const value = frequencies[freqIndex]
        const [r, g, b] = getColorForValue(value)
        
        const pixelIndex = (row * canvas.width + col) * 4
        imageData.data[pixelIndex] = r
        imageData.data[pixelIndex + 1] = g
        imageData.data[pixelIndex + 2] = b
        imageData.data[pixelIndex + 3] = 255
      }
    }
    
    spectrogramData.value = imageData
    ctx.putImageData(imageData, 0, 0)
    
  } catch (e) {
    console.error('Spectrogram generation failed:', e)
    error.value = 'Failed to generate spectrogram'
    
    // Draw placeholder
    const width = canvas.width || 300
    const height = canvas.height || 100
    canvas.width = width
    canvas.height = height
    ctx.fillStyle = '#394053'
    ctx.fillRect(0, 0, width, height)
    ctx.fillStyle = '#657392'
    ctx.textAlign = 'center'
    ctx.fillText('Spectrogram unavailable', width / 2, height / 2)
  } finally {
    isAnalyzing.value = false
    
    // Cleanup
    if (audioContext && audioContext.state !== 'closed') {
      audioContext.close()
    }
  }
}

// Watch for URL changes
watch(() => props.audioUrl, () => {
  if (props.audioUrl) {
    generateSpectrogram()
  }
}, { immediate: true })

onUnmounted(() => {
  if (audioContext && audioContext.state !== 'closed') {
    audioContext.close()
  }
})
</script>

<template>
  <div class="space-y-2">
    <div v-if="label" class="text-sm text-noche-400">{{ label }}</div>
    
    <!-- Loading State -->
    <div v-if="isAnalyzing" class="flex items-center justify-center h-24 bg-noche-800 rounded-lg">
      <div class="flex items-center gap-2 text-noche-400">
        <div class="w-4 h-4 border-2 border-sol-500 border-t-transparent rounded-full animate-spin"></div>
        <span class="text-sm">Analyzing...</span>
      </div>
    </div>
    
    <!-- Spectrogram Canvas -->
    <canvas
      v-show="!isAnalyzing"
      ref="canvasRef"
      class="w-full h-24 rounded-lg bg-noche-800"
    />
    
    <!-- Error State -->
    <div v-if="error" class="text-xs text-tierra-400 text-center">
      {{ error }}
    </div>
    
    <!-- Frequency Labels -->
    <div class="flex justify-between text-xs text-noche-500">
      <span>Low freq</span>
      <span>High freq</span>
    </div>
  </div>
</template>

