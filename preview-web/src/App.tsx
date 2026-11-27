import { Component, lazy, Suspense, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import {
  ArrowDownRight, ArrowRight, ArrowUpRight, Check, ChevronRight, Flag,
  Gauge, Layers3, Menu, Moon, RefreshCw, Sun, Timer, Trophy,
} from 'lucide-react'
import { useResource } from './api'
import { categories, categoryPath, navigationPath, selectedCategory, selectedSeason, selectionParams } from './selection'
import type { Category } from './selection'
import { bestSectors, cleanLaps, lapTime, MARC_ID, median, riderStyle, signed } from './data'
import type { Analysis, Championship, GrandPrix, Lap, Rider, Session } from './types'
import type { LineSeries } from './PlotChart'
import './App.css'

const Chart = lazy(() => import('./PlotChart'))
const classicUrl = import.meta.env.VITE_CLASSIC_URL || 'https://motogp-data.com'
const views = [
  { id: 'championship', name: 'The title fight', icon: Trophy, detail: 'The season, in perspective' },
  { id: 'results', name: 'Session results', icon: Flag, detail: 'Every position. Every point.' },
  { id: 'laps', name: 'Lap comparison', icon: Timer, detail: 'Find the difference in pace' },
  { id: 'sectors', name: 'Sector analysis', icon: Layers3, detail: 'Where the time is won' },
] as const
type View = typeof views[number]['id']
type UpdateLocation = (values: Record<string, string | null>) => void

function dateLabel(value: string | null | undefined) {
  return value ? new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short' }).format(new Date(value)) : '\u2014'
}

function RiderName({ rider }: { rider: Rider }) {
  const token = riderStyle(rider.rider_id).token
  return <span className="rider-name">
    <span className="rider-number" style={{ color: `var(${token})` }}>{rider.number ?? '\u2014'}</span>
    <span>{rider.rider}</span>
  </span>
}

function Loading({ label = 'Loading race data' }: { label?: string }) {
  return <div className="loading" role="status"><span className="spinner" />{label}</div>
}

function DataState({ resource, empty }: { resource: { error: string | null; retry: () => void }; empty?: string }) {
  return <div className="data-state" role={resource.error ? 'alert' : 'status'}>
    <Flag size={28} aria-hidden="true" />
    <h3>{resource.error ? 'The data is taking a pit stop' : 'Nothing recorded here yet'}</h3>
    <p>{resource.error ?? empty}</p>
    {resource.error && <button className="button" onClick={resource.retry}><RefreshCw size={15} />Try again</button>}
  </div>
}

class ChartBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(error: Error) { console.error('Chart loading failed', error) }
  render() {
    return this.state.failed
      ? <DataState resource={{ error: 'The chart could not be loaded. Recorded values remain available in the tables.', retry: () => window.location.reload() }} />
      : this.props.children
  }
}

function Plot({ series, yTitle, theme, baseline, timing, height }: {
  series: LineSeries[]; yTitle: string; theme: string; baseline?: boolean; timing?: boolean; height?: number
}) {
  return <ChartBoundary><Suspense fallback={<Loading label="Preparing chart" />}>
    <Chart series={series} yTitle={yTitle} theme={theme} baseline={baseline} timing={timing} height={height} />
  </Suspense></ChartBoundary>
}

function Stat({ label, value, note }: { label: string; value: string | number; note: string }) {
  return <div className="stat"><span className="eyebrow">{label}</span><strong>{value}</strong><span>{note}</span></div>
}

