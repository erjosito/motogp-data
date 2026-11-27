import { useCallback, useEffect, useState } from 'react'
import { appPath } from './paths'

export function useResource<T>(url: string | null) {
  const [attempt, setAttempt] = useState(0)
  const key = `${url}:${attempt}`
  const [state, setState] = useState<{
    key: string | null; data: T | null; error: string | null; loading: boolean
  }>({ key: null, data: null, error: null, loading: false })
  const retry = useCallback(() => setAttempt((value) => value + 1), [])

  useEffect(() => {
    if (!url) return
    const controller = new AbortController()
    fetch(appPath(url), { signal: controller.signal, cache: 'no-store' })
      .then(async (response) => {
        if (!response.ok) {
          let message = `The request failed (${response.status}). Please retry.`
          const body: unknown = await response.json()
          if (typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string') {
            message = body.detail
          }
          throw new Error(message)
        }
        return response.json() as Promise<T>
      })
      .then((data) => {
        if (!controller.signal.aborted) setState({ key, data, error: null, loading: false })
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setState({
          key, data: null, loading: false,
          error: error instanceof Error ? error.message : 'The data service could not be reached.',
        })
      })
    return () => controller.abort()
  }, [url, key])

  return {
    ...(state.key === key ? state : { key, data: null, error: null, loading: Boolean(url) }),
    retry,
  }
}
