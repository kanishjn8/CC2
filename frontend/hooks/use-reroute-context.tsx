"use client"

import { createContext, useCallback, useContext, useState } from "react"
import type { RerouteResult } from "@/lib/types"

interface RerouteContextValue {
  rerouteData: RerouteResult | null
  setRerouteData: (data: RerouteResult | null) => void
  clearReroute: () => void
}

const RerouteContext = createContext<RerouteContextValue>({
  rerouteData: null,
  setRerouteData: () => {},
  clearReroute: () => {},
})

export function RerouteProvider({ children }: { children: React.ReactNode }) {
  const [rerouteData, setRerouteData] = useState<RerouteResult | null>(null)
  const clearReroute = useCallback(() => setRerouteData(null), [])

  return (
    <RerouteContext.Provider value={{ rerouteData, setRerouteData, clearReroute }}>
      {children}
    </RerouteContext.Provider>
  )
}

export function useRerouteContext() {
  return useContext(RerouteContext)
}
