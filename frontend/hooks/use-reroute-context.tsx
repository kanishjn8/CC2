"use client"

import { createContext, useCallback, useContext, useState } from "react"
import type { RerouteResult, CarrierSwitchResult } from "@/lib/types"

interface RerouteContextValue {
  rerouteData: RerouteResult | null
  setRerouteData: (data: RerouteResult | null) => void
  clearReroute: () => void
  carrierSwitchData: CarrierSwitchResult | null
  setCarrierSwitchData: (data: CarrierSwitchResult | null) => void
  clearCarrierSwitch: () => void
  clearAll: () => void
}

const RerouteContext = createContext<RerouteContextValue>({
  rerouteData: null,
  setRerouteData: () => {},
  clearReroute: () => {},
  carrierSwitchData: null,
  setCarrierSwitchData: () => {},
  clearCarrierSwitch: () => {},
  clearAll: () => {},
})

export function RerouteProvider({ children }: { children: React.ReactNode }) {
  const [rerouteData, setRerouteData] = useState<RerouteResult | null>(null)
  const [carrierSwitchData, setCarrierSwitchData] = useState<CarrierSwitchResult | null>(null)
  const clearReroute = useCallback(() => setRerouteData(null), [])
  const clearCarrierSwitch = useCallback(() => setCarrierSwitchData(null), [])
  const clearAll = useCallback(() => {
    setRerouteData(null)
    setCarrierSwitchData(null)
  }, [])

  return (
    <RerouteContext.Provider value={{
      rerouteData, setRerouteData, clearReroute,
      carrierSwitchData, setCarrierSwitchData, clearCarrierSwitch,
      clearAll,
    }}>
      {children}
    </RerouteContext.Provider>
  )
}

export function useRerouteContext() {
  return useContext(RerouteContext)
}
