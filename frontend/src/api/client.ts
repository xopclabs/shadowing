const API_BASE = '/api'

interface RecordingResponse {
  id: string
  filename: string
  created_at: string
  clip_id?: number
}

interface RecordingListResponse {
  recordings: RecordingResponse[]
}

interface ClipResponse {
  id: number
  audioUrl: string
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl
  }

  private async fetch<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`API error: ${response.status} - ${error}`)
    }

    return response.json()
  }

  // Recordings API
  async uploadRecording(
    audioBlob: Blob,
    clipId?: number
  ): Promise<RecordingResponse> {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.webm')
    if (clipId !== undefined) {
      formData.append('clip_id', clipId.toString())
    }

    return this.fetch<RecordingResponse>('/recordings/upload', {
      method: 'POST',
      body: formData,
    })
  }

  async listRecordings(): Promise<RecordingListResponse> {
    return this.fetch<RecordingListResponse>('/recordings')
  }

  getRecordingUrl(filename: string): string {
    return `${this.baseUrl}/recordings/${filename}`
  }

  async deleteRecording(filename: string): Promise<void> {
    await this.fetch(`/recordings/${filename}`, {
      method: 'DELETE',
    })
  }

  // Clips API
  async extractClip(
    videoPath: string,
    startTime: number,
    endTime: number
  ): Promise<ClipResponse> {
    const response = await this.fetch<{ 
      id: number
      audio_path: string 
    }>('/clips/extract', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        video_path: videoPath,
        start_time: startTime,
        end_time: endTime,
      }),
    })

    return {
      id: response.id,
      audioUrl: `${this.baseUrl}/clips/${response.id}/audio`,
    }
  }

  getClipAudioUrl(clipId: number): string {
    return `${this.baseUrl}/clips/${clipId}/audio`
  }
}

export const api = new ApiClient()

