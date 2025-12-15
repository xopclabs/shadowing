import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/client'

export interface ClipInfo {
  videoPath: string
  startTime: number
  endTime: number
  audioUrl?: string
  id?: number
}

export interface Recording {
  id: string
  filename: string
  url: string
  createdAt: string
}

export const useSessionStore = defineStore('session', () => {
  // State
  const currentClip = ref<ClipInfo | null>(null)
  const recordings = ref<Recording[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const lastRecording = computed(() => 
    recordings.value.length > 0 
      ? recordings.value[recordings.value.length - 1] 
      : null
  )

  const attemptCount = computed(() => recordings.value.length)

  // Actions
  const startSession = async (clipInfo: { 
    videoPath: string
    startTime: number
    endTime: number 
  }) => {
    isLoading.value = true
    error.value = null
    recordings.value = []

    try {
      // Extract audio from video
      const clip = await api.extractClip(
        clipInfo.videoPath,
        clipInfo.startTime,
        clipInfo.endTime
      )

      currentClip.value = {
        ...clipInfo,
        audioUrl: clip.audioUrl,
        id: clip.id,
      }
    } catch (e) {
      error.value = 'Failed to extract audio clip'
      console.error(e)
      throw e
    } finally {
      isLoading.value = false
    }
  }

  const saveRecording = async (audioBlob: Blob) => {
    isLoading.value = true
    error.value = null

    try {
      const result = await api.uploadRecording(audioBlob, currentClip.value?.id)
      
      const recording: Recording = {
        id: result.id,
        filename: result.filename,
        url: api.getRecordingUrl(result.filename),
        createdAt: result.created_at,
      }

      recordings.value.push(recording)
      return recording
    } catch (e) {
      error.value = 'Failed to save recording'
      console.error(e)
      throw e
    } finally {
      isLoading.value = false
    }
  }

  const endSession = () => {
    currentClip.value = null
    recordings.value = []
    error.value = null
  }

  return {
    // State
    currentClip,
    recordings,
    isLoading,
    error,
    // Getters
    lastRecording,
    attemptCount,
    // Actions
    startSession,
    saveRecording,
    endSession,
  }
})

