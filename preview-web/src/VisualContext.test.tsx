import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { CircuitGraphic, NumberArtworkAccent, NumberMark, RiderIdentity, RiderNumber, RiderVisualContext } from './VisualContext'
import * as api from './api'
import type { CircuitContextData, RiderEnrichment } from './VisualContext'

const rider = { rider_id: 'marc', rider: 'Marc Marquez', number: 93 }
const enrichment: RiderEnrichment = {
  status: 'available', profile: { rider_id: 'marc',
    biography: { birth_date: '1993-02-17', birth_city: 'Cervera', birth_country: 'Spain', height_cm: 169 },
    source: { source_url: 'https://example.com/facts', retrieved_at: '2026-11-27T00:00:00Z' } },
}
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('rider visual context', () => {
  it('uses only selected artwork for the noninteractive decorative accent, never a plain-number fallback', () => {
    vi.stubGlobal('window', { location: { pathname: '/paddock/' } })
    const html = renderToStaticMarkup(<NumberArtworkAccent data={{ artwork: [
      { season: 2011, category: 'Moto2', number: 93, url: '/api/numbers/old', source_url: 'https://example.com/art' },
      { season: 2024, category: 'MotoGP', number: 93, url: '/api/numbers/latest', source_url: 'https://example.com/art' },
    ] }} />)
    expect(html).toContain('class="number-artwork-accent" aria-hidden="true"')
    expect(html).toContain('src="/paddock/api/numbers/latest" alt="" draggable="false"')
    expect(html).not.toContain('/api/numbers/old')
    expect(html).not.toContain('aria-label')
    expect(html).not.toContain('<a ')
    expect(renderToStaticMarkup(<NumberArtworkAccent data={{ artwork: [] }} />)).toBe('')
    expect(renderToStaticMarkup(<NumberArtworkAccent />)).toBe('')
  })
  it('requests stable rider identity art even when the classification number is missing', () => {
    vi.stubGlobal('window', { location: { pathname: '/paddock/' } })
    const request = vi.spyOn(api, 'useResource').mockReturnValue({
      key: 'identity', loading: false, error: null, retry: () => {}, data: { artwork: [{
        season: 2024, category: 'MotoGP', number: 93, source_url: 'https://example.com/art',
        url: '/api/riders/marc/number-identity/image',
      }] },
    })
    const html = renderToStaticMarkup(<RiderNumber rider={{ ...rider, number: null }} season={1970} category="350cc" fallback={null} />)
    expect(request).toHaveBeenCalledWith('/api/riders/marc/number-identity')
    expect(html).toContain('<img')
    expect(html).toContain('2024 MotoGP design')
    expect(html).toContain('2024 · MotoGP · #93')
  })
  it('uses the latest matching career number design in place of text, preserving its actual scope in credits', () => {
    vi.stubGlobal('window', { location: { pathname: '/paddock/' } })
    const html = renderToStaticMarkup(<NumberMark rider={rider} data={{ artwork: [{
      season: 2011, category: 'Moto2', number: 93, url: '/api/numbers/old', source_url: 'https://example.com/art',
    }, { season: 2024, category: 'MotoGP', number: 93, url: '/api/numbers/93', source_url: 'https://example.com/art' }] }} />)
    expect(html).toContain('/paddock/api/numbers/93')
    expect(html).not.toContain('/api/numbers/old')
    expect(html).toContain('2024 · MotoGP · #93')
    expect(html).toContain('Marc Marquez, number 93, 2024 MotoGP design')
    expect(html).not.toContain('<summary>')
    expect(html).not.toContain('aria-label="Rider number 93"')
  })
  it('uses the rider identity design independently of selected season, class and classification number', () => {
    vi.stubGlobal('window', { location: { pathname: '/paddock/' } })
    const item = { season: 2024, category: 'MotoGP', number: 93, url: '/api/numbers/93', source_url: 'https://example.com/art' }
    const number = (artwork = [item], season = 2024, category: 'premier' | 'intermediate' = 'premier') =>
      renderToStaticMarkup(<NumberMark rider={rider} data={{ artwork }} season={season} category={category} />)
    expect(number()).toContain('<img')
    for (const html of [number([item], 2026), number([item], 2024, 'intermediate'),
      number([{ ...item, number: 1 }]), number([item, { ...item, url: '/api/ambiguous' }])]) expect(html).toContain('<img')
    expect(number([])).toContain('aria-label="Rider number 93">#93')
    expect(renderToStaticMarkup(<NumberMark rider={{ ...rider, number: null }} data={{ artwork: [item] }} />))
      .toContain('<img')
    expect(renderToStaticMarkup(<NumberMark rider={{ ...rider, number: null }} data={{ artwork: [] }}
      fallback={<span>MM</span>} />)).toContain('<span>MM</span>')
  })
  it('keeps biography facts and sources without a photo, initials tile or reserved photo column', () => {
    const request = vi.spyOn(api, 'useResource').mockReturnValue({
      key: 'biography', loading: false, error: null, retry: () => {}, data: enrichment,
    })
    const html = renderToStaticMarkup(<RiderVisualContext rider={rider} />)
    expect(html).toContain('Feb 17, 1993')
    expect(html).toContain('Cervera, Spain')
    expect(html).toContain('not a historical measurement')
    expect(html).toContain('Biography source')
    expect(html).not.toContain('<img')
    expect(html).not.toContain('rider-portrait')
    expect(html).not.toContain('rider-initials')
    expect(html).not.toContain('<figcaption')
    expect(request).toHaveBeenCalledTimes(1)
    expect(request).toHaveBeenCalledWith('/api/riders/marc/enrichment')
  })

  it('does not replace missing biography facts with a photo placeholder or another rider’s facts', () => {
    const html = renderToStaticMarkup(<RiderIdentity rider={rider} />)
    expect(html).not.toContain('<img')
    expect(html).not.toContain('initials')
    expect(html).not.toContain('Hometown')
    const other = renderToStaticMarkup(<RiderIdentity rider={{ ...rider, rider_id: 'other', rider: 'Other Rider' }}
      enrichment={enrichment} />)
    expect(other).not.toContain('<img')
    expect(other).not.toContain('Cervera')
    expect(other).not.toContain('initials')
  })
})

describe('circuit reference graphic', () => {
  const data: CircuitContextData = { status: 'available', circuit: {
    id: 'jerez', name: 'Jerez', length_km: 4.423, turns: 13, reference_season: 2026,
    facts_source: 'https://example.com/facts', facts_verified: '2026-11-27',
    outline_source: 'https://www.openstreetmap.org/way/1', outline_license_url: 'https://opendatacommons.org/licenses/odbl/1-0/',
    outline: [[16, 16], [304, 16], [16, 304], [16, 16]],
  } }
  it('labels historical selections as current reference without imaginary sectors', () => {
    const html = renderToStaticMarkup(<CircuitGraphic data={data} season={1967} />)
    expect(html).toContain('not a reconstruction of the 1967 track')
    expect(html).toContain('not a sector map')
    expect(html).toContain('OpenStreetMap contributors')
    expect(html).toContain('ODbL 1.0')
    expect(html).toContain('No sector boundaries, start line or direction inferred.')
    expect(html).toContain('4.423')
  })
  it('does not fabricate a graphic for an uncollected venue', () => {
    expect(renderToStaticMarkup(<CircuitGraphic data={{ status: 'not_collected', circuit: null }} season={2026} />)).toBe('')
  })
})
