/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { MARC_ID } from './data'
import { seasonCharts } from './seasonCharts'
import type { Championship, Standing } from './types'
import { ChampionshipContent } from './App'

function standing(rider_id: string, points: number, position: number, extra: Partial<Omit<Standing, 'constructor'>> = {}): Standing {
  return { rider_id, rider: rider_id, points, position, number: null, gap: 100 - points,
    wins: null, podiums: null, team: null, constructor: null, series: [], ...extra }
}

function championship(standings: Standing[], extra: Partial<Championship> = {}): Championship {
  return { season: 1967, category: 'premier', standings: standings.map((rider) => ({ ...rider, gap: standings[0].points - rider.points })),
    rounds: [], gp_results: 0, weekends: 0, scoring_sessions: 0,
    standings_source: 'official', is_final: true, external_sources_used: false, comeback: null,
    official_points_inconsistent: false, points_warning: null,
    story: { kind: 'standings', headline: 'Story', accent: 'Evidence', summary: 'Summary',
      metric_label: 'Points', metric: 100, metric_note: 'Official', context_url: null }, ...extra }
}

describe('evidence-led season chart pairs', () => {
  it('keeps supplied 9/28/46 scores paired with official ranks without warnings or derived margins', () => {
    const standings = [standing('Agostini', 9, 1, { gap: null }), standing('Carruthers', 28, 2, { gap: null }),
      standing('Pasolini', 46, 3, { gap: null })]
    const data = championship(standings, {
      season: 1970, category: '350cc', standings,
      official_points_inconsistent: true,
      points_warning: 'Supplied point totals require source verification. Period scoring or source discrepancies may explain this.',
      story: { ...championship([]).story, kind: 'close-finish' },
    })
    const before = structuredClone(data)
    const result = seasonCharts(data)
    expect(result.layout).toBe('source-verification')
    expect(result.charts.map((chart) => chart.kind)).toEqual(['bar', 'scatter'])
    expect(result.charts[0].series[0].x).toEqual([9, 28, 46])
    expect(result.charts[0].series[0].y).toEqual(['P1 Agostini', 'P2 Carruthers', 'P3 Pasolini'])
    expect(result.charts[1].series.map((series) => [series.x, series.y])).toEqual([[[9], [1]], [[28], [2]], [[46], [3]]])
    expect(result.charts.every((chart) => !chart.note.includes('verification') && !chart.xTitle?.includes('verification'))).toBe(true)
    expect(result.charts.every((chart) => !chart.id.includes('gap') && chart.id !== 'margins')).toBe(true)
    expect(seasonCharts({ ...data, points_warning: null }).charts.every((chart) =>
      !chart.note.includes('verification'))).toBe(true)
    expect(data).toEqual(before)
  })

  it('labels independently corrected scores without deriving margins', () => {
    const standings = [standing('Agostini', 90, 1, { gap: null }), standing('Carruthers', 58, 2, { gap: null }),
      standing('Pasolini', 46, 3, { gap: null })]
    const result = seasonCharts(championship(standings, {
      season: 1970, category: '350cc', standings, official_points_inconsistent: true,
      points_correction: { note: 'Two corrections', source_url: 'https://example.com', corroborating_url: 'https://example.org' },
    }))
    expect(result.layout).toBe('source-verification')
    expect(result.charts[0].series[0].x).toEqual([90, 58, 46])
    expect(result.charts.every((chart) => chart.note.includes('corrections') && !chart.note.includes('unchanged'))).toBe(true)
    expect(result.charts.every((chart) => !chart.id.includes('gap') && chart.id !== 'margins')).toBe(true)
  })

  it('never treats a null gap as a close finish, tie or zero-valued lollipop endpoint', () => {
    const standings = [standing('first', 46, 1, { gap: 0 }), standing('second', 46, 2, { gap: null })]
    for (const kind of ['standings', 'tie-break', 'close-finish'] as const) {
      const result = seasonCharts(championship(standings, { standings, story: { ...championship([]).story, kind } }))
      expect(result.layout).toBe('standings')
      expect(result.charts.map((chart) => chart.kind)).toEqual(['bar', 'scatter'])
      expect(result.charts[1].series.map((series) => series.x)).toEqual([[46], [46]])
    }
    const negative = standings.map((rider) => ({ ...rider, gap: rider.position === 1 ? 0 : -19 }))
    expect(seasonCharts(championship(negative, { standings: negative })).charts.map((chart) => chart.kind)).toEqual(['bar', 'scatter'])
  })

  it('preserves distinct official ranks for tied points, without inventing a timeline', () => {
    const data = championship([
      standing('Agostini', 46, 1, { gap: 0 }), standing('Hailwood', 46, 2, { gap: 0 }),
    ])
    const result = seasonCharts(data)
    expect(result.layout).toBe('tie-break')
    expect(result.charts[0].kind).toBe('comparison')
    expect(result.charts[0].series.map((series) => [series.x, series.y])).toEqual([[[46], [1]], [[46], [2]]])
    expect(result.charts[1].series[0].x).toEqual([0, 0])
    expect(result.charts[1].series[0].y).toEqual(['P1 Agostini', 'P2 Hailwood'])
    expect(result.charts.every((chart) => chart.kind !== 'line')).toBe(true)
    const shared = seasonCharts(championship([standing('one', 46.5, 1), standing('two', 46.5, 1)]))
    expect(shared.charts[0].title).toBe('Same points. Shared rank.')
    expect(shared.charts[0].series.map((row) => [row.x[0], row.y[0]])).toEqual([[46.5, 1], [46.5, 1]])
  })

  it('bridges the actual 102-point deficit to the 43-point lead, even if Marc is not first in the table', () => {
    const low = { session_id: 'low', event_id: 'ita', event: 'ITA', type: 'RAC', label: 'ITA / Race', date: null, points: 100, margin: -102 }
    const latest = { ...low, session_id: 'latest', event: 'POR', label: 'POR / Race', points: 439, margin: 43 }
    const data = championship([standing('other', 500, 1), standing(MARC_ID, 439, 2)], {
      season: 2026,
      story: { ...championship([]).story, kind: 'comeback' },
      comeback: { rider_id: MARC_ID, history: [low, latest], low, max_deficit: 102,
        current_margin: 43, recovered: 145, verified_102: true },
    })
    const charts = seasonCharts(data).charts
    expect(charts[0].series[0].id).toBe(MARC_ID)
    expect(charts[0].series[0].y).toEqual([-102, 43])
    expect(charts[1].series[0].base).toEqual([0, -102, 0])
    expect(charts[1].series[0].y).toEqual([-102, 145, 43])
    const html = renderToStaticMarkup(createElement(ChampionshipContent, { data, category: 'premier', theme: 'light' }))
    expect(html.indexOf('data-season-chart="recovery-bridge"')).toBeLessThan(html.indexOf('class="standings-table"'))
    expect(html).toContain('championship standings')
    const single = seasonCharts({ ...data, comeback: { ...data.comeback!, history: [low] } }).charts
    expect(single[1].kind).toBe('bridge')
    expect(single[1].series[0].y).toEqual([-102, 0, -102])
    expect(single[1].series[0].colors?.at(-1)).toBe('--cp-danger')
  })

  it('shows the points-versus-wins trade-off and partitions podiums without double-counting wins', () => {
    const data = championship([
      standing('Martin', 508, 1, { wins: 3, podiums: 16 }),
      standing('Bagnaia', 498, 2, { wins: 11, podiums: 16 }),
    ])
    const result = seasonCharts(data)
    expect(result.layout).toBe('consistency')
    expect(result.charts[0].series.map((series) => [series.x[0], series.y[0]])).toEqual([[3, 508], [11, 498]])
    expect(result.charts[1].series.map((series) => series.y)).toEqual([[3, 11], [13, 5]])
  })

  it('uses recorded victories, not scheduled GPs, as the win-share denominator and separates equal surnames', () => {
    const data = championship([
      standing('Marc Marquez', 545, 1, { wins: 11 }), standing('Alex Marquez', 467, 2, { wins: 3 }),
    ], { gp_results: 22 })
    const charts = seasonCharts(data).charts
    expect(charts[0].series[0].y).toEqual(['P1 Marquez', 'P2 Marquez'])
    expect(charts[1].series[0].y).toEqual([11, 3])
    expect(charts[1].note).toContain('14 imported GP wins')
  })

  it('retains decimal historical scores and includes the entire field in classified-point shares', () => {
    const data = championship([
      standing('Lawson', 228, 1), standing('Rainey', 210.5, 2), standing('third', 180, 3), standing('fourth', 77.5, 4),
    ])
    const charts = seasonCharts(data).charts
    expect(charts[0].series[0].x).toEqual([228, 210.5, 180, 77.5])
    expect(charts[1].series[0].y).toEqual([228, 210.5, 180, 77.5])
    expect(charts[1].note).toContain('not share of all points awarded')
  })

  it('uses actual record coverage, including known zeros, when no title standings are available', () => {
    const result = seasonCharts(championship([], { coverage: {
      sessions: 8, classified_sessions: 3, classification_rows: 42, lap_rows: 0,
    } }))
    expect(result.charts[0].series[0].y).toEqual([42, 0])
    expect(result.charts[1].series[0].y).toEqual([3, 5])
    expect(result.charts.every((chart) => chart.series[0].showValues)).toBe(true)
    expect(() => seasonCharts(championship([]))).toThrow('coverage evidence is missing')
  })

  it('shows decisive session points rather than treating cumulative totals as race points', () => {
    const rounds = ['one', 'two', 'three'].map((id) => ({ session_id: id, event_id: id, event: id, label: id, type: 'RAC', date: null }))
    const data = championship([
      standing('winner', 60, 1, { series: [20, 35, 60] }), standing('rival', 58, 2, { series: [25, 40, 58] }),
    ], { standings_source: 'computed', rounds, story: { ...championship([]).story, kind: 'late-surge' } })
    expect(seasonCharts(data).charts[1].series.map((series) => series.y)).toEqual([[20, 15, 25], [25, 15, 18]])
  })

  it('keeps single-rider and zero-score official evidence chartable without a fabricated percentage', () => {
    const result = seasonCharts(championship([standing('only', 0, 1, { gap: 0 })]))
    expect(result.charts[0].series[0].x).toEqual([0])
    expect(result.charts[1].series[0].y).toEqual(['P1 only'])
    expect(result.charts.every((chart) => chart.kind !== 'doughnut')).toBe(true)
  })
  it('directly labels the historical official leading pair and field gaps without reordering scores', () => {
    const data = championship([standing('Angel Nieto', 76, 1), standing('Aalt Toersen', 75, 2),
      standing('third', 65.5, 3)], { season: 1969, category: '50cc' })
    const before = structuredClone(data)
    const charts = seasonCharts(data).charts
    expect(charts[0].kind).toBe('comparison')
    expect(charts[0].series.map((row) => [row.name, row.x[0], row.y[0]])).toEqual([
      ['Angel Nieto', 76, 1], ['Aalt Toersen', 75, 2],
    ])
    expect(charts[1].series).toHaveLength(1)
    expect(charts[1].series[0].y).toEqual(['P1 Angel Nieto', 'P2 Aalt Toersen', 'P3 third'])
    expect(charts[1].series[0].x).toEqual([0, 1, 10.5])
    expect(charts[1].series[0].showValues).toBe(true)
    const html = renderToStaticMarkup(createElement(ChampionshipContent, { data, category: '50cc', theme: 'dark' }))
    expect(html).toContain('class="score-comparison"')
    expect(html).toContain('<h3>Angel Nieto</h3><strong>76</strong>')
    expect(data).toEqual(before)
    expect(seasonCharts({ ...data, season: 2015 }).charts[0].kind).toBe('scatter')
  })
})

