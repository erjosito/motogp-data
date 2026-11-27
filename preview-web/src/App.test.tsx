import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import App from './App'

function render(search: string) {
  vi.stubGlobal('window', { location: { search, pathname: '/paddock/' } })
  vi.stubGlobal('document', { documentElement: { dataset: { theme: 'light' } } })
  return renderToStaticMarkup(<App />)
}

afterEach(() => vi.unstubAllGlobals())

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
})
