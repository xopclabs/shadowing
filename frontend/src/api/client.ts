const API_BASE = "/api";

interface RecordingResponse {
  id: string;
  filename: string;
  created_at: string;
  clip_id?: number;
}

interface RecordingListResponse {
  recordings: RecordingResponse[];
}

interface ClipResponse {
  id: number;
  audioUrl: string;
}

export interface RecentFile {
  id: number;
  video_path: string;
  filename: string;
  last_timestamp: number;
  last_used: string;
  source: "youtube" | "media";
  thumbnail_url: string | null;
}

interface RecentFilesResponse {
  recent_files: RecentFile[];
}

export interface Stats {
  total_recordings: number;
  total_clips_practiced: number;
  total_practice_minutes: number;
  recordings_this_week: number;
  first_recording_date?: string;
  last_recording_date?: string;
}

export interface StorageInfo {
  clips_count: number;
  clips_size_bytes: number;
  recordings_count: number;
  recordings_size_bytes: number;
  total_size_bytes: number;
}

export interface ServerSettings {
  socks5_proxy: string | null;
  youtube_download_dir: string | null;
}

export interface YouTubeVideoInfo {
  id: string;
  title: string;
  duration: number | null;
  thumbnail: string | null;
  uploader: string | null;
  description: string | null;
}

export interface YouTubeDownloadResult {
  success: boolean;
  video_id: string;
  title: string;
  file_path: string | null;
  error: string | null;
}

export interface YouTubeDownloadRecord {
  id: number;
  video_id: string;
  title: string;
  file_path: string;
  thumbnail_url: string | null;
  duration: number | null;
  uploader: string | null;
  is_audio_only: boolean;
  created_at: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`API error: ${response.status} - ${error}`);
    }

    return response.json();
  }

  // Recordings API
  async uploadRecording(
    audioBlob: Blob,
    clipId?: number,
  ): Promise<RecordingResponse> {
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.webm");
    if (clipId !== undefined) {
      formData.append("clip_id", clipId.toString());
    }

    return this.fetch<RecordingResponse>("/recordings/upload", {
      method: "POST",
      body: formData,
    });
  }

  async listRecordings(): Promise<RecordingListResponse> {
    return this.fetch<RecordingListResponse>("/recordings");
  }

  getRecordingUrl(filename: string): string {
    return `${this.baseUrl}/recordings/${filename}`;
  }

  async deleteRecording(filename: string): Promise<void> {
    await this.fetch(`/recordings/${filename}`, {
      method: "DELETE",
    });
  }

  // Clips API
  async extractClip(
    videoPath: string,
    startTime: number,
    endTime: number,
  ): Promise<ClipResponse> {
    const response = await this.fetch<{
      id: number;
      audio_path: string;
    }>("/clips/extract", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        video_path: videoPath,
        start_time: startTime,
        end_time: endTime,
      }),
    });

    return {
      id: response.id,
      audioUrl: `${this.baseUrl}/clips/${response.id}/audio`,
    };
  }

  getClipAudioUrl(clipId: number): string {
    return `${this.baseUrl}/clips/${clipId}/audio`;
  }

  getThumbnailUrl(videoPath: string, timestamp: number = 0): string {
    return `${this.baseUrl}/files/thumbnail?path=${encodeURIComponent(videoPath)}&timestamp=${timestamp}`;
  }

  // Recent Files API
  async listRecentFiles(source?: "youtube" | "media"): Promise<RecentFile[]> {
    const params = source ? `?source=${source}` : "";
    const response = await this.fetch<RecentFilesResponse>(
      `/recent-files${params}`,
    );
    return response.recent_files;
  }

  async addRecentFile(
    videoPath: string,
    lastTimestamp: number,
    source: "youtube" | "media" = "media",
    thumbnailUrl?: string,
  ): Promise<void> {
    await this.fetch("/recent-files", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        video_path: videoPath,
        last_timestamp: lastTimestamp,
        source,
        thumbnail_url: thumbnailUrl,
      }),
    });
  }

  async deleteRecentFile(fileId: number): Promise<void> {
    await this.fetch(`/recent-files/${fileId}`, {
      method: "DELETE",
    });
  }

  // Stats API
  async getStats(): Promise<Stats> {
    return this.fetch<Stats>("/stats");
  }

  // Storage API
  async getStorageInfo(): Promise<StorageInfo> {
    return this.fetch<StorageInfo>("/storage");
  }

  async deleteFiles(
    deleteClips: boolean,
    deleteRecordings: boolean,
  ): Promise<{
    deleted_clips: number;
    deleted_recordings: number;
    freed_bytes: number;
  }> {
    return this.fetch("/storage/delete-files", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        delete_clips: deleteClips,
        delete_recordings: deleteRecordings,
      }),
    });
  }

  async clearDatabase(): Promise<void> {
    await this.fetch("/database/clear", {
      method: "POST",
    });
  }

  // Server Settings API
  async getServerSettings(): Promise<ServerSettings> {
    return this.fetch<ServerSettings>("/settings");
  }

  async updateServerSettings(
    settings: Partial<ServerSettings>,
  ): Promise<ServerSettings> {
    return this.fetch<ServerSettings>("/settings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(settings),
    });
  }

  // YouTube API
  async getYouTubeVideoInfo(url: string): Promise<YouTubeVideoInfo> {
    return this.fetch<YouTubeVideoInfo>("/youtube/info", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url }),
    });
  }

  async downloadYouTubeVideo(
    url: string,
    audioOnly: boolean = false,
  ): Promise<YouTubeDownloadResult> {
    return this.fetch<YouTubeDownloadResult>("/youtube/download", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url, audio_only: audioOnly }),
    });
  }

  async listYouTubeDownloads(): Promise<YouTubeDownloadRecord[]> {
    const response = await this.fetch<{ downloads: YouTubeDownloadRecord[] }>(
      "/youtube/downloads",
    );
    return response.downloads;
  }

  async deleteYouTubeDownload(
    downloadId: number,
    deleteFile: boolean = false,
  ): Promise<void> {
    await this.fetch(
      `/youtube/downloads/${downloadId}?delete_file=${deleteFile}`,
      {
        method: "DELETE",
      },
    );
  }
}

export const api = new ApiClient();
