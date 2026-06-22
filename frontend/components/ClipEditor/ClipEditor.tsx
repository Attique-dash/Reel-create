"use client"

import { useState } from "react"
import type { Clip } from "@/lib/api"
import { downloadClip, previewClip } from "@/lib/api"

interface ClipEditorProps {
  clips: Clip[]
  jobId: string
  onClipUpdate?: (clip: Clip) => void
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, "0")}`
}

function EngagementBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color =
    pct >= 75 ? "bg-green-500" :
    pct >= 50 ? "bg-yellow-500" :
    "bg-red-400"
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-semibold text-gray-500 w-8">{pct}%</span>
    </div>
  )
}

export default function ClipEditor({ clips, jobId, onClipUpdate }: ClipEditorProps) {
  const [selectedClip, setSelectedClip] = useState<string | null>(clips[0]?.id || null)
  const [editingTags, setEditingTags] = useState<string | null>(null)
  const [newTag, setNewTag] = useState("")

  const selected = clips.find((c) => c.id === selectedClip)

  const handleAddTag = (clipId: string, currentTags: string[]) => {
    if (!newTag.trim()) return
    onClipUpdate?.({ ...clips.find((c) => c.id === clipId)!, tags: [...currentTags, newTag.trim()] })
    setNewTag("")
  }

  const handleRemoveTag = (clip: Clip, tag: string) => {
    onClipUpdate?.({ ...clip, tags: clip.tags.filter((t) => t !== tag) })
  }

  if (clips.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
        <p className="text-sm">No clips generated yet</p>
      </div>
    )
  }

  return (
    <div className="flex gap-4 h-full min-h-[500px]">
      {/* Clip List */}
      <div className="w-64 flex-shrink-0 space-y-2 overflow-y-auto">
        {clips.map((clip, i) => (
          <button
            key={clip.id}
            onClick={() => setSelectedClip(clip.id)}
            className={`w-full text-left rounded-xl p-3 border-2 transition-all ${
              selectedClip === clip.id
                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                : "border-transparent bg-white dark:bg-gray-800 hover:border-gray-200 dark:hover:border-gray-600"
            }`}
          >
            {/* Thumbnail placeholder */}
            <div className="aspect-[9/16] bg-gray-900 rounded-lg mb-2 flex items-center justify-center relative overflow-hidden">
              <div className="text-2xl">🎬</div>
              <div className="absolute bottom-1 right-1 bg-black/70 text-white text-xs px-1 rounded">
                {formatTime(clip.duration)}
              </div>
              <div className="absolute top-1 left-1 bg-blue-600 text-white text-xs px-1.5 py-0.5 rounded-full font-bold">
                #{i + 1}
              </div>
            </div>
            <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 truncate">
              {formatTime(clip.start_time)} → {formatTime(clip.end_time)}
            </p>
            <EngagementBar score={clip.engagement_score} />
          </button>
        ))}
      </div>

      {/* Clip Detail */}
      {selected && (
        <div className="flex-1 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6 space-y-5">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-bold text-gray-900 dark:text-gray-100 text-lg">
                Clip {clips.findIndex((c) => c.id === selected.id) + 1}
              </h3>
              <p className="text-sm text-gray-500">
                {formatTime(selected.start_time)} – {formatTime(selected.end_time)} · {formatTime(selected.duration)}
              </p>
            </div>
            <a
              href={downloadClip(selected.id)}
              download={`${selected.id}.mp4`}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download
            </a>
          </div>

          {/* Video Preview */}
          <div className="aspect-[9/16] max-h-80 bg-gray-900 rounded-xl flex items-center justify-center mx-auto overflow-hidden">
            {selected.video_path ? (
              <video
                src={previewClip(selected.id)}
                controls
                className="h-full w-auto"
              />
            ) : (
              <div className="text-center text-gray-500">
                <div className="text-4xl mb-2">🎬</div>
                <p className="text-xs">Preview unavailable</p>
              </div>
            )}
          </div>

          {/* Engagement */}
          <div className="bg-gray-50 dark:bg-gray-900 rounded-xl p-4 space-y-1">
            <div className="flex justify-between text-sm">
              <span className="font-medium text-gray-700 dark:text-gray-300">Engagement Score</span>
              <span className="font-bold text-blue-600">{Math.round(selected.engagement_score * 100)}%</span>
            </div>
            <EngagementBar score={selected.engagement_score} />
          </div>

          {/* Tags */}
          <div>
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Tags</p>
            <div className="flex flex-wrap gap-2 mb-3">
              {selected.tags.map((tag) => (
                <span
                  key={tag}
                  className="flex items-center gap-1 px-3 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full text-xs font-medium"
                >
                  #{tag}
                  <button
                    onClick={() => handleRemoveTag(selected, tag)}
                    className="hover:text-red-500 transition-colors ml-0.5"
                  >
                    ×
                  </button>
                </span>
              ))}
              {selected.tags.length === 0 && (
                <span className="text-xs text-gray-400 italic">No tags yet</span>
              )}
            </div>
            {editingTags === selected.id ? (
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleAddTag(selected.id, selected.tags)
                    if (e.key === "Escape") setEditingTags(null)
                  }}
                  placeholder="Add tag..."
                  autoFocus
                  className="flex-1 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={() => handleAddTag(selected.id, selected.tags)}
                  className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
                >
                  Add
                </button>
                <button
                  onClick={() => setEditingTags(null)}
                  className="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-lg text-sm font-medium"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setEditingTags(selected.id)}
                className="text-xs text-blue-600 hover:text-blue-700 font-medium"
              >
                + Add tag
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}