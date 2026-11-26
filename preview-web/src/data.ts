import type { Lap } from './types'

export const MARC_ID = 'f55b433d-38b8-4d1d-bb3a-a709c82a0260'

const palette = ['--cp-link', '--cp-success', '--cp-warning', '--cp-text-soft', '--cp-danger']
const dashes = ['solid', 'dash', 'dot', 'dashdot'] as const

export function riderStyle(id: string) {
  if (id === MARC_ID) return { token: '--cp-accent', dash: 'solid' as const }
  let hash = 0
  for (const char of id) hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  return { token: palette[hash % palette.length], dash: dashes[Math.floor(hash / palette.length) % dashes.length] }
}

export function lapTime(seconds: number | null | undefined) {
  if (seconds == null || !Number.isFinite(seconds)) return '\u2014'
  const milliseconds = Math.round(seconds * 1000)
  const minutes = Math.floor(milliseconds / 60000)
  const rest = milliseconds % 60000
  return `${minutes}:${Math.floor(rest / 1000).toString().padStart(2, '0')}.${(rest % 1000).toString().padStart(3, '0')}`
}

export function signed(value: number) {
  return `${value > 0 ? '+' : ''}${Number(value.toFixed(1))}`
}

export function median(values: number[]) {
  const sorted = [...values].sort((a, b) => a - b)
  const middle = Math.floor(sorted.length / 2)
  return sorted.length ? (sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2) : null
}

export function cleanLaps(laps: Lap[], excludePit: boolean, excludeSlow: boolean) {
  const usable = laps.filter((lap) => lap.lap_seconds != null && (!excludePit || !lap.is_pit))
  if (!excludeSlow) return usable
  const groups = new Map<string, number[]>()
  for (const lap of usable) {
    const times = groups.get(lap.rider_id) ?? []
    times.push(Math.round(lap.lap_seconds! * 1000))
    groups.set(lap.rider_id, times)
  }
  const medians = new Map([...groups].map(([id, times]) => [id, median(times)!]))
  return usable.filter((lap) => Math.round(lap.lap_seconds! * 1000) * 100 <= medians.get(lap.rider_id)! * 115)
}

export function bestSectors(laps: Lap[]) {
  return [0, 1, 2, 3].map((index) => {
    const values = laps.flatMap((lap) => lap.sectors[index] == null ? [] : [lap.sectors[index]!])
    return values.length ? Math.min(...values) : null
  })
}
