import { describe, expect, it } from 'vitest'
import { bestSectors, categoryTicks, cleanLaps, confirmedFinal, lapSamples, lapTakeaway, lapTime, sectorTakeaway, standingsLabel, statisticText } from './data'
import type { Lap } from './types'

function lap(rider: string, time: number | null, pit = false): Lap {
  return {
    rider_id: rider, rider, number: 1, lap_number: 1, lap_seconds: time,
    sectors: [20, null, 30, null], speed_kmh: null, is_pit: pit,
    run_number: 1, front_tyre: null, rear_tyre: null,
  }
}

describe('lap comparison data', () => {
  it('never treats missing lifecycle evidence or an unknown status as confirmed finality', () => {
    expect(confirmedFinal()).toBe(false)
    expect(confirmedFinal({ status: 'unknown', evidence: null })).toBe(false)
    expect(confirmedFinal({ status: 'official_final', evidence: null })).toBe(false)
    expect(standingsLabel()).toBe('Standings · finality unverified')
    expect(statisticText('At that point in the season, 9 points behind.')).toContain('At that point in the season')
  })
  it('simplifies statistic qualifiers without changing counts, units, timing or final/to-date scope', () => {
    expect(statisticText('OFFICIAL TITLES RECORDED')).toBe('TITLES')
    expect(statisticText('15 recorded titles. One remarkable rider.')).toBe('15 titles. One remarkable rider.')
    expect(statisticText('13 recorded GP wins in 2014: strongest winning season in this rider’s archive.'))
      .toBe('13 GP wins in 2014: strongest winning season.')
    expect(statisticText('Official standings to date · 9.5 supplied points')).toBe('standings to date · 9.5 points')
    expect(statisticText('Supplied scores, in source order')).toBe('scores, in classification order')
    expect(statisticText('Elapsed-time difference to P1 (s)')).toBe('Elapsed-time difference to P1 (s)')
    expect(statisticText('Final standings · GP + Sprint · unavailable')).toBe('Final standings · GP + Sprint · unavailable')
    expect(statisticText('1 points ahead · 11 points · 1.1 points')).toBe('1 point ahead · 11 points · 1.1 points')
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
    expect(cleanLaps([lap('one', Infinity), lap('one', 0), lap('one', -1)], false, false)).toEqual([])
  })
  it('rounds timing across minute boundaries without displaying 60 seconds', () => {
    expect(lapTime(119.9999)).toBe('2:00.000')
    expect(lapTime(null)).toBe('\u2014')
  })
  it('compares included medians, not matched lap numbers, and updates with selection/filter samples', () => {
    const riders = [{ rider_id: 'marc', rider: 'Marc Marquez', number: 93 }, { rider_id: 'bez', rider: 'Marco Bezzecchi', number: 72 }]
    const laps = [lap('marc', 100), lap('marc', 100.426), lap('bez', 99), { ...lap('bez', 99.778), lap_number: 24 }]
    expect(lapTakeaway(laps, riders).title).toContain("Marco Bezzecchi's median lap is 0.824s quicker than Marc Marquez's")
    expect(lapSamples(laps, riders)[1].laps.map((value) => value.lap_number)).toEqual([1, 24])
    expect(lapTakeaway(laps, riders.slice(0, 1)).detail).toContain('One selected rider')
    expect(lapTakeaway(laps.slice(0, 3), riders).title).toContain('More timed laps')
    expect(lapTakeaway([], riders).title).toContain('More timed laps')
    const tied = [...laps.slice(0, 2), lap('bez', 100), lap('bez', 100.426)]
    expect(lapTakeaway(tied, riders).title).toContain('share the lowest median')
    expect(lapTakeaway(tied, [...riders].reverse())).toEqual(lapTakeaway(tied, riders))
    const pit = { ...lap('marc', 130), is_pit: true }
    expect(lapTakeaway(cleanLaps([...laps, pit], false, false), riders).title)
      .not.toEqual(lapTakeaway(cleanLaps([...laps, pit], true, false), riders).title)
  })
  it('distinguishes selected best-sector combinations from actual laps and requires all sectors', () => {
    const riders = [{ rider_id: 'one', rider: 'One Rider', number: 1 }, { rider_id: 'two', rider: 'Two Rider', number: 2 }]
    const first = { ...lap('one', 100), sectors: [20, 25, 30, 25] }
    const otherLap = { ...first, lap_number: 2, sectors: [21, 24, 31, 26] }
    const second = { ...lap('two', 101), sectors: [20.1, 25, 30, 25] }
    const takeaway = sectorTakeaway([first, otherLap, second], riders)
    expect(takeaway.title).toContain("One Rider's best-sector sum is 1.100s lower")
    expect(takeaway.detail).toContain('theoretical combination')
    expect(takeaway.detail).toContain('sector 2, 1.000s')
    expect(sectorTakeaway([first, second], riders.slice(0, 1)).detail).toContain('not an actual lap')
    expect(sectorTakeaway([first, { ...second, sectors: [20.1, null, 30, 25] }], riders).title).toContain('unavailable')
    expect(sectorTakeaway([first, { ...second, sectors: first.sectors }], riders).title).toContain('share the lowest')
    expect(bestSectors([{ ...first, sectors: [0, -1, Infinity, null] }])).toEqual([null, null, null, null])
  })
})
