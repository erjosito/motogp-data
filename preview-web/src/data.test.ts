import { describe, expect, it } from 'vitest'
import { bestSectors, categoryTicks, cleanLaps, lapTime, statisticText } from './data'
import type { Lap } from './types'

function lap(rider: string, time: number | null, pit = false): Lap {
  return {
    rider_id: rider, rider, number: 1, lap_number: 1, lap_seconds: time,
    sectors: [20, null, 30, null], speed_kmh: null, is_pit: pit,
    run_number: 1, front_tyre: null, rear_tyre: null,
  }
}

describe('lap comparison data', () => {
  it('simplifies statistic qualifiers without changing counts, units, timing or final/to-date scope', () => {
    expect(statisticText('OFFICIAL TITLES RECORDED')).toBe('TITLES')
    expect(statisticText('15 recorded titles. One remarkable rider.')).toBe('15 titles. One remarkable rider.')
    expect(statisticText('13 recorded GP wins in 2014: strongest winning season in this rider’s archive.'))
      .toBe('13 GP wins in 2014: strongest winning season.')
    expect(statisticText('Official standings to date · 9.5 supplied points')).toBe('standings to date · 9.5 points')
    expect(statisticText('Supplied scores, in source order')).toBe('scores, in classification order')
    expect(statisticText('Elapsed-time difference to P1 (s)')).toBe('Elapsed-time difference to P1 (s)')
    expect(statisticText('Final standings · GP + Sprint · unavailable')).toBe('Final standings · GP + Sprint · unavailable')
  })
  it('reduces categorical labels, retaining endpoints without removing plotted data', () => {
    const x = Array.from({ length: 20 }, (_, i) => `Round ${i + 1}`)
    const series = [{ id: 'one', name: 'Rider', x, y: x.map((_, i) => i) }]
    expect(categoryTicks(series, 4)).toEqual(['Round 1', 'Round 7', 'Round 14', 'Round 20'])
    expect(series[0].x).toHaveLength(20)
    expect(categoryTicks([{ ...series[0], orientation: 'h' }], 4)).toEqual([])
  })
  it('filters slow laps using each rider median and keeps the 115% boundary', () => {
    const laps = [
      lap('fast', 100), lap('fast', 100), lap('fast', 100), lap('fast', 115), lap('fast', 116),
      lap('slow', 200), lap('slow', 200), lap('slow', 229),
    ]
    expect(cleanLaps(laps, true, true).map((value) => value.lap_seconds))
      .toEqual([100, 100, 100, 115, 200, 200, 229])
  })
  it('keeps pit exclusion optional and never plots missing timing as zero', () => {
    const laps = [lap('one', 90, true), lap('one', null), lap('one', 100)]
    expect(cleanLaps(laps, true, false)).toHaveLength(1)
    expect(cleanLaps(laps, false, false)).toHaveLength(2)
    expect(bestSectors(laps)).toEqual([20, null, 30, null])
  })
  it('rounds timing across minute boundaries without displaying 60 seconds', () => {
    expect(lapTime(119.9999)).toBe('2:00.000')
    expect(lapTime(null)).toBe('\u2014')
  })
})