function ChampionshipPage({ season, category, theme }: { season: number; category: Category; theme: string }) {
  const resource = useResource<Championship>(categoryPath(`/api/championship?season=${season}`, category))
  const data = resource.data
  if (resource.error) return <DataState resource={resource} />
  if (!data) return <Loading />
  if (!data.standings.length) return <><div className="page-heading"><div><p className="eyebrow">{season} / SEASON STORY</p><h1>{data.story.headline}</h1><p>{data.story.accent}</p></div></div>
    <DataState resource={resource} empty={data.story.summary} /></>

  const story = data.comeback
  const featured = category === 'premier' && season === 2026 && story?.verified_102
  const official = data.standings_source === 'official'
  const final = official && data.is_final
  const officialLabel = final ? 'Official final standings' : 'Official standings to date'
  const narrative = data.story
  const marc = data.standings.find((rider) => rider.rider_id === MARC_ID)
  const leader = data.standings[0]
  const last = data.rounds.at(-1)
  const gap = story ? story.current_margin : 0
  const marginLabel = gap > 0 ? `${gap} points ahead` : gap === 0 ? 'Level on points' : `${-gap} points behind`
  return <>
    <div className="page-heading"><div><p className="eyebrow">THE BIG PICTURE</p><h1>The title fight.</h1>
      <p>Not just the standings. The story behind them.</p></div>
      <span className="quiet-badge"><span className="status-dot" />{official ? `${season} · ${officialLabel}` : `Through ${last?.event} · ${dateLabel(last?.date)}`}</span>
    </div>

    <section className="story-card" aria-labelledby="season-story-title">
      <div className="story-intro">
        <div className="story-copy">
          <p className="eyebrow accent">{season} / SEASON STORY</p>
          <h2 id="season-story-title">{narrative.headline}<br /><span>{narrative.accent}</span></h2>
          <p>{narrative.summary}</p>
          {narrative.context_url && <a className="classic-link" href={narrative.context_url} target="_blank" rel="noreferrer">The injury-recovery story · MotoGP<ArrowUpRight size={16} /></a>}
          <span className="verification verified">
            <Check size={14} />
            {featured ? '102-point deficit verified in race results' : official ? `Based on ${officialLabel.toLowerCase()}` : 'Based on imported race results · coverage shown below'}
          </span>
        </div>
        <div className="comeback-score">
          <span className="ghost-number" aria-hidden="true">{featured ? '93' : leader.number ?? season}</span>
          <span className="eyebrow">{narrative.metric_label}</span>
          <div className="recovery-value">{narrative.metric}<ArrowUpRight size={35} aria-hidden="true" /></div>
          <p>{narrative.metric_note}</p>
          <div className="mini-stats"><div><strong>P{featured && marc ? marc.position : leader.position}</strong><span>{official ? (final ? 'official final rank' : 'official rank to date') : 'in the imported standings'}</span></div><div><strong>{featured && marc ? marc.points : leader.points}</strong><span>points earned</span></div></div>
        </div>
      </div>
      {featured && story && <div className="story-chart">
        <div className="section-heading"><div><h3>The comeback curve</h3><p>Points relative to the strongest title rival after every Sprint and Grand Prix.</p></div><span className="chart-key"><i />Marc Márquez</span></div>
        <Plot series={[{
          id: MARC_ID, name: 'Marc Márquez',
          x: story.history.map((point) => point.label),
          y: story.history.map((point) => point.margin),
        }]} yTitle="Points vs nearest rival" theme={theme} baseline height={320} />
        <div className="timeline-milestones">
          <div><ArrowDownRight size={17} /><span><b>THE LOW / {story.low.event}</b><strong>{-story.max_deficit} pts</strong></span></div>
          <div><span className="timeline-rule" /></div>
          <div><ArrowUpRight size={17} /><span><b>LATEST / {last?.event}</b><strong>{marginLabel}</strong></span></div>
        </div>
        <details className="source-details"><summary>Explore the points behind the curve</summary>
          <div className="table-scroll"><table><thead><tr><th>Source session</th><th>Márquez points</th><th>Margin to nearest rival</th></tr></thead>
            <tbody>{story.history.map((point) => <tr key={point.session_id}><td>{point.label}</td><td>{point.points}</td><td>{signed(point.margin)} pts</td></tr>)}</tbody></table></div>
        </details>
      </div>}
    </section>

    <div className="stats-grid">
      <Stat label={final ? 'OFFICIAL CHAMPION' : 'CHAMPIONSHIP LEADER'} value={leader.rider} note={`${leader.points} points${leader.wins == null ? '' : ` · ${leader.wins} imported Grand Prix wins`}`} />
      <Stat label={featured ? 'MÁRQUEZ / THE GAP' : 'LEAD OVER SECOND'} value={featured ? marginLabel : `${data.standings[1]?.gap ?? 0} pts`} note={featured ? 'Relative to the closest title rival' : official ? `From ${officialLabel.toLowerCase()}` : 'Calculated from imported results'} />
      <Stat label={official ? 'OFFICIAL CLASSIFICATION' : 'SCORING WEEKENDS'} value={official ? data.standings.length : data.weekends} note={official ? `Riders in the ${final ? 'preserved final' : 'current official'} standings` : `${data.gp_results} GP race results · ${data.scoring_sessions} scoring sessions`} />
    </div>

    <div className="championship-grid">
      <section className="panel"><div className="section-heading"><div><p className="eyebrow">THE ORDER</p><h2>Championship standings</h2></div><span className="quiet-badge">{season}</span></div>
        <div className="table-scroll"><table className="standings-table">
          <thead><tr><th>Pos</th><th>Rider</th><th>Pts</th><th>Gap</th><th>{official ? 'Imported GP wins' : 'Wins'}</th></tr></thead>
          <tbody>{data.standings.map((rider) => <tr key={rider.rider_id} className={featured && rider.rider_id === MARC_ID ? 'featured-row' : ''}>
            <td><span className={`position ${rider.position <= 3 ? 'top-position' : ''}`}>{String(rider.position).padStart(2, '0')}</span></td>
            <td><RiderName rider={rider} /><small>{rider.constructor || rider.team || 'Team not recorded'}</small></td>
            <td className="strong numeric">{rider.points}</td><td className="muted numeric">{rider.gap ? `−${rider.gap}` : '—'}</td><td className="numeric">{rider.wins ?? '—'}</td>
          </tr>)}</tbody></table></div>
        <p className="panel-note">{official ? `${officialLabel}. Official positions and decimal points are preserved independently of race points. Wins, where shown, count only the ${data.gp_results} imported scoring GP races; missing historical wins are not inferred.` : 'GP + Sprint points. Wins and GP finish countback exclude sessions awarding no points. Source adjustments outside the database are not included.'}</p>
      </section>
      <section className="panel progression-panel"><div className="section-heading"><div><p className="eyebrow">THE TRAJECTORY</p><h2>Points on the board</h2><p>The leading five riders, session by session.</p></div></div>
        {official ? <p className="notice">The official table is independent of imported race points. No cumulative curve is inferred from official totals{final ? '; the final official table is authoritative' : '; this season is not marked final'}.</p> : <Plot series={data.standings.slice(0, 5).map((rider) => ({
          id: rider.rider_id, name: rider.rider, x: data.rounds.map((round) => round.label), y: rider.series,
        }))} yTitle="Championship points" theme={theme} height={400} />}
        <div className="context-note"><Trophy size={22} /><div><strong>{leader.rider} {official ? 'is ranked first' : 'leads'} on {leader.points} points.</strong><p>{featured ? 'The gap chart above tracks Márquez against whichever rival is strongest at each point, not just today’s runner-up.' : 'The headline is grounded in this season’s available evidence. Visit Classic for the complete analysis suite.'}</p></div></div>
      </section>
    </div>
    {data.external_sources_used && <p className="notice">External archive evidence is used in the imported race classifications. Missing timing and historical race points are not inferred.</p>}
    {official && leader.source_url && <a className="classic-link" href={leader.source_url} target="_blank" rel="noreferrer">Official championship source<ArrowUpRight size={16} /></a>}
  </>
}

function ResultTable({ data }: { data: Analysis }) {
  const [search, setSearch] = useState('')
  const results = data.results.filter((rider) => `${rider.rider} ${rider.team ?? ''}`.toLowerCase().includes(search.toLowerCase()))
  const times = data.laps.filter((lap) => !lap.is_pit && lap.lap_seconds != null).map((lap) => lap.lap_seconds!)
  const classificationTimes = data.results.flatMap((result) => result.best_lap_seconds == null ? [] : [result.best_lap_seconds])
  const recordedTimes = [...times, ...classificationTimes]
  const fastest = recordedTimes.length ? Math.min(...recordedTimes) : null
  const winner = data.results.find((result) => result.position === 1)
  return <>
    <div className="stats-grid">
      <Stat label="TOP CLASSIFIED" value={winner?.rider ?? 'Not recorded'} note={winner?.constructor ?? data.session.session_label} />
      <Stat label="FASTEST RECORDED LAP" value={lapTime(fastest)} note="From classification and non-pit timing data" />
      <Stat label="RIDERS CLASSIFIED" value={data.results.length} note={`${data.laps.length.toLocaleString()} lap records available`} />
    </div>
    <section className="panel"><div className="section-heading"><div><p className="eyebrow">THE RESULT</p><h2>Classification</h2></div>
      <label className="search-label"><span className="sr-only">Search riders or teams</span><input type="search" placeholder="Find rider or team…" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
    </div>
      {!data.results.length ? <DataState resource={{ error: null, retry: () => {} }} empty="No classification has been recorded for this session." /> : <div className="table-scroll">
        <table className="results-table"><thead><tr><th>Pos</th><th>Rider / team</th><th>Laps</th><th>Time</th><th>Gap</th><th>Best lap</th><th>Top speed</th><th>Pts</th><th>Status</th></tr></thead>
          <tbody>{results.map((rider) => <tr key={rider.rider_id}>
            <td><span className={`position ${(rider.position ?? 99) <= 3 ? 'top-position' : ''}`}>{rider.position == null ? '—' : String(rider.position).padStart(2, '0')}</span></td>
            <td><RiderName rider={rider} /><small>{rider.team ?? rider.constructor ?? 'Not recorded'}</small>{rider.source_kind !== 'official-api' && <small>{rider.source_kind === 'external' ? 'External archive classification' : 'Official classification · externally augmented'}</small>}</td>
            <td className="numeric">{rider.total_laps ?? '—'}</td><td className="numeric">{rider.time_text || '—'}</td><td className="numeric muted">{rider.gap_first || '—'}</td>
            <td className="numeric">{lapTime(rider.best_lap_seconds)}</td><td className="numeric">{rider.top_speed == null ? '—' : `${rider.top_speed.toFixed(1)}`}</td><td className="strong numeric">{rider.points ?? '—'}</td><td><span className="status-label">{rider.status ?? '—'}</span></td>
          </tr>)}</tbody>
        </table>
        {!results.length && <p className="panel-note" role="status">No riders match “{search}”.</p>}
      </div>}
      <p className="panel-note">Speed in km/h. A dash means the source does not contain that value; no timing is inferred.</p>
    </section>
  </>
}

