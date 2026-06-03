"use client"

import { useState } from "react"
import type { Clip } from "@/lib/api"
import { downloadClip, downloadAllClips } from "@/lib/api"

interface OutputPreviewProps {
  clips: Clip[]
  jobId: string
  onClose?: () => void
}

export default function OutputPreview({ clips, jobId, onClose }: OutputPreviewProps) {
  const [selectedClip, setSelectedClip] = useState<Clip | null>(clips[0] || null)
  const [isDownloading, setIsDownloading] = useState(false)

  const handleDownloadClip = async (clipId: string) => {
    setIsDownloading(true)
    try {
      const link = document.createElement('a')
      link.href = downloadClip(clipId)
      link.download = `${clipId}.mp4`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } finally {
      setIsDownloading(false)
    }
  }

  const handleDownloadAll = async () => {
    setIsDownloading(true)
    try {
      window.open(downloadAllClips(jobId), '_blank')
    } finally {
      setIsDownloading(false)
    }
  }

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Output Preview
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {clips.length} clips generated
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleDownloadAll}
              disabled={isDownloading}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download All
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Clip List */}
          <div className="w-80 border-r border-gray-200 dark:border-gray-700 overflow-y-auto p-4 space-y-3">
            {clips.map((clip, index) => (
              <button
                key={clip.id}
                onClick={() => setSelectedClip(clip)}
                className={`w-full text-left p-3 rounded-xl transition-all ${
                  selectedClip?.id === clip.id
                    ? "bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-500"
                    : "bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 border-2 border-transparent"
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <span className="font-semibold text-gray-900 dark:text-gray-100">
                    Clip {index + 1}
                  </span>
                  <span className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-full">
                    {Math.round(clip.engagement_score * 100)}%
                  </span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {formatTime(clip.start_time)} → {formatTime(clip.end_time)}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                  Duration: {formatTime(clip.duration)}
                </p>
                {clip.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {clip.tags.slice(0, 2).map(tag => (
                      <span key={tag} className="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded-full">
                        #{tag}
                      </span>
                    ))}
                    {clip.tags.length > 2 && (
                      <span className="text-xs text-gray-500">+{clip.tags.length - 2}</span>
                    )}
                  </div>
                )}
              </button>
            ))}
          </div>

          {/* Video Preview */}
          <div className="flex-1 p-6 overflow-y-auto">
            {selectedClip ? (
              <div className="space-y-6">
                {/* Video Player */}
                <div className="bg-black rounded-xl overflow-hidden aspect-[9/16] max-h-[60vh] mx-auto">
                  {selectedClip.video_path ? (
                    <video
                      src={`/api/preview/${selectedClip.id}`}
                      controls
                      autoPlay
                      className="w-full h-full object-contain"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <div className="text-center">
                        <svg className="w-16 h-16 text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        <p className="text-gray-400">Preview not available</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Clip Details */}
                <div className="bg-gray-50 dark:bg-gray-900 rounded-xl p-4 space-y-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                        Clip Details
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        Segment: {formatTime(selectedClip.start_time)} - {formatTime(selectedClip.end_time)}
                      </p>
                    </div>
                    <button
                      onClick={() => handleDownloadClip(selectedClip.id)}
                      disabled={isDownloading}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      Download Clip
                    </button>
                  </div>

                  {/* Engagement Score */}
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600 dark:text-gray-400">Engagement Score</span>
                      <span className="font-semibold text-blue-600">
                        {Math.round(selectedClip.engagement_score * 100)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all"
                        style={{ width: `${selectedClip.engagement_score * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Tags */}
                  {selectedClip.tags.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Tags
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {selectedClip.tags.map(tag => (
                          <span
                            key={tag}
                            className="px-3 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full text-sm"
                          >
                            #{tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center">
                <div className="text-center">
                  <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <p className="text-gray-500 dark:text-gray-400">Select a clip to preview</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}