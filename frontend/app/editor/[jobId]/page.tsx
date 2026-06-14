"use client"

import { useState, useEffect } from "react"
import { useParams } from "next/navigation"
import { getJobStatus, pollJobStatus, type JobStatus } from "@/lib/api"
import ClipEditor from "@/components/ClipEditor/ClipEditor"
import Link from "next/link"

export default function EditorPage() {
  const params = useParams()
  const jobId = params.jobId as string
  
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [isPolling, setIsPolling] = useState(true)

  useEffect(() => {
    if (!jobId) return

    // Initial load
    getJobStatus(jobId).then(setJobStatus).catch(console.error)

    // Start polling
    const stopPolling = pollJobStatus(jobId, (status) => {
      setJobStatus(status)
      if (status.status === "completed" || status.status === "failed") {
        setIsPolling(false)
      }
    })

    return () => {
      stopPolling()
      setIsPolling(false)
    }
  }, [jobId])

  if (!jobStatus) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (jobStatus.status === "failed") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">❌</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Processing Failed</h1>
          <p className="text-gray-600 mb-6">{jobStatus.error || "An error occurred while processing your video"}</p>
          <Link href="/upload" className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Try Again
          </Link>
        </div>
      </div>
    )
  }

  if (jobStatus.status !== "completed") {
    // Calculate estimated time remaining
    const progress = jobStatus.progress || 0
    const estimatedTimeRemaining = progress > 0 ? Math.round((100 - progress) / 10) : null // Rough estimate: 10% per minute
    
    return (
      <div className="min-h-screen flex items-center justify-center bg-black">
        <div className="text-center max-w-md">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <h1 className="text-2xl font-bold text-white mb-2">Processing Video</h1>
          <p className="text-gray-300 mb-4">Please wait while we analyze and create your clips...</p>
          <div className="w-full bg-gray-700 rounded-full h-2.5">
            <div 
              className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-sm text-gray-400 mt-2">{progress}% complete</p>
          {estimatedTimeRemaining && (
            <p className="text-sm text-gray-400 mt-1">Estimated time remaining: ~{estimatedTimeRemaining} min</p>
          )}
        </div>
      </div>
    )
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 dark:from-gray-900 dark:to-gray-800 py-12">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              Edit Your Clips
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-2">
              Review and download your AI-generated clips
            </p>
          </div>
          <Link 
            href="/dashboard" 
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            View Dashboard
          </Link>
        </div>

        <ClipEditor 
          clips={jobStatus.clips}
          jobId={jobId}
          onClipUpdate={(updatedClip) => {
            // Handle clip updates (tag editing, etc.)
            if (jobStatus) {
              const updatedClips = jobStatus.clips.map(clip => 
                clip.id === updatedClip.id ? updatedClip : clip
              )
              setJobStatus({ ...jobStatus, clips: updatedClips })
            }
          }}
        />
      </div>
    </main>
  )
}