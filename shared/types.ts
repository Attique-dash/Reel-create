// Shared types between frontend and backend

export type AspectRatio = "9:16" | "1:1" | "16:9"
export type JobStatusType = "pending" | "processing" | "completed" | "failed"

export interface SubtitleStyle {
  font: string
  size: number
  color: string
  position: "top" | "center" | "bottom"
}

export interface Clip {
  id: string
  start_time: number
  end_time: number
  duration: number
  subtitle_path?: string
  video_path?: string
  tags: string[]
  engagement_score: number
}

export interface JobRequest {
  url?: string
  num_clips: number
  clip_duration: number
  aspect_ratio: AspectRatio
  subtitle_style: SubtitleStyle
}

export interface Job {
  job_id: string
  status: JobStatusType
  progress: number
  video_path?: string
  clips: Clip[]
  created_at: string
  updated_at: string
  error?: string
  settings: JobRequest
}

export interface UploadResponse {
  job_id: string
  status: string
  message: string
}

export interface ApiError {
  detail: string
}

export const DEFAULT_SETTINGS: JobRequest = {
  num_clips: 5,
  clip_duration: 60,
  aspect_ratio: "9:16",
  subtitle_style: {
    font: "Arial",
    size: 24,
    color: "white",
    position: "bottom",
  },
}