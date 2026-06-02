import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "Video Processor - AI-Powered Short Content Creator",
  description: "Transform long videos into engaging short clips using AI",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
