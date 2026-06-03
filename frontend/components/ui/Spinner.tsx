"use client"

interface SpinnerProps {
  size?: "sm" | "md" | "lg"
  color?: string
}

export const Spinner = ({ size = "md", color = "blue" }: SpinnerProps) => {
  const sizes = {
    sm: "w-4 h-4",
    md: "w-8 h-8",
    lg: "w-12 h-12",
  }
  
  const colors = {
    blue: "border-blue-600",
    gray: "border-gray-600",
    white: "border-white",
  }
  
  return (
    <div className="flex justify-center items-center">
      <div
        className={`
          ${sizes[size]} 
          ${colors[color as keyof typeof colors]} 
          border-2 
          border-t-transparent 
          rounded-full 
          animate-spin
        `}
      />
    </div>
  )
}