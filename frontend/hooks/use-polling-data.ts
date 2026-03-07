"use client"

import { useState, useEffect, useCallback, useRef } from "react"

interface UsePollingDataOptions<T> {
  fetcher: () => Promise<T>
  fallback: T
  interval?: number
}

interface UsePollingDataReturn<T> {
  data: T
  loading: boolean
  error: string | null
  refetch: () => void
  lastUpdated: Date | null
}

export function usePollingData<T>({
  fetcher,
  fallback,
  interval = 10000,
}: UsePollingDataOptions<T>): UsePollingDataReturn<T> {
  const [data, setData] = useState<T>(fallback)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const mountedRef = useRef(true)

  const fetchData = useCallback(async () => {
    try {
      const result = await fetcher()
      if (mountedRef.current) {
        setData(result)
        setError(null)
        setLastUpdated(new Date())
      }
    } catch {
      if (mountedRef.current) {
        setData(fallback)
        setError(null)
        setLastUpdated(new Date())
      }
    } finally {
      if (mountedRef.current) setLoading(false)
    }
  }, [fetcher, fallback])

  useEffect(() => {
    mountedRef.current = true
    fetchData()

    let timer: ReturnType<typeof setInterval> | undefined
    if (interval > 0) {
      timer = setInterval(fetchData, interval)
    }

    return () => {
      mountedRef.current = false
      if (timer) clearInterval(timer)
    }
  }, [fetchData, interval])

  return { data, loading, error, refetch: fetchData, lastUpdated }
}
