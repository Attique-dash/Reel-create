import Link from "next/link"

export function Navigation() {
  return (
    <nav className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      <div className="container mx-auto px-4 py-4">
        <div className="flex justify-between items-center">
          <Link href="/" className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Video Processor
          </Link>
          <div className="flex gap-4">
            <Link href="/" className="text-gray-600 dark:text-gray-300 hover:text-blue-600 transition-colors">
              Home
            </Link>
            <Link href="/upload" className="text-gray-600 dark:text-gray-300 hover:text-blue-600 transition-colors">
              Upload
            </Link>
            <Link href="/dashboard" className="text-gray-600 dark:text-gray-300 hover:text-blue-600 transition-colors">
              Dashboard
            </Link>
          </div>
        </div>
      </div>
    </nav>
  )
}
