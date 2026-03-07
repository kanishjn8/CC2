"use client"

import React from "react"
import { usePathname } from "next/navigation"
import { Bell, RefreshCw, Search } from "lucide-react"
import { Button } from "@/components/ui/button"

const PAGE_TITLES: Record<string, string> = {
  "/": "Network Overview",
  "/shipments": "Shipment Risk Explorer",
  "/warehouses": "Warehouse Operations",
  "/carriers": "Carrier Reliability",
  "/decisions": "AI Agent Decisions",
  "/simulator": "Scenario Simulator",
}

export function AppHeader() {
  const pathname = usePathname()
  const title = PAGE_TITLES[pathname] || "RouteSense"

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-white/[0.06] bg-black/40 backdrop-blur-xl px-6">
      <div>
        <h2 className="text-lg font-semibold text-foreground">{title}</h2>
        <p className="text-xs text-muted-foreground">
          Real-time logistics intelligence
        </p>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))}
          className="hidden sm:flex items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 text-xs text-muted-foreground hover:bg-white/[0.05] transition-colors"
        >
          <Search className="h-3.5 w-3.5" />
          <span>Search...</span>
          <kbd className="ml-4 rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
            ⌘K
          </kbd>
        </button>
        <Button variant="ghost" size="icon" title="Refresh data">
          <RefreshCw className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" className="relative" title="Notifications">
          <Bell className="h-4 w-4" />
          <span className="absolute -top-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-destructive text-[9px] font-bold text-destructive-foreground">
            3
          </span>
        </Button>
        <div className="ml-2 h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xs font-bold text-white">
          OP
        </div>
      </div>
    </header>
  )
}
