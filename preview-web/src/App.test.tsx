import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import App from './App'
import * as api from './api'
import type { Championship } from './types'

function render(search: string) {
  vi.stubGlobal('window', { location: { search, pathname: '/paddock/' } })
  vi.stubGlobal('document', { documentElement: { dataset: { theme: 'light' } } })
  return renderToStaticMarkup(<App />)
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('category selector and navigation', () => {
  it('keeps an extinct category selectable alongside every lineage while resources load', () => {
    const markup = render('?category=80cc&season=1984&view=laps&clawpilotTheme=dark')
    expect(markup).toContain('aria-label="Category"')
    expect(markup).toContain('<option value="80cc" selected="">80cc</option>')
    for (const category of ['premier', 'intermediate', 'lightweight', '350cc', '50cc']) {
      expect(markup).toContain(`<option value="${category}">`)
    }
    expect(markup).toContain('category=80cc&amp;season=1984')
    expect(markup).toContain('clawpilotTheme=dark')
    expect(markup).not.toContain('Premier class')
  })

  it('defaults to premier but offers recovery for invalid deep-linked categories', () => {
    expect(render('')).toContain('<option value="premier" selected="">MotoGP / 500cc</option>')
    const markup = render('?category=unsupported')
    expect(markup).toContain('This category key is unsupported')
    expect(markup).toContain('aria-label="Category"')
    expect(markup).not.toContain('Loading race data')
  })

  it('preserves 9/28/46 supplied scores and official champion rank without displaying a points margin', () => {
    const data: Championship = {
      season: 1970, category: '350cc', standings_source: 'official', is_final: true,
      official_points_inconsistent: true,
      points_warning: 'Supplied official point totals require source verification. Period scoring or source discrepancies may explain this.',
      external_sources_used: false, rounds: [], gp_results: 0, weekends: 0,
      scoring_sessions: 0, comeback: null,
      standings: ['Giacomo Agostini', 'Kel Carruthers', 'Renzo Pasolini'].map((rider, index) => ({
        rider, rider_id: rider, number: null, position: index + 1,
        points: [9, 28, 46][index], gap: null, wins: null, podiums: null,
        team: null, constructor: 'Bike', series: [],
      })),
      story: {
        kind: 'standings',
        headline: 'Giacomo Agostini: officially ranked first.',
        accent: 'Official standings, in source order.',
        summary: 'Official source ranks and supplied scores are preserved unchanged.',
        metric_label: 'OFFICIAL RANK', metric: 1, metric_note: 'Official champion rank',
        context_url: null,
      },
    }
    vi.spyOn(api, 'useResource')
      .mockReturnValueOnce({ key: 'seasons', data: [1970], loading: false, error: null, retry: () => {} })
      .mockReturnValueOnce({ key: 'championship', data, loading: false, error: null, retry: () => {} })
    const markup = render('?category=350cc&season=1970')
    expect(markup).not.toContain('role="alert"')
    expect(markup).not.toContain('Period scoring or source discrepancies')
    expect(markup).not.toContain('need verification')
    expect(markup).not.toContain('Verification required')
    expect(markup).not.toContain('source verification required')
    expect(markup).toContain('OFFICIAL CHAMPION')
    expect(markup).toContain('Giacomo Agostini')
    expect(markup).toContain('<th>Pts</th>')
    for (const points of [9, 28, 46]) expect(markup).toContain(`class="strong numeric">${points}</td>`)
    expect(markup.match(/class="muted numeric">—<\/td>/g)).toHaveLength(3)
    expect(markup).not.toContain('LEAD OVER SECOND')
    expect(markup).not.toContain('0 pts')
    expect(markup).not.toContain('−-19')
    expect(markup).not.toContain('The comeback curve')
    expect(markup).not.toContain('a narrow crown')
    expect(markup.match(/data-season-chart=/g)).toHaveLength(2)
    expect(markup).toContain('data-chart-kind="bar"')
    expect(markup).toContain('data-chart-kind="scatter"')
    expect(markup).not.toContain('data-chart-kind="lollipop"')
  })
})