function LapComparison({ laps, riders, theme }: { laps: Lap[]; riders: Rider[]; theme: string }) {
  const series = riders.map((rider) => {
    const recorded = laps.filter((lap) => lap.rider_id === rider.rider_id)
    return {
      id: rider.rider_id, name: rider.rider, x: recorded.map((lap) => lap.lap_number),
      y: recorded.map((lap) => lap.lap_seconds), text: recorded.map((lap) => lapTime(lap.lap_seconds)),
    }
  })
  return <>
    <section className="panel"><div className="section-heading"><div><p className="eyebrow">THE PACE</p><h2>Every lap tells a story</h2><p>Lower is faster. Hover to compare recorded lap times.</p></div><Timer size={22} className="muted" /></div>
      {series.some((line) => line.x.length) ? <Plot series={series} yTitle="Lap time (seconds)" theme={theme} timing height={420} /> : <p className="panel-note" role="status">No recorded laps remain for these riders and filters.</p>}
    </section>
    <section className="panel"><div className="section-heading"><div><h2>Pace at a glance</h2><p>Calculated from the laps currently included above.</p></div></div>
      <div className="table-scroll"><table><thead><tr><th>Rider</th><th>Included laps</th><th>Best</th><th>Median</th><th>Spread*</th></tr></thead>
        <tbody>{riders.map((rider) => {
          const values = laps.filter((lap) => lap.rider_id === rider.rider_id).flatMap((lap) => lap.lap_seconds == null ? [] : [lap.lap_seconds])
          return <tr key={rider.rider_id}><td><RiderName rider={rider} /></td><td className="numeric">{values.length}</td><td className="numeric">{lapTime(values.length ? Math.min(...values) : null)}</td><td className="numeric">{lapTime(median(values))}</td><td className="numeric">{values.length ? `${(Math.max(...values) - Math.min(...values)).toFixed(3)}s` : '—'}</td></tr>
        })}</tbody></table></div>
      <p className="panel-note">*Spread is slowest minus fastest included lap. Missing lap records are not interpolated.</p>
    </section>
  </>
}

function SectorAnalysis({ laps, allLaps, riders }: { laps: Lap[]; allLaps: Lap[]; riders: Rider[] }) {
  const benchmark = bestSectors(allLaps)
  const rows = riders.map((rider) => ({ rider, sectors: bestSectors(laps.filter((lap) => lap.rider_id === rider.rider_id)) }))
  const deltas = rows.flatMap((row) => row.sectors.flatMap((value, index) => value == null || benchmark[index] == null ? [] : [value - benchmark[index]!]))
  const maximum = Math.max(0.001, ...deltas)
  const ideal = benchmark.every((value) => value != null) ? benchmark.reduce<number>((total, value) => total + (value ?? 0), 0) : null
  return <>
    <div className="stats-grid">
      <Stat label="THEORETICAL RECORDED BEST" value={lapTime(ideal)} note="Sum of the fastest recorded sectors; not an actual lap" />
      <Stat label="SECTORS RECORDED" value={`${benchmark.filter((value) => value != null).length} / 4`} note="Based on all riders using the current lap filters" />
      <Stat label="COMPARISON FIELD" value={riders.length} note="Selected riders with available timing records" />
    </div>
    <section className="panel"><div className="section-heading"><div><p className="eyebrow">FIND THE ADVANTAGE</p><h2>The sector picture</h2><p>Each rider’s best sector, compared with the best in the entire session.</p></div><span className="quiet-badge">Seconds</span></div>
      <div className="table-scroll"><table className="sector-table"><thead><tr><th>Rider</th>{benchmark.map((value, index) => <th key={index}><span>SECTOR {index + 1}</span><small>Session best {value == null ? '—' : `${value.toFixed(3)}s`}</small></th>)}<th>Theoretical lap</th></tr></thead>
        <tbody>{rows.map(({ rider, sectors }) => <tr key={rider.rider_id}><td><RiderName rider={rider} /></td>{sectors.map((value, index) => {
          const delta = value == null || benchmark[index] == null ? null : value - benchmark[index]!
          const strength = delta == null ? 0 : 7 + (delta / maximum) * 32
          return <td key={index}><div className={`sector-cell ${delta === 0 ? 'sector-best' : ''}`} style={{ backgroundColor: `color-mix(in srgb, var(--cp-accent) ${strength}%, var(--cp-surface))` }}>
            <strong>{value == null ? '—' : value.toFixed(3)}</strong><span>{delta == null ? 'Not recorded' : delta === 0 ? 'SESSION BEST' : `+${delta.toFixed(3)}`}</span>
          </div></td>
        })}<td className="numeric strong">{lapTime(sectors.every((value) => value != null) ? sectors.reduce<number>((total, value) => total + (value ?? 0), 0) : null)}</td></tr>)}</tbody>
      </table></div>
      <div className="heatmap-legend"><span>Smaller gap</span><i /><i /><i /><span>Larger gap</span></div>
      <p className="panel-note">Best sectors may come from different laps. The session benchmark includes unselected riders. Missing sectors remain blank rather than counting as zero.</p>
    </section>
  </>
}