const evidencePath = process.env.SEASON_CHART_EVIDENCE
if (evidencePath) {
  const evidence: Championship[] = JSON.parse(readFileSync(evidencePath, 'utf8'))
  describe('every available SQL-backed season/category', () => {
    for (const data of evidence) it(`${data.season} / ${data.category}`, () => {
      const { charts } = seasonCharts(data)
      expect(charts).toHaveLength(2)
      for (const chart of charts) {
        expect(chart.series.length).toBeGreaterThan(0)
        for (const series of chart.series) {
          expect(series.x.length).toBeGreaterThan(0)
          expect(series.y).toHaveLength(series.x.length)
          expect(series.y.every((value) => value == null || typeof value === 'string' || Number.isFinite(value))).toBe(true)
          if (series.type === 'pie') {
            expect(series.y.every((value) => typeof value === 'number' && value >= 0)).toBe(true)
            expect(series.y.reduce<number>((total, value) => total + Number(value), 0)).toBeGreaterThan(0)
          }
        }
      }
      if (data.standings_source === 'official' && !data.comeback?.verified_102) {
        expect(charts.some((chart) => chart.kind === 'line')).toBe(false)
      }
      const markup = renderToStaticMarkup(createElement(ChampionshipContent, { data, category: data.category, theme: 'light' }))
      expect(markup.match(/data-season-chart=/g)).toHaveLength(2)
    })
  })
}
