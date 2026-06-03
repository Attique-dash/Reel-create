"use client"

import { useState, useCallback, useRef } from "react"
import { uploadVideo, uploadVideoUrl, type UploadResponse } from "@/lib/api"

interface VideoUploaderProps {
  onUploadSuccess: (jobId: string) => void
  onError?: (error: string) => void
}

export default function VideoUploader({ onUploadSuccess, onError }: VideoUploaderProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [uploadMode, setUploadMode] = useState<"file" | "url">("file")
  const [url, setUrl] = useState("")
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) await handleFileUpload(file)
  }, [])

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) await handleFileUpload(file)
  }, [])

  const handleFileUpload = async (file: File) => {
    const validTypes = ["video/mp4", "video/mov", "video/avi", "video/quicktime", "video/x-msvideo"]
    if (!validTypes.includes(file.type)) {
      onError?.("Please upload a valid video file (MP4, MOV, AVI)")
      return
    }
    if (file.size > 500 * 1024 * 1024) {
      onError?.("File size must be under 500MB")
      return
    }

    setIsUploading(true)
    setUploadProgress(0)

    // Simulate progress
    const progressInterval = setInterval(() => {
      setUploadProgress((p) => Math.min(p + 10, 90))
    }, 300)

    try {
      const response: UploadResponse = await uploadVideo(file)
      clearInterval(progressInterval)
      setUploadProgress(100)
      setTimeout(() => {
        setIsUploading(false)
        onUploadSuccess(response.job_id)
      }, 500)
    } catch (err: any) {
      clearInterval(progressInterval)
      setIsUploading(false)
      setUploadProgress(0)
      onError?.(err?.response?.data?.detail || "Upload failed. Please try again.")
    }
  }

  const handleUrlSubmit = async () => {
    if (!url.trim()) {
      onError?.("Please enter a valid URL")
      return
    }
    const urlPattern = /^https?:\/\/.+/
    if (!urlPattern.test(url)) {
      onError?.("Please enter a valid URL starting with http:// or https://")
      return
    }

    setIsUploading(true)
    try {
      const response = await uploadVideoUrl({ url })
      setIsUploading(false)
      onUploadSuccess(response.job_id)
    } catch (err: any) {
      setIsUploading(false)
      onError?.(err?.response?.data?.detail || "Failed to process URL. Please try again.")
    }
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Mode Toggle */}
      <div className="flex rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 mb-6">
        <button
          onClick={() => setUploadMode("file")}
          className={`flex-1 py-3 text-sm font-semibold transition-colors ${
            uploadMode === "file"
              ? "bg-blue-600 text-white"
              : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
          }`}
        >
          📁 Upload File
        </button>
        <button
          onClick={() => setUploadMode("url")}
          className={`flex-1 py-3 text-sm font-semibold transition-colors ${
            uploadMode === "url"
              ? "bg-blue-600 text-white"
              : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
          }`}
        >
          🔗 Paste URL
        </button>
      </div>

      {uploadMode === "file" ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !isUploading && fileInputRef.current?.click()}
          className={`
            relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all
            ${isDragging ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 scale-[1.02]" : "border-gray-300 dark:border-gray-600 hover:border-blue-400 hover:bg-gray-50 dark:hover:bg-gray-800/50"}
            ${isUploading ? "pointer-events-none opacity-80" : ""}
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            onChange={handleFileSelect}
            className="hidden"
          />

          {isUploading ? (
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center animate-pulse">
                <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Uploading...</p>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                <div
                  className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-xs text-gray-500">{uploadProgress}%</p>
            </div>
          ) : (
            <>
              <div className="w-16 h-16 mx-auto rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center mb-4">
                <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <p className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Drop your video here
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
                or <span className="text-blue-600 font-medium">browse files</span>
              </p>
              <p className="text-xs text-gray-400">MP4, MOV, AVI up to 500MB</p>
            </>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl p-6 space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Video URL
              </label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleUrlSubmit()}
                placeholder="https://youtube.com/watch?v=..."
                className="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                disabled={isUploading}
              />
            </div>
            <div className="flex gap-2 flex-wrap">
              {["YouTube", "Vimeo", "Instagram", "TikTok"].map((platform) => (
                <span key={platform} className="px-3 py-1 bg-gray-100 dark:bg-gray-700 rounded-full text-xs text-gray-600 dark:text-gray-400 font-medium">
                  ✓ {platform}
                </span>
              ))}
            </div>
            <button
              onClick={handleUrlSubmit}
              disabled={isUploading || !url.trim()}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 text-white rounded-xl font-semibold transition-colors text-sm"
            >
              {isUploading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Processing...
                </span>
              ) : "Process Video"}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}