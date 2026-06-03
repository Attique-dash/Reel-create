"use client"

import { useState } from "react"
import type { JobRequest } from "@/lib/api"

interface SettingsPanelProps {
  settings: JobRequest
  onChange: (settings: JobRequest) => void
}

const FONTS = ["Arial", "Impact", "Helvetica", "Georgia", "Verdana", "Roboto"]
const COLORS = [
  { label: "White", value: "white", hex: "#ffffff" },
  { label: "Yellow", value: "yellow", hex: "#facc15" },
  { label: "Cyan", value: "cyan", hex: "#22d3ee" },
  { label: "Red", value: "red", hex: "#ef4444" },
]

export default function SettingsPanel({ settings, onChange }: SettingsPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  const update = (patch: Partial<JobRequest>) => onChange({ ...settings, ...patch })
  
  // Fix: Ensure subtitle_style always has all required properties
  const updateSubtitle = (patch: Partial<NonNullable<JobRequest["subtitle_style"]>>) => {
    const currentStyle = settings.subtitle_style || {
      font: "Arial",
      size: 24,
      color: "white",
      position: "bottom"
    }
    onChange({ 
      ...settings, 
      subtitle_style: { ...currentStyle, ...patch }
    })
  }

  // Make sure settings have default values
  const safeSettings = {
    num_clips: settings.num_clips ?? 5,
    clip_duration: settings.clip_duration ?? 30,
    aspect_ratio: settings.aspect_ratio ?? "9:16",
    subtitle_style: settings.subtitle_style ?? {
      font: "Arial",
      size: 24,
      color: "white",
      position: "bottom"
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
            </svg>
          </div>
          <span className="font-semibold text-gray-900 dark:text-gray-100">Processing Settings</span>
        </div>
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-6 pb-6 space-y-6 border-t border-gray-100 dark:border-gray-700 pt-5">
          {/* Clips & Duration */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                Number of Clips
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={1}
                  max={20}
                  value={safeSettings.num_clips}
                  onChange={(e) => update({ num_clips: Number(e.target.value) })}
                  className="flex-1 accent-blue-600"
                />
                <span className="w-8 text-center text-sm font-bold text-blue-600">{safeSettings.num_clips}</span>
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                Clip Duration (s)
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={15}
                  max={180}
                  step={15}
                  value={safeSettings.clip_duration}
                  onChange={(e) => update({ clip_duration: Number(e.target.value) })}
                  className="flex-1 accent-blue-600"
                />
                <span className="w-10 text-center text-sm font-bold text-blue-600">{safeSettings.clip_duration}s</span>
              </div>
            </div>
          </div>

          {/* Aspect Ratio */}
          <div>
            <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
              Aspect Ratio
            </label>
            <div className="flex gap-3">
              {(["9:16", "1:1", "16:9"] as const).map((ratio) => (
                <button
                  key={ratio}
                  onClick={() => update({ aspect_ratio: ratio })}
                  className={`flex-1 py-3 rounded-xl border-2 text-sm font-semibold transition-all ${
                    safeSettings.aspect_ratio === ratio
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-600"
                      : "border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-gray-300"
                  }`}
                >
                  <div className="flex flex-col items-center gap-1">
                    <div
                      className={`border-2 rounded ${safeSettings.aspect_ratio === ratio ? "border-blue-500" : "border-current"}`}
                      style={{
                        width: ratio === "9:16" ? 12 : ratio === "1:1" ? 20 : 32,
                        height: ratio === "9:16" ? 21 : ratio === "1:1" ? 20 : 18,
                      }}
                    />
                    <span>{ratio}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Subtitle Style */}
          <div>
            <label className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
              Subtitle Style
            </label>
            <div className="space-y-3">
              {/* Font */}
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600 dark:text-gray-400 w-16">Font</span>
                <select
                  value={safeSettings.subtitle_style.font}
                  onChange={(e) => updateSubtitle({ font: e.target.value })}
                  className="flex-1 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {FONTS.map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>

              {/* Size */}
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600 dark:text-gray-400 w-16">Size</span>
                <input
                  type="range"
                  min={14}
                  max={48}
                  value={safeSettings.subtitle_style.size}
                  onChange={(e) => updateSubtitle({ size: Number(e.target.value) })}
                  className="flex-1 accent-purple-600"
                />
                <span className="w-8 text-right text-sm font-bold text-purple-600">{safeSettings.subtitle_style.size}px</span>
              </div>

              {/* Color */}
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600 dark:text-gray-400 w-16">Color</span>
                <div className="flex gap-2">
                  {COLORS.map((c) => (
                    <button
                      key={c.value}
                      onClick={() => updateSubtitle({ color: c.value })}
                      title={c.label}
                      className={`w-8 h-8 rounded-full border-2 transition-transform hover:scale-110 ${
                        safeSettings.subtitle_style.color === c.value ? "border-blue-500 scale-110" : "border-gray-300 dark:border-gray-600"
                      }`}
                      style={{ backgroundColor: c.hex }}
                    />
                  ))}
                </div>
              </div>

              {/* Position */}
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600 dark:text-gray-400 w-16">Position</span>
                <div className="flex gap-2">
                  {(["top", "center", "bottom"] as const).map((pos) => (
                    <button
                      key={pos}
                      onClick={() => updateSubtitle({ position: pos })}
                      className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-colors capitalize ${
                        safeSettings.subtitle_style.position === pos
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
                      }`}
                    >
                      {pos}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Preview Badge */}
          <div className="bg-gray-50 dark:bg-gray-900 rounded-xl p-4">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 font-medium">Subtitle Preview</p>
            <div className="h-16 bg-gray-800 rounded-lg relative flex items-center justify-center overflow-hidden">
              <div
                className={`px-3 py-1 rounded bg-black/60 absolute ${
                  safeSettings.subtitle_style.position === "top" ? "top-2" :
                  safeSettings.subtitle_style.position === "center" ? "top-1/2 -translate-y-1/2" :
                  "bottom-2"
                }`}
              >
                <span
                  style={{
                    fontFamily: safeSettings.subtitle_style.font,
                    fontSize: Math.min(safeSettings.subtitle_style.size * 0.5, 16),
                    color: safeSettings.subtitle_style.color,
                  }}
                >
                  Sample subtitle text
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}