function AnalysisPanel({ data, view, theme }: { data: Analysis; view: View; theme: string }) {
  const available = [...new Map(data.laps.map((lap) => [lap.rider_id, {
    rider_id: lap.rider_id, rider: lap.rider, number: lap.number,
  }])).values()]
  const ordered = [...available].sort((a, b) => {
    if (a.rider_id === MARC_ID) return -1
    if (b.rider_id === MARC_ID) return 1
    const rank = (rider: Rider) => data.results.find((result) => result.rider_id === rider.rider_id)?.position ?? 999
    return rank(a) - rank(b)
  })
  const [selected, setSelected] = useState<string[]>(() => ordered.slice(0, 3).map((rider) => rider.rider_id))
  const [excludePit, setExcludePit] = useState(true)
  const [excludeSlow, setExcludeSlow] = useState(true)
  if (view === 'results') return <ResultTable data={data} />
  if (!data.laps.length) return <DataState resource={{ error: null, retry: () => {} }} empty="Lap analysis is not available for this session. Results remain available; older events may not have timing PDFs." />
  const allLaps = cleanLaps(data.laps, excludePit, excludeSlow)
  const laps = allLaps.filter((lap) => selected.includes(lap.rider_id))
  const riders = ordered.filter((rider) => selected.includes(rider.rider_id))
  return <>
    <section className="rider-picker panel">
      <div className="section-heading"><div><h2>Choose your comparison</h2><p>{selected.length} selected · rider colors stay consistent across charts</p></div>
        <button className="text-button" onClick={() => setSelected(selected.length === ordered.length ? [] : ordered.map((rider) => rider.rider_id))}>{selected.length === ordered.length ? 'Clear selection' : 'Select all'}</button>
      </div>
      <div className="rider-chips">{ordered.map((rider) => <label key={rider.rider_id} className={`rider-chip ${selected.includes(rider.rider_id) ? 'selected' : ''}`}>
        <input type="checkbox" checked={selected.includes(rider.rider_id)} onChange={(event) => setSelected((previous) => event.target.checked ? [...previous, rider.rider_id] : previous.filter((id) => id !== rider.rider_id))} />
        <RiderName rider={rider} />
      </label>)}</div>
      <div className="lap-options">
        <label><input type="checkbox" checked={excludePit} onChange={(event) => setExcludePit(event.target.checked)} />Exclude pit laps</label>
        <label><input type="checkbox" checked={excludeSlow} onChange={(event) => setExcludeSlow(event.target.checked)} />Hide laps slower than 115% of each rider’s median</label>
        <span>{laps.length.toLocaleString()} laps included</span>
      </div>
    </section>
    {!riders.length ? <p className="selection-message" role="status">Select at least one rider to begin the comparison.</p>
      : view === 'laps' ? <LapComparison laps={laps} riders={riders} theme={theme} />
        : <SectorAnalysis laps={laps} allLaps={allLaps} riders={riders} />}
  </>
}

function SessionWorkspace({ season, category, params, update, view, theme }: {
  season: number; category: Category; params: URLSearchParams; update: UpdateLocation; view: View; theme: string
}) {
  const eventResource = useResource<GrandPrix[]>(categoryPath(`/api/events?season=${season}`, category))
  const events = eventResource.data ?? []
  const event = events.find((item) => item.event_id === params.get('event')) ?? events.at(-1)
  const sessionResource = useResource<Session[]>(event ? categoryPath(`/api/events/${event.event_id}/sessions`, category) : null)
  const sessions = sessionResource.data ?? []
  const session = sessions.find((item) => item.session_id === params.get('session')) ?? sessions.findLast((item) => item.session_type === 'RAC') ?? sessions.at(-1)
  const analysis = useResource<Analysis>(session ? categoryPath(`/api/sessions/${session.session_id}/analysis`, category) : null)
  const failed = [eventResource, sessionResource, analysis].find((resource) => resource.error)
  const viewInfo = views.find((item) => item.id === view)!
  const invalidEvent = params.has('event') && events.length > 0 && !events.some((item) => item.event_id === params.get('event'))
  const invalidSession = params.has('session') && sessions.length > 0 && !sessions.some((item) => item.session_id === params.get('session'))
  return <>
    <div className="page-heading"><div><p className="eyebrow">INSIDE THE WEEKEND</p><h1>{viewInfo.name}.</h1><p>{viewInfo.detail}</p></div></div>
    <div className="session-filters panel">
      <label>Grand Prix<select value={event?.event_id ?? ''} disabled={!events.length} onChange={(change) => update({ event: change.target.value, session: null })}>
        {!events.length && <option value="">No events available</option>}
        {events.map((item) => <option key={item.event_id} value={item.event_id}>{item.short_name} / {item.event_name}</option>)}
      </select></label>
      <label>Session<select value={session?.session_id ?? ''} disabled={!sessions.length} onChange={(change) => update({ event: event?.event_id ?? null, session: change.target.value })}>
        {!sessions.length && <option value="">No sessions available</option>}
        {sessions.map((item) => <option key={item.session_id} value={item.session_id}>{item.session_label}</option>)}
      </select></label>
    </div>
    {(invalidEvent || invalidSession) && <p className="notice" role="status">The requested {invalidEvent ? 'Grand Prix' : 'session'} is unavailable in this scope. Showing the latest available race.</p>}
    {event && session && <div className="event-strip"><div><strong>{event.circuit_name ?? event.event_name}</strong><span>{event.country_name} · {dateLabel(session.session_date)}</span></div><div>{session.weather && <span>{session.weather}</span>}{session.air_temp && <span>Air {session.air_temp}</span>}{session.ground_temp && <span>Track {session.ground_temp}</span>}</div></div>}
    {analysis.data?.results.some((row) => row.source_kind !== 'official-api') && <p className="notice">This classification includes verified external archive supplementation. Source labels identify supplemented and external-only rows; no missing timing is invented.</p>}
    <p className="notice" role="status">Timing limitation: cancellation flags are not yet stored. Recorded lap and sector comparisons may include cancelled times; they are not official valid-lap rankings.</p>
    {failed ? <DataState resource={failed} />
      : eventResource.loading || sessionResource.loading || analysis.loading ? <Loading />
        : !events.length || !sessions.length ? <DataState resource={{ error: null, retry: () => {} }} empty="No classified sessions have been imported for this season or event." />
          : analysis.data && <AnalysisPanel key={`${category}:${analysis.data.session.session_id}`} data={analysis.data} view={view} theme={theme} />}
  </>
}

