import DataManagement from "@/components/data-management"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Database } from "lucide-react"
import Link from "next/link"

export default function DataManagementPage() {
  return (
    <div className="min-h-screen bg-black text-white">
      <div className="container mx-auto p-6 space-y-6">
        {/* Header with Back Button */}
        <div className="flex flex-col space-y-6 md:flex-row md:items-center md:justify-between md:space-y-0">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <Link href="/">
                <Button
                  variant="outline"
                  size="sm"
                  className="border-gray-600 bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white"
                >
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to Dashboard
                </Button>
              </Link>
            </div>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-900/30 rounded-lg border border-purple-700/50">
                <Database className="h-6 w-6 text-purple-400" />
              </div>
              <div>
                <h1 className="text-3xl font-bold tracking-tight text-white">Tonnage Records Management</h1>
              </div>
            </div>
          </div>
        </div>

        {/* Data Management Component */}
        <DataManagementWrapper />
      </div>
    </div>
  )
}

// Wrapper component to handle data fetching on this page
function DataManagementWrapper() {
  return <DataManagement />
}
