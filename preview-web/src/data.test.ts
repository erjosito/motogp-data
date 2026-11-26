import { describe, expect, it } from 'vitest'
import { bestSectors, cleanLaps, lapTime } from './data'
import type { Lap } from './types'

function lap(rider: string, time: number | null, pit = false): Lap {
  return {
    rider_id: rider, rider, number: 1, lap_number: 1, lap_seconds: time,
    sectors: [20, null, 30, null], speed_kmh: null, is_pit: pit,
    run_number: 1, front_tyre: null, rear_tyre: null,
  }
}

describe('lap comparison data', () => {
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
