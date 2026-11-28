import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import App, { ChampionshipContent, LapComparison, RiderProfileContent, SectorAnalysis } from './App'
import * as api from './api'
import type { Championship, Lap, RiderProfile } from './types'

function render(search: string) {
  vi.stubGlobal('window', { location: { search, pathname: '/paddock/' } })
  vi.stubGlobal('document', { documentElement: { dataset: { theme: 'light' } } })
  return renderToStaticMarkup(<App />)
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

it('keeps timing takeaways scoped to selected samples and separates theoretical sums from all-rider benchmarks', () => {
  const riders = [{ rider_id: 'one', rider: 'One Rider', number: 1 }, { rider_id: 'two', rider: 'Two Rider', number: 2 }]
  const lap = (rider_id: string, lap_number: number, time: number, sectors: (number | null)[]): Lap => ({
    rider_id, rider: `${rider_id} Rider`, number: 1, lap_number, lap_seconds: time, sectors,
    speed_kmh: null, is_pit: false, run_number: 1, front_tyre: null, rear_tyre: null,
  })
  const laps = [lap('one', 1, 100, [20, 25, 30, 25]), lap('one', 2, 102, [21, 24, 31, 26]),
    lap('two', 4, 104, [21, 25, 30, 25]), lap('two', 5, 106, [22, 26, 31, 26])]
  const scope = 'Example / Race; pit laps excluded; slow laps included'
  const pace = renderToStaticMarkup(<LapComparison laps={laps} riders={riders} theme="dark" scope={scope} />)
  expect(pace).toContain("One Rider&#x27;s median lap is 4.000s quicker than Two Rider&#x27;s")
  expect(pace).toContain('2 timed laps · lap-number span 4–5')
  expect(pace).toContain('not matched-lap or causal pace superiority')
  expect(pace).toContain(scope)
  const sector = renderToStaticMarkup(<SectorAnalysis laps={laps}
    allLaps={[...laps, lap('other', 1, 90, [19, 23, 29, 24])]} riders={riders} scope={scope} />)
  expect(sector).toContain("One Rider&#x27;s best-sector sum is 2.000s lower")
  expect(sector).toContain('Theoretical sums can combine different laps, not actual completed laps')
  expect(sector).toContain('including those not selected')
  expect(sector).toContain('Session best 19.000s')
  expect(sector).toContain('2 included laps')
})

describe('category selector and navigation', () => {
  it('exposes Data analysis in the always-visible top bar', () => {
    const markup = render('?clawpilotTheme=dark')
    const header = markup.slice(markup.indexOf('<header'), markup.indexOf('</header>'))
    expect(header).toContain('class="streamlit-link" href="https://motogp-data.com" target="_blank" rel="noreferrer"')
    expect(header).toContain('Data analysis')
    expect(header).toContain('Open Data analysis in a new tab')
  })

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
    expect(render('?view=championship')).toContain('<option value="premier" selected="">MotoGP / 500cc</option>')
    const markup = render('?category=unsupported')
    expect(markup).toContain('This category key is unsupported')
    expect(markup).toContain('aria-label="Category"')
    expect(markup).not.toContain('Loading race data')
  })

  describe('rider-first entry', () => {
    it('opens Marc on a bare or theme-only URL without season controls', () => {
      const spy = vi.spyOn(api, 'useResource').mockReturnValue({ key: '', data: null, error: null, loading: true, retry: () => {} })
      const markup = render('?clawpilotTheme=dark')
      expect(markup).toContain('The riders')
      expect(markup).toContain('Rider stories')
      expect(markup).not.toContain('aria-label="Season"')
      expect(markup).not.toContain('aria-label="Category"')
      expect(spy).toHaveBeenCalledWith('/api/riders/f55b433d-38b8-4d1d-bb3a-a709c82a0260')
      expect(markup).toContain('Find a rider')
    })

    it('gives a standings-only historical rider two charts without claiming zero race results', () => {
      const season = { season: 1970, category: '350cc' as const, gp_appearances: 0, gp_wins: 0, gp_podiums: 0,
        sprint_wins: 0, sprint_appearances: 0, position: 1, points: 9, is_final: true, source_url: 'https://example.com' }
      const data: RiderProfile = {
        rider: { rider_id: 'ago', rider: 'Giacomo Agostini', number: null }, headline: 'A remarkable rider.', summary: 'Official championship-winning seasons.',
        totals: { titles: 1, gp_appearances: 0, gp_wins: 0, gp_podiums: 0, sprint_appearances: 0, sprint_wins: 0 },
        first_season: 1970, latest_season: 1970, best_season: null, seasons: [season], titles: [season], venues: [],
      }
      const html = renderToStaticMarkup(<RiderProfileContent data={data} params={new URLSearchParams('clawpilotTheme=dark')} theme="dark" />)
      expect(html.match(/data-rider-chart=/g)).toHaveLength(2)
      expect(html).toContain('>TITLES</span>')
      expect(html).toContain('view=championship&amp;season=1970&amp;category=350cc&amp;clawpilotTheme=dark')
      expect(html).toContain('The championship finishing record')
      expect(html).not.toContain('0 recorded GP wins')
      expect(html).not.toContain('verification required')
      expect(html).toContain('class="identity-number"></span>')
      expect(html).not.toContain('ghost-number')
      const nonChampion = renderToStaticMarkup(<RiderProfileContent data={{ ...data, totals: { ...data.totals, titles: 0 },
        seasons: [{ ...season, position: 5 }], titles: [] }} params={new URLSearchParams()} theme="dark" />)
      expect(nonChampion).toContain('SEASON RECORDS</span><div class="recovery-value">1</div>')
      expect(nonChampion).not.toContain('RECORDED GP APPEARANCES')
    })

    it('leads with race achievements instead of an incomplete title count', () => {
      const title = { season: 2012, category: 'intermediate' as const, gp_appearances: 17, gp_wins: 9, gp_podiums: 14,
        sprint_wins: 0, sprint_appearances: 0, position: 1, points: 328, is_final: true, source_url: 'https://example.com' }
      const data: RiderProfile = {
        rider: { rider_id: 'rider', rider: 'A Rider', number: 93 }, headline: 'At the sharp end.', summary: 'A winning career.',
        totals: { titles: 1, gp_appearances: 35, gp_wins: 15, gp_podiums: 30, sprint_appearances: 0, sprint_wins: 0 },
        first_season: 2012, latest_season: 2013, best_season: title,
        seasons: [title, { ...title, season: 2013, category: 'premier', position: null, is_final: false, source_url: null }],
        titles: [title], venues: [{ venue: 'Circuit', appearances: 2, wins: 1, podiums: 2 }],
      }
      const html = renderToStaticMarkup(<RiderProfileContent data={data} params={new URLSearchParams()} theme="dark" />)
      const heading = html.slice(html.indexOf('<h1'), html.indexOf('</h1>'))
      expect(heading).toContain('aria-label="Rider number 93">#93</span>')
      expect(heading).toContain('A Rider.')
      expect(html).not.toContain('ghost-number')
      expect(html).toContain('GP WINS</span><div class="recovery-value">15</div>')
      expect(html).not.toContain('OFFICIAL TITLES RECORDED')
      expect(html).toContain('TITLE SEASONS')
      expect(html).toContain('>GP APPEARANCES</span>')
      expect(html).toContain('2012<span>Moto2</span>')
      expect(html).toContain('2013 / MotoGP')
      expect(html).not.toContain('Moto2 / 250cc')
      expect(html).not.toContain('MotoGP / 500cc')
    })

    it('distinguishes Q2 pole wins, evidenced zero and unavailable qualifying coverage', () => {
      const season = { season: 2025, category: 'premier' as const, gp_appearances: 10, gp_wins: 1, gp_podiums: 2,
        sprint_wins: 0, sprint_appearances: 0, position: 2, points: 150, is_final: true, source_url: null }
      const data: RiderProfile = {
        rider: { rider_id: 'rider', rider: 'A Rider', number: 7 }, headline: 'A career.', summary: 'Results.',
        totals: { titles: 0, gp_appearances: 40, gp_wins: 4, gp_podiums: 8, sprint_appearances: 0, sprint_wins: 0 },
        first_season: 2012, latest_season: 2025, best_season: season, titles: [], venues: [],
        seasons: [
          { ...season, gp_poles: 3, gp_poles_q2_events: 8, gp_poles_method: 'recorded_q2_wins' },
          { ...season, season: 2024, gp_poles: 0, gp_poles_q2_events: 2, gp_poles_method: 'recorded_q2_wins' },
          { ...season, season: 2012, gp_poles: null, gp_poles_q2_events: 0, gp_poles_method: 'recorded_q2_wins' },
          { ...season, season: 2023 },
        ],
      }
      const html = renderToStaticMarkup(<RiderProfileContent data={data} params={new URLSearchParams()} theme="dark" />)
      expect(html).toContain('>Q2 poles</th>')
      expect(html).toContain('title="8 available classified Q2 events for this rider; imports may be partial">3</td>')
      expect(html).toContain('title="2 available classified Q2 events for this rider; imports may be partial">0</td>')
      expect(html.match(/title="No supported classified Q2 evidence available">—<\/td>/g)).toHaveLength(2)
      expect(html).toContain('MotoGP from 2013 and Moto2/Moto3 from 2019')
      expect(html).toContain('not complete historical or penalty-adjusted')
    })
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
    const identity = renderToStaticMarkup(<ChampionshipContent data={{
      ...data, standings: data.standings.map((row, i) => ({ ...row, number: i === 0 ? 46 : null })),
    }} category="350cc" theme="dark" />)
    const storyRider = identity.slice(identity.indexOf('class="story-rider"'), identity.indexOf('<h2 id="season-story-title"'))
    expect(storyRider).toContain('>#46</span>')
    expect(storyRider).toContain('Giacomo Agostini')
    expect(storyRider).toContain('view=riders')
    expect(identity).not.toContain('ghost-number')
    expect(markup).not.toContain('role="alert"')
    expect(markup).not.toContain('Period scoring or source discrepancies')
    expect(markup).not.toContain('need verification')
    expect(markup).not.toContain('Verification required')
    expect(markup).not.toContain('source verification required')
    expect(markup).toContain('>CHAMPION</span>')
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

  it('identifies independently corrected points and preserves the no-margin guard', () => {
    const data: Championship = {
      season: 1970, category: '350cc', standings_source: 'official', is_final: true,
      official_points_inconsistent: true, points_warning: 'Unresolved official source discrepancy',
      points_correction: { note: 'Two independently sourced corrections; other totals remain unverified.',
        source_url: 'https://en.wikipedia.org/wiki/1970_Grand_Prix_motorcycle_racing_season',
        corroborating_url: 'https://www.lequipe.fr/Moto/1970/moto-350cc-classement.html' },
      external_sources_used: false, rounds: [], gp_results: 0, weekends: 0,
      scoring_sessions: 0, comeback: null,
      standings: ['Agostini', 'Carruthers', 'Pasolini'].map((rider, index) => ({
        rider, rider_id: rider, number: null, position: index + 1,
        points: [90, 58, 46][index], gap: null, wins: null, podiums: null,
        team: null, constructor: 'Bike', series: [],
      })),
      story: { kind: 'standings', headline: 'Champion', accent: 'Official rank',
        summary: 'Official ranks with corrections.', metric_label: 'OFFICIAL RANK',
        metric: 1, metric_note: 'Official champion rank', context_url: null },
    }
    const markup = renderToStaticMarkup(<ChampionshipContent data={data} category="350cc" theme="dark" />)
    for (const points of [90, 58, 46]) expect(markup).toContain(`class="strong numeric">${points}</td>`)
    expect(markup).toContain('Two independently sourced corrections')
    expect(markup).toContain('L&#x27;Équipe')
    expect(markup).not.toContain('historical source points')
    expect(markup).not.toContain('LEAD OVER SECOND')
    expect(markup.match(/class="muted numeric">—<\/td>/g)).toHaveLength(3)
  })
})
