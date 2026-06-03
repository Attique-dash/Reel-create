"use client"

import { ReactNode } from "react"

interface AlertProps {
  type: "success" | "error" | "warning" | "info"
  message: string
  onClose?: () => void
}

export const Alert = ({ type, message, onClose }: AlertProps) => {
  const styles = {
    success: "bg-green-50 dark:bg-green-900/20 border-green-500 text-green-800 dark:text-green-200",
    error: "bg-red-50 dark:bg-red-900/20 border-red-500 text-red-800 dark:text-red-200",
    warning: "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-500 text-yellow-800 dark:text-yellow-200",
    info: "bg-blue-50 dark:bg-blue-900/20 border-blue-500 text-blue-800 dark:text-blue-200",
  }
  
  const icons = {
    success: "✓",
    error: "✗",
    warning: "⚠",
    info: "ℹ",
  }
  
  return (
    <div className={`p-4 rounded-lg border-l-4 ${styles[type]} mb-4`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xl">{icons[type]}</span>
          <span className="text-sm font-medium">{message}</span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-current opacity-50 hover:opacity-100 transition-opacity"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  )
}