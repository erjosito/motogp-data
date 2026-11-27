import { describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import ResultStory from './ResultStory'
import DetailSection from './DetailSection'
import type { Analysis, Result } from './types'

const row = (position: number, extra: Partial<Omit<Result, 'constructor'>> = {}): Result => ({
  rider_id: `rider-${position}`, rider: `Rider ${position}`, number: position === 1 ? 72 : null,
  position, source_kind: 'official-api', team: 'Team', constructor: 'Bike', total_laps: 25,
  time_text: '41:30.802', gap_first: '0.000', status: 'INSTND', best_lap_seconds: null,
  top_speed: null, points: 25, finish_gap_seconds: position === 1 ? 0 : position, finish_gap_reason: null, ...extra,
})
const analysis = (results: Result[], session_type = 'RAC'): Analysis => ({
  session: { session_id: 'race', session_type, session_label: 'Race', session_date: null,
    weather: null, air_temp: null, ground_temp: null, event_id: 'por', short_name: 'POR',
    event_name: 'Portugal', circuit_name: null, country_name: 'Portugal', season_year: 2026 },
  results, laps: [],
})

describe('recorded finish story', () => {
  it('directly labels same-lap elapsed gaps while preserving rank, numbers, initials and source context', () => {
    const data = analysis([row(1), row(2, { gap_first: '3.845', finish_gap_seconds: 3.845 }), row(3, { finish_gap_seconds: 5.711 })])
    const html = renderToStaticMarkup(<ResultStory data={data} />)
    expect(html).toContain('Rider 1 is classified first.')
    expect(html).toContain('P2 is +3.845 s on elapsed time. P3 is +5.711 s to P1.')
    expect(html).toContain('Elapsed-time difference to P1 (s)')
    expect(html).toContain('#72')
    expect(html).toContain('R2')
    expect(html).toContain('Gap: 3.845')
    expect(html).toContain('not an official adjusted winning margin')
    expect(html.indexOf('P1</span>')).toBeLessThan(html.indexOf('P2</span>'))
  })

  it('keeps lapped, non-finish and missing gaps unscaled instead of substituting zero', () => {
    const data = analysis([row(1), row(2, { finish_gap_seconds: null, finish_gap_reason: 'Different completed lap count.', gap_first: '1 Lap' }),
      row(3, { status: 'DNF', finish_gap_seconds: null, finish_gap_reason: 'Not a classified finish.', gap_first: null })])
    const html = renderToStaticMarkup(<ResultStory data={data} />)
    expect(html.match(/>Unscaled</g)).toHaveLength(2)
    expect(html).toContain('Gap: 1 Lap')
    expect(html).toContain('Not a classified finish.')
    expect(html).not.toContain('P2 is +')
    expect(renderToStaticMarkup(<ResultStory data={analysis([row(2)])} />)).not.toContain('classified first')
  })

  it('does not turn a non-race or incomplete/tied source rank into a race-winning story', () => {
    const nonrace = renderToStaticMarkup(<ResultStory data={analysis([row(1), row(2)], 'Q2')} />)
    expect(nonrace).toContain('This is not a race finish')
    expect(nonrace).not.toContain('Podium positions')
    expect(nonrace).not.toContain('Elapsed-time difference')
    const tiedRank = renderToStaticMarkup(<ResultStory data={analysis([row(1), row(1, { rider_id: 'another' }), row(3)])} />)
    expect(tiedRank).toContain('The race classification.')
    expect(renderToStaticMarkup(<ResultStory data={analysis([row(1), row(2, { finish_gap_seconds: 0 })])} />)).toContain('equal elapsed times')
    expect(renderToStaticMarkup(<ResultStory data={analysis([])} />)).toContain('No classification is available')
  })
})

it('defaults disclosures closed on mobile and open on desktop without unmounting detail controls', () => {
  vi.stubGlobal('window', { matchMedia: () => ({ matches: true }) })
  const mobile = renderToStaticMarkup(<DetailSection title="full classification" note="24 rows"><input defaultValue="Marc" /></DetailSection>)
  expect(mobile).toContain('aria-expanded="false"')
  expect(mobile).toContain('Show full classification')
  expect(mobile).toContain('value="Marc"')
  vi.stubGlobal('window', { matchMedia: () => ({ matches: false }) })
  expect(renderToStaticMarkup(<DetailSection title="standings" note="24 rows">All rows</DetailSection>)).toContain('aria-expanded="true"')
  vi.unstubAllGlobals()
})
