import { describe, expect, it } from 'vitest'
import { appPath } from './paths'
import { categories, categoryPath, navigationPath, selectedCategory, selectedSeason, selectionParams } from './selection'

describe('category selection', () => {
  it('defaults only an absent category and rejects unsupported or inherited keys', () => {
    expect(selectedCategory(null)).toBe('premier')
    for (const key of Object.keys(categories)) expect(selectedCategory(key)).toBe(key)
    for (const key of ['', 'Moto2', 'constructor', '__proto__']) expect(selectedCategory(key)).toBeNull()
    expect(Object.keys(categories)).toEqual(['premier', 'intermediate', 'lightweight', '350cc', '50cc', '80cc'])
  })

  it('drops dependent selections on category or season change but preserves view and theme', () => {
    const params = new URLSearchParams('category=premier&season=2026&event=gp&session=race&view=laps&clawpilotTheme=dark')
    const next = selectionParams(params, { category: '80cc' })
    expect(next.toString()).toBe('category=80cc&view=laps&clawpilotTheme=dark')
    expect(params.get('session')).toBe('race')
    const year = selectionParams(params, { season: '1984' })
    expect(year.get('category')).toBe('premier')
    expect(year.has('event')).toBe(false)
    expect(year.has('session')).toBe(false)
    expect(selectionParams(params, { event: 'another' }).has('session')).toBe(false)
    expect(selectionParams(params, { event: 'gp', session: 'other' }).get('session')).toBe('other')
    expect(selectionParams(params, { view: 'results' }).get('session')).toBe('race')
  })

  it('binds every resource URL and keeps root and native paddock routing', () => {
    for (const path of ['/api/seasons', '/api/events?season=1969', '/api/events/gp/sessions', '/api/sessions/race/analysis', '/api/championship?season=1969']) {
      const scoped = categoryPath(path, '50cc')
      expect(new URL(scoped, 'https://example.com').searchParams.get('category')).toBe('50cc')
      expect(appPath(scoped, '/paddock/')).toBe(`/paddock${scoped}`)
      expect(appPath(scoped, '/')).toBe(scoped)
    }
    expect(categoryPath('/api/championship?season=1969&category=premier', '350cc'))
      .toBe('/api/championship?season=1969&category=350cc')
  })

  it('keeps an explicitly requested no-data season instead of silently crossing eras', () => {
    expect(selectedSeason(new URLSearchParams('season=2026'), [1984])).toBe(2026)
    expect(selectedSeason(new URLSearchParams(), [1989, 1984])).toBe(1989)
    expect(selectedSeason(new URLSearchParams('season=invalid'), [1984])).toBe(1984)
    expect(selectedSeason(new URLSearchParams(), [])).toBeUndefined()
  })

  it('keeps deep-linked category, season, session and theme when opening a navigation link', () => {
    const params = new URLSearchParams('category=80cc&season=1984&event=gp&session=race&clawpilotTheme=dark')
    const link = navigationPath(params, 'championship')
    const url = new URL(link, 'https://example.com/paddock/')
    expect(url.pathname).toBe('/paddock/')
    expect(url.searchParams.get('category')).toBe('80cc')
    expect(url.searchParams.get('season')).toBe('1984')
    expect(url.searchParams.get('session')).toBe('race')
    expect(url.searchParams.get('clawpilotTheme')).toBe('dark')
    expect(navigationPath(new URLSearchParams(), 'laps')).toContain('category=premier')
  })
})
