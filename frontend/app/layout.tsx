import "./globals.css"
import { Navigation } from "@/components/Navigation/Navigation"

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>
        <Navigation />
        {children}
      </body>
    </html>
  )
}