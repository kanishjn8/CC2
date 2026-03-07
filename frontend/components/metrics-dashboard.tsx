"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { BarChart3, ArrowLeft } from "lucide-react"
import Link from "next/link"

export default function MetricsDashboard() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto p-6 space-y-8">
        {/* Header matching data management page style */}
        <div className="flex flex-col space-y-4 md:flex-row md:items-center md:justify-between md:space-y-0">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Button
                size="sm"
                variant="outline"
                className="bg-transparent border-border text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
          </div>
        </div>

        {/* Title Section matching data management page */}
        <div className="flex items-center gap-4">
          <div className="p-3 bg-primary/10 rounded-lg border border-primary/20">
            <BarChart3 className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-foreground">Metrics Dashboard</h1>
        </div>

        {/* PostHog Dashboard - Final height adjustment */}
        <div className="max-w-5xl mx-auto">
          <Card className="bg-card border-border shadow-xl">
            <CardContent className="p-0">
              <div className="relative">
                <iframe
                  width="100%"
                  height="3200"
                  frameBorder="0"
                  allowFullScreen
                  src="https://us.posthog.com/embedded/yFR-gBmfXon9FS3SMp9M9c1OaGnraA"
                  className="rounded-lg"
                  style={{
                    filter: "brightness(0.9) contrast(1.1)",
                    background: "#000000",
                    maxWidth: "1100px",
                    margin: "0 auto",
                  }}
                />
                {/* Overlay to help with dark theme */}
                <div className="absolute inset-0 bg-black/10 pointer-events-none rounded-lg"></div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