export default function App() {
  const [params, setParams] = useState(() => new URLSearchParams(window.location.search))
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme ?? 'light')
  const [menuOpen, setMenuOpen] = useState(false)
  const category = selectedCategory(params.get('category'))
  const resource = useResource<number[]>(category ? categoryPath('/api/seasons', category) : null)
  const seasons = resource.data ?? []
  const season = selectedSeason(params, seasons)
  const view: View = views.find((item) => item.id === params.get('view'))?.id ?? 'championship'

  useEffect(() => {
    const onPopState = () => {
      const next = new URLSearchParams(window.location.search)
      setParams(next)
      const nextTheme = next.get('clawpilotTheme') ?? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
      document.documentElement.dataset.theme = nextTheme
      setTheme(nextTheme)
    }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const update: UpdateLocation = (values) => {
    const next = selectionParams(new URLSearchParams(window.location.search), values)
    window.history.pushState(null, '', `${window.location.pathname}?${next}`)
    setParams(next)
  }
  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    setTheme(next)
    update({ clawpilotTheme: next })
  }

  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to content</a>
    <aside className={`sidebar ${menuOpen ? 'menu-open' : ''}`}>
      <a className="brand" href={navigationPath(params, 'championship')} onClick={(event) => { event.preventDefault(); update({ view: 'championship' }) }}>
        <span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /></span><span>MotoGP<span className="brand-sub">RACE INTELLIGENCE</span></span>
      </a>
      <button className="mobile-menu icon-button" aria-label="Toggle navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}><Menu size={23} /></button>
      <div className="sidebar-content">
        <p className="nav-caption">THE PADDOCK</p>
        <nav aria-label="Main navigation">{views.map(({ id, name, icon: Icon }) => <a key={id} href={navigationPath(params, id)} className={view === id ? 'active' : ''} aria-current={view === id ? 'page' : undefined}
          onClick={(event) => { event.preventDefault(); update({ view: id }); setMenuOpen(false) }}>
          <Icon size={19} /><span>{name}</span>{view === id && <ChevronRight size={15} className="nav-chevron" />}
        </a>)}</nav>
        <div className="sidebar-bottom"><span className="preview-tag">NEW ENGINE / PREVIEW</span><h3>A new way to read the race.</h3><p>Four focused tools. The complete suite and all languages are still in Classic.</p>
          <a className="classic-link" href={classicUrl} target="_blank" rel="noreferrer">Open Classic<ArrowUpRight size={16} /></a>
          <div className="sidebar-foot"><Gauge size={14} /><span>Read-only · Sources labeled</span></div>
        </div>
      </div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><div className="breadcrumb"><span>{category ? categories[category] : 'Unknown category'}</span><ChevronRight size={13} /><strong>{season ?? 'Season'}</strong></div>
        <div className="topbar-actions">
          <label className="season-select category-select"><span>CATEGORY</span><select aria-label="Category" value={category ?? ''} onChange={(event) => update({ category: event.target.value })}>
            {!category && <option value="" disabled>Unsupported category</option>}
            {Object.entries(categories).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select></label>
          <label className="season-select"><span>SEASON</span><select aria-label="Season" value={season ?? ''} disabled={!seasons.length} onChange={(event) => update({ season: event.target.value })}>
          {season && !seasons.includes(season) && <option value={season}>{season} · not imported</option>}
          {!seasons.length && <option value="">—</option>}{seasons.map((year) => <option key={year} value={year}>{year}</option>)}
        </select></label>
          <button className="icon-button" aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} onClick={toggleTheme}>{theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}</button>
          <button className="icon-button" aria-label="Refresh data" onClick={() => window.location.reload()}><RefreshCw size={17} /></button>
        </div>
      </header>
      <main id="main">
        {category && params.has('season') && seasons.length > 0 && Number(params.get('season')) !== season && <p className="notice" role="status">The requested season value is invalid. Showing {season}.</p>}
        {!category ? <DataState resource={{ error: null, retry: () => {} }} empty="This category key is unsupported. Choose a Grand Prix category above." />
          : resource.error ? <DataState resource={resource} /> : resource.loading ? <Loading />
          : !season || !seasons.includes(season) ? <DataState resource={resource} empty={`No data has been imported for ${categories[category]}${season ? ` in ${season}` : ''}. This is not a zero-point result. Choose another season or category; extinct classes remain separate.`} />
            : view === 'championship' ? <ChampionshipPage key={category} season={season} category={category} theme={theme} />
              : <SessionWorkspace key={`${category}:${season}`} season={season} category={category} params={params} update={update} view={view} theme={theme} />}
      </main>
      <footer><span>MotoGP Race Intelligence <span className="footer-divider">/</span> Engine preview · English</span><span>Official API, timing PDFs & labeled archives <ArrowRight size={13} /></span></footer>
    </div>
  </div>
}
