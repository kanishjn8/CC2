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
  // Store fallback in a ref so it never triggers re-renders / effect resets
  const fallbackRef = useRef(fallback)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const [data, setData] = useState<T>(fallback)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const mountedRef = useRef(true)

  const fetchData = useCallback(async () => {
    try {
      const result = await fetcherRef.current()
      if (mountedRef.current) {
        setData(result)
        setError(null)
        setLastUpdated(new Date())
      }
    } catch {
      if (mountedRef.current) {
        // On error keep existing data (don't reset to fallback)
        setError("Fetch failed")
      }
    } finally {
      if (mountedRef.current) setLoading(false)
    }
  }, []) // stable — never changes

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
