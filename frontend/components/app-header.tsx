"use client"

import React from "react"
import { usePathname } from "next/navigation"
import { Search } from "lucide-react"

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
      </div>
    </header>
  )
}
