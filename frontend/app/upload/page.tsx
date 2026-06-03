"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import VideoUploader from "@/components/VideoUploader/VideoUploader"
import SettingsPanel from "@/components/SettingsPanel/SettingsPanel"
import type { JobRequest } from "@/lib/api"
import { DEFAULT_SETTINGS } from "../../../shared/types"

export default function UploadPage() {
  const router = useRouter()
  const [settings, setSettings] = useState<JobRequest>(DEFAULT_SETTINGS)

  const handleUploadSuccess = (jobId: string) => {
    router.push(`/editor/${jobId}`)
  }

  const handleError = (error: string) => {
    console.error("Upload error:", error)
    alert(error)
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 dark:from-gray-900 dark:to-gray-800 py-12">
      <div className="container mx-auto px-4 max-w-4xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            Upload Video
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Upload a video file or paste a URL to generate short clips
          </p>
        </div>

        <div className="space-y-8">
          <VideoUploader 
            onUploadSuccess={handleUploadSuccess}
            onError={handleError}
          />
          
          <SettingsPanel 
            settings={settings}
            onChange={setSettings}
          />
        </div>
      </div>
    </main>
  )
}