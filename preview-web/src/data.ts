import type { Lap, Rider, SeasonLifecycle } from './types'
import type { ChartSeries } from './PlotChart'

export function statisticText(text: string) {
  return text.replace(/\b(?:recorded|imported|supplied|stored|official|officially)\b\s*/gi, '')
    .replace(/(?<![\d.])1 points\b/g, '1 point')
    .replace(/\s+in this rider['’]s archive\b/gi, '')
    .replace(/\bsource order\b/gi, 'classification order')
    .replace(/\bsource ranks?\b/gi, 'rank')
    .replace(/\s{2,}/g, ' ').trim()
}

export function confirmedFinal(lifecycle?: SeasonLifecycle) {
  return lifecycle?.status === 'official_final' && lifecycle.evidence != null
}

export function standingsLabel(lifecycle?: SeasonLifecycle) {
  return confirmedFinal(lifecycle) ? 'Final standings' : 'Standings · finality unverified'
}

export function categoryTicks(series: ChartSeries[], maximum: number) {
  const labels = [...new Set(series.filter((line) => line.orientation !== 'h' && line.type !== 'pie').flatMap((line) => line.x).filter((value): value is string => typeof value === 'string'))]
  if (labels.length <= maximum) return labels
  return Array.from({ length: maximum }, (_, index) => labels[Math.round(index * (labels.length - 1) / (maximum - 1))])
}

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
  const usable = laps.filter((lap) => lap.lap_seconds != null && Number.isFinite(lap.lap_seconds) && lap.lap_seconds > 0 && (!excludePit || !lap.is_pit))
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
    const values = laps.flatMap((lap) => lap.sectors[index] == null || !Number.isFinite(lap.sectors[index]) || lap.sectors[index]! <= 0 ? [] : [lap.sectors[index]!])
    return values.length ? Math.min(...values) : null
  })
}

export function lapSamples(laps: Lap[], riders: Rider[]) {
  return riders.map((rider) => {
    const included = laps.filter((lap) => lap.rider_id === rider.rider_id && lap.lap_seconds != null
      && Number.isFinite(lap.lap_seconds) && lap.lap_seconds > 0)
    const values = included.map((lap) => lap.lap_seconds!)
    return { rider, laps: included, values, median: median(values) }
  })
}

export function lapTakeaway(laps: Lap[], riders: Rider[]) {
  const samples = lapSamples(laps, riders)
  const compared = samples.filter((sample): sample is typeof sample & { median: number } =>
    sample.values.length >= 2 && sample.median != null).sort((a, b) =>
    Math.round(a.median * 1000) - Math.round(b.median * 1000) || a.rider.rider_id.localeCompare(b.rider.rider_id))
  if (compared.length !== samples.length || !compared.length) return {
    title: 'More timed laps are needed for a median comparison.',
    detail: 'Each selected rider needs at least two included timed laps.',
  }
  const [first, second] = compared
  if (!second) return { title: `${first.rider.rider}'s median lap: ${lapTime(first.median)}.`,
    detail: 'One selected rider; no between-rider comparison.' }
  const tied = compared.filter((sample) => Math.round(sample.median * 1000) === Math.round(first.median * 1000))
  if (tied.length > 1) return { title: `${tied.map((sample) => sample.rider.rider).join(' / ')} share the lowest median: ${lapTime(first.median)}.`,
    detail: 'Equal at displayed millisecond precision among the selected riders.' }
  const delta = (Math.round(second.median * 1000) - Math.round(first.median * 1000)) / 1000
  return { title: `${first.rider.rider}'s median lap is ${delta.toFixed(3)}s quicker than ${second.rider.rider}'s.`,
    detail: samples.length > 2 ? `Lowest versus next-lowest median among ${samples.length} selected riders.` : 'The two selected riders, using their included samples.' }
}

export function sectorTakeaway(laps: Lap[], riders: Rider[]) {
  const rows = riders.map((rider) => {
    const sectors = bestSectors(laps.filter((lap) => lap.rider_id === rider.rider_id))
    return { rider, sectors, sum: sectors.every((value) => value != null)
      ? sectors.reduce<number>((total, value) => total + value!, 0) : null }
  })
  const complete = rows.filter((row): row is typeof row & { sum: number } => row.sum != null)
    .sort((a, b) => Math.round(a.sum * 1000) - Math.round(b.sum * 1000) || a.rider.rider_id.localeCompare(b.rider.rider_id))
  if (!complete.length || complete.length !== rows.length) return {
    title: 'A complete selected-rider sector comparison is unavailable.',
    detail: 'Each selected rider needs all four best-sector values; missing sectors are not zero.',
  }
  const [first, second] = complete
  if (!second) return { title: `${first.rider.rider}'s best sectors sum to ${lapTime(first.sum)}.`,
    detail: 'One selected rider; this theoretical combination is not an actual lap.' }
  const tied = complete.filter((row) => Math.round(row.sum * 1000) === Math.round(first.sum * 1000))
  if (tied.length > 1) return { title: `${tied.map((row) => row.rider.rider).join(' / ')} share the lowest best-sector sum: ${lapTime(first.sum)}.`,
    detail: 'Equal at displayed millisecond precision; theoretical combinations, not actual laps.' }
  const delta = (Math.round(second.sum * 1000) - Math.round(first.sum * 1000)) / 1000
  const differences = first.sectors.map((value, index) => ({ index, gap: second.sectors[index]! - value! }))
    .sort((a, b) => Math.abs(b.gap) - Math.abs(a.gap) || a.index - b.index)
  const largest = differences[0]
  return { title: `${first.rider.rider}'s best-sector sum is ${delta.toFixed(3)}s lower than ${second.rider.rider}'s.`,
    detail: `Lowest versus next-lowest theoretical combination among ${rows.length} selected riders. Largest pair difference: sector ${largest.index + 1}, ${Math.abs(largest.gap).toFixed(3)}s in ${largest.gap >= 0 ? first.rider.rider : second.rider.rider}'s favor.` }
}
