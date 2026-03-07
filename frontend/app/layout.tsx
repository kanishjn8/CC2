import type React from "react"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/toaster"
import { AppSidebar } from "@/components/app-sidebar"
import { AppHeader } from "@/components/app-header"
import { BackgroundWrapper } from "@/components/background-wrapper"
import { CommandPalette } from "@/components/command-palette"
import { AlertNotifications } from "@/components/alert-notifications"
import { RerouteProvider } from "@/hooks/use-reroute-context"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "RouteSense — AI Logistics Dashboard",
  description: "AI-powered logistics monitoring, risk detection, and autonomous decision dashboard",
  generator: "v0.app",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
          <RerouteProvider>
            <BackgroundWrapper />
            <AppSidebar />
            <div className="ml-[260px] min-h-screen flex flex-col">
              <AppHeader />
              <main className="flex-1 p-6">{children}</main>
            </div>
            <CommandPalette />
            <AlertNotifications />
            <Toaster />
          </RerouteProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
