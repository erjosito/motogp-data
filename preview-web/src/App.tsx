import { Component, lazy, Suspense, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import {
  ArrowDownRight, ArrowRight, ArrowUpRight, Check, ChevronRight, Flag,
  Gauge, Layers3, Menu, Moon, RefreshCw, Sun, Timer, Trophy, Users,
} from 'lucide-react'
import { useResource } from './api'
import { categories, categoryPath, navigationPath, profilePath, selectedCategory, selectedSeason, selectedView, selectionParams } from './selection'
import type { Category } from './selection'
import { bestSectors, cleanLaps, lapTime, MARC_ID, median, riderStyle, signed } from './data'
import type { Analysis, Championship, GrandPrix, Lap, Rider, RiderProfile, Session } from './types'
import type { PlotChartProps } from './PlotChart'
import { seasonCharts } from './seasonCharts'
import { CircuitContext, RiderVisualContext } from './VisualContext'
import type { SeasonChart } from './seasonCharts'
import './App.css'

const Chart = lazy(() => import('./PlotChart'))
const classicUrl = import.meta.env.VITE_CLASSIC_URL || 'https://motogp-data.com'
const views = [
  { id: 'riders', name: 'The riders', icon: Users, detail: 'Remarkable careers. Unforgettable rides.' },
  { id: 'championship', name: 'The title fight', icon: Trophy, detail: 'The season, in perspective' },
  { id: 'results', name: 'Session results', icon: Flag, detail: 'Every position. Every point.' },
  { id: 'laps', name: 'Lap comparison', icon: Timer, detail: 'Find the difference in pace' },
  { id: 'sectors', name: 'Sector analysis', icon: Layers3, detail: 'Where the time is won' },
] as const
type View = typeof views[number]['id']
type UpdateLocation = (values: Record<string, string | null>) => void

export function RiderProfileContent({ data, params, theme }: { data: RiderProfile; params: URLSearchParams; theme: string }) {
  const { rider, totals } = data
  const racing = data.seasons.filter((row) => row.gp_appearances > 0)
  const ranked = data.seasons.filter((row) => row.position != null)
  const titleHero = totals.titles > 0 && ranked.length === data.seasons.length
  const heroMetric = titleHero ? 'titles' : totals.gp_wins ? 'gp_wins' : totals.gp_podiums ? 'gp_podiums' : 'gp_appearances'
  const heroLabel = titleHero ? 'OFFICIAL TITLES RECORDED' : !totals.gp_appearances ? 'OFFICIAL SEASON RECORDS' : totals.gp_wins ? 'RECORDED GP WINS' : totals.gp_podiums ? 'RECORDED GP PODIUMS' : 'RECORDED GP APPEARANCES'
  const venueMetric = totals.gp_wins > 0 ? 'wins' : totals.gp_podiums > 0 ? 'podiums' : 'appearances'
  const venueRows = [...data.venues].sort((a, b) => b[venueMetric] - a[venueMetric]).slice(0, 7)
  const seasonLabel = (row: typeof data.seasons[number]) => `${row.season} / ${categories[row.category]}`
  const finalRanks = new Map<string, number>()
  for (const row of ranked) {
    const label = `P${row.position}${row.is_final ? '' : ' (to date)'}`
    finalRanks.set(label, (finalRanks.get(label) ?? 0) + 1)
  }
  return <>
    <div className="page-heading"><div><p className="eyebrow">THE RIDERS / CAREER PORTRAIT</p><h1>{rider.rider}.</h1><p>More than a name on the timing screen.</p></div>
      <span className="quiet-badge">{data.first_season === data.latest_season ? data.first_season : `${data.first_season} — ${data.latest_season}`} · recorded seasons</span></div>
    <section className={`story-card rider-hero ${rider.rider_id === MARC_ID ? 'marc-hero' : ''}`}>
      <div className="rider-visual-header"><RiderVisualContext rider={rider} /></div>
      <div className="story-intro"><div className="story-copy"><p className="eyebrow accent">{rider.rider_id === MARC_ID ? 'THE PROTAGONIST / 93' : 'A CAREER IN FOCUS'}</p>
        <h2>{data.headline}</h2><p>{data.summary}</p>
        {!!data.titles.length && <p className="eyebrow">OFFICIAL TITLE SEASONS IN THE ARCHIVE</p>}
        <div className="rider-title-years">{data.titles.map((row) => <a key={`${row.season}-${row.category}`}
          href={profilePath(params, { view: 'championship', season: String(row.season), category: row.category })}>
          <Trophy size={13} />{row.season}<span>{categories[row.category]}</span></a>)}</div>
        {!data.titles.length && <p>Explore the recorded results and championship positions below.</p>}
      </div><div className="comeback-score"><span className="ghost-number" aria-hidden="true">{rider.number ?? ''}</span>
        <span className="eyebrow">{heroLabel}</span><div className="recovery-value">{titleHero || totals.gp_appearances ? totals[heroMetric] : ranked.length}</div>
        <p>{titleHero ? 'Final rank-one season/class records' : !totals.gp_appearances ? 'Supplied season/class championship positions' : 'Across the recorded Grand Prix archive'}</p><div className="mini-stats"><div><strong>{new Set(data.seasons.map((row) => row.season)).size}</strong><span>recorded seasons</span></div>
          <div><strong>{new Set(data.seasons.map((row) => row.category)).size}</strong><span>category families</span></div></div>
      </div></div>
    </section>
    <div className="stats-grid rider-stats">
      <Stat label={heroMetric === 'gp_wins' ? 'RECORDED GP APPEARANCES' : 'RECORDED GP WINS'} value={totals.gp_appearances ? heroMetric === 'gp_wins' ? totals.gp_appearances : totals.gp_wins : '\u2014'} note="Grand Prix classifications; Sprints kept separate" />
      <Stat label="RECORDED GP PODIUMS" value={totals.gp_appearances ? totals.gp_podiums : '\u2014'} note="Top-three GP finishes, including victories" />
      <Stat label="RECORDED SPRINT WINS" value={totals.sprint_appearances ? totals.sprint_wins : '\u2014'} note="Sprint classifications only, not Grand Prix wins" />
    </div>
    {rider.rider_id === MARC_ID && <MarcRiderStory params={params} theme={theme} />}
    <div className="season-chart-grid rider-chart-grid">
      <section className="panel" data-rider-chart="seasons"><div className="section-heading"><div><p className="eyebrow">THE CAREER ARC</p>
        <h2>{racing.length ? 'Seasons that made the rider' : 'A place in championship history'}</h2>
        <p>{racing.length ? totals.gp_podiums ? 'GP wins and other podiums, season by season and class by class.' : 'Recorded Grand Prix appearances, season by season and class by class.' : 'Official championship positions, with final and to-date records distinguished.'}</p></div></div>
        {racing.length ? <Plot theme={theme} height={420} yTitle={totals.gp_podiums ? 'Recorded GP podiums' : 'Recorded GP appearances'} valueUnit={totals.gp_podiums ? 'podiums' : 'appearances'} stacked series={totals.gp_podiums ? [
          { id: rider.rider_id, name: 'Wins', type: 'bar', x: racing.map(seasonLabel), y: racing.map((row) => row.gp_wins) },
          { id: 'other-podiums', name: 'Other podiums', type: 'bar', colors: ['--cp-text-muted'], x: racing.map(seasonLabel), y: racing.map((row) => row.gp_podiums - row.gp_wins) },
        ] : [{ id: rider.rider_id, name: 'GP appearances', type: 'bar', x: racing.map(seasonLabel), y: racing.map((row) => row.gp_appearances) }]} /> : <Plot theme={theme} height={420} yTitle="Official championship rank" rank valueUnit="rank" series={[
          { id: rider.rider_id, name: rider.rider, type: 'scatter', x: ranked.map((row) => `${seasonLabel(row)}${row.is_final ? '' : ' (to date)'}`), y: ranked.map((row) => row.position) },
        ]} />}
      </section>
      <section className="panel" data-rider-chart="signature"><div className="section-heading"><div><p className="eyebrow">THE SIGNATURE</p>
        <h2>{venueRows.length ? `Where the ${venueMetric === 'wins' ? 'victories' : venueMetric === 'podiums' ? 'podiums' : 'races'} happened` : 'The championship finishing record'}</h2>
        <p>{venueRows.length ? 'Leading venues across the rider’s recorded Grand Prix results.' : 'Frequency of supplied official ranks; no race results inferred.'}</p></div></div>
        <Plot theme={theme} height={420} yTitle="" xTitle={venueRows.length ? `Recorded GP ${venueMetric}` : 'Season/class records'} valueUnit={venueRows.length ? venueMetric : 'records'} series={[{
          id: rider.rider_id, name: venueRows.length ? `GP ${venueMetric}` : 'Championship ranks', type: 'bar', orientation: 'h', showValues: true,
          x: venueRows.length ? venueRows.map((row) => row[venueMetric]) : [...finalRanks.values()],
          y: venueRows.length ? venueRows.map((row) => row.venue) : [...finalRanks.keys()],
        }]} />
      </section>
    </div>
    <section className="panel"><div className="section-heading"><div><p className="eyebrow">CHAPTER BY CHAPTER</p><h2>The season record</h2><p>Open any season to explore the title fight.</p></div></div>
      <div className="table-scroll"><table><thead><tr><th>Season / class</th><th>Official rank</th><th>GP wins</th><th>GP podiums</th><th>Standings</th></tr></thead>
        <tbody>{[...data.seasons].reverse().map((row) => <tr key={`${row.season}-${row.category}`}>
          <td><a href={profilePath(params, { view: 'championship', season: String(row.season), category: row.category })}>{seasonLabel(row)} <ArrowUpRight size={12} /></a></td>
          <td className="numeric">{row.position == null ? '\u2014' : `P${row.position}${row.is_final ? '' : ' · to date'}`}</td>
          <td className="numeric">{row.gp_appearances ? row.gp_wins : '\u2014'}</td><td className="numeric">{row.gp_appearances ? row.gp_podiums : '\u2014'}</td>
          <td>{row.source_url ? <a href={row.source_url} target="_blank" rel="noreferrer">Official source <ArrowUpRight size={12} /></a> : '\u2014'}</td>
        </tr>)}</tbody></table></div>
      <p className="panel-note">Titles use official final season/class ranks only. Race statistics describe stored classifications across supported classes, not certified complete-career totals. From 1990, only sessions awarding points are counted. Grand Prix and Sprint records remain separate.</p>
    </section>
  </>
}

function MarcRiderStory({ params, theme }: { params: URLSearchParams; theme: string }) {
  const resource = useResource<Championship>('/api/championship?season=2026&category=premier')
  const comeback = resource.data?.comeback
  if (resource.error) return <DataState resource={resource} />
  if (resource.loading) return <Loading label="Loading the comeback chapter" />
  if (!comeback?.verified_102) return null
  return <section className="panel marc-chapter" data-rider-chart="comeback">
    <div className="section-heading"><div><p className="eyebrow accent">MARC / THE COMEBACK CHAPTER</p><h2>102 behind. {signed(comeback.current_margin)} at the latest result.</h2>
      <p>{comeback.recovered} points of net recovery from the low. Every imported Sprint and Grand Prix is part of this chapter.</p></div>
      <a className="text-button" href={profilePath(params, { view: 'championship', season: '2026', category: 'premier' })}>Read the season <ArrowUpRight size={14} /></a></div>
    <Plot theme={theme} height={300} baseline yTitle="Points vs strongest rival" series={[{
      id: MARC_ID, name: 'Marc Marquez', x: comeback.history.map((point) => point.label), y: comeback.history.map((point) => point.margin),
    }]} />
  </section>
}

function RiderPage({ params, update, theme }: { params: URLSearchParams; update: UpdateLocation; theme: string }) {
  const riderId = params.get('rider') ?? MARC_ID
  const directory = useResource<Rider[]>('/api/riders')
  const resource = useResource<RiderProfile>(`/api/riders/${encodeURIComponent(riderId)}`)
  const [search, setSearch] = useState('')
  useEffect(() => {
    if (resource.data) document.title = `MotoGP | ${resource.data.rider.rider}`
  }, [resource.data])
  const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  const riders = (directory.data ?? []).filter((rider) => normalize(rider.rider).includes(normalize(search)))
  const featuredNames = ['marc marquez', 'valentino rossi', 'giacomo agostini', 'jorge lorenzo', 'dani pedrosa', 'casey stoner', 'francesco bagnaia', 'fabio quartararo']
  const visible = search ? riders.slice(0, 24) : featuredNames.flatMap((name) => riders.filter((rider) => normalize(rider.rider) === name))
  return <>
    {resource.error ? <DataState resource={resource} /> : resource.data ? <RiderProfileContent data={resource.data} params={params} theme={theme} /> : <Loading label="Loading the rider’s story" />}
    <section className="panel rider-directory"><div className="section-heading"><div><p className="eyebrow">EXPLORE THE PADDOCK</p><h2>Every rider has a story.</h2><p>Find a current contender or a name from the archives.</p></div>
      <label className="search-label"><span className="eyebrow">FIND A RIDER</span><input aria-label="Find a rider" type="search" value={search} placeholder="Search any rider…" onChange={(event) => setSearch(event.target.value)} /></label></div>
      {directory.error ? <DataState resource={directory} /> : directory.loading ? <Loading label="Loading the rider directory" /> : <>
        <div className="rider-directory-grid">{visible.map((rider) => <a key={rider.rider_id} aria-current={rider.rider_id === riderId ? 'page' : undefined}
          href={profilePath(params, { view: 'riders', rider: rider.rider_id })} onClick={(event) => { event.preventDefault(); update({ view: 'riders', rider: rider.rider_id }); }}>
          <RiderName rider={rider} /><ArrowUpRight size={15} /></a>)}</div>
        <p className="panel-note" role="status">{search ? `${riders.length} matching riders${riders.length > 24 ? ' · Showing the first 24; refine your search.' : ''}` : `${directory.data?.length.toLocaleString()} riders in the archive. Search to explore them all.`}</p>
      </>}
    </section>
  </>
}

function dateLabel(value: string | null | undefined) {
  return value ? new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short' }).format(new Date(value)) : '\u2014'
}

function RiderName({ rider, linked = false }: { rider: Rider; linked?: boolean }) {
  const token = riderStyle(rider.rider_id).token
  return <span className="rider-name">
    <span className="rider-number" style={{ color: `var(${token})` }}>{rider.number ?? '\u2014'}</span>
    {linked ? <a href={profilePath(new URLSearchParams(typeof window === 'undefined' ? '' : window.location.search), { view: 'riders', rider: rider.rider_id })}>{rider.rider}</a> : <span>{rider.rider}</span>}
  </span>
}

function Loading({ label = 'Loading race data' }: { label?: string }) {
  return <div className="loading" role="status"><span className="spinner" />{label}</div>
}

function DataState({ resource, empty }: { resource?: { error: string | null; retry: () => void }; empty?: string }) {
  return <div className="data-state" role={resource?.error ? 'alert' : 'status'}>
    <Flag size={28} aria-hidden="true" />
    <h3>{resource?.error ? 'The data is taking a pit stop' : 'Nothing recorded here yet'}</h3>
    <p>{resource?.error ?? empty}</p>
    {resource?.error && <button className="button" onClick={resource.retry}><RefreshCw size={15} />Try again</button>}
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

function Plot(props: PlotChartProps) {
  return <ChartBoundary><Suspense fallback={<Loading label="Preparing chart" />}>
    <Chart {...props} />
  </Suspense></ChartBoundary>
}

function SeasonChartPanel({ chart, theme }: { chart: SeasonChart; theme: string }) {
  return <section className="panel season-chart-panel" data-season-chart={chart.id} data-chart-kind={chart.kind} aria-labelledby={`chart-${chart.id}`}>
    <div className="section-heading"><div><p className="eyebrow">THE STORY IN DATA</p><h2 id={`chart-${chart.id}`}>{chart.title}</h2><p>{chart.description}</p></div>
      <span className="quiet-badge chart-type">{chart.kind === 'bridge' ? 'Recovery bridge' : chart.kind}</span></div>
    <Plot series={chart.series} yTitle={chart.yTitle} xTitle={chart.xTitle} baseline={chart.baseline}
      valueUnit={chart.valueUnit} rank={chart.rank} stacked={chart.stacked} theme={theme} height={420} />
    <p className="panel-note">{chart.note}</p>
  </section>
}

function Stat({ label, value, note }: { label: string; value: string | number; note: string }) {
  return <div className="stat"><span className="eyebrow">{label}</span><strong>{value}</strong><span>{note}</span></div>
}

function ChampionshipPage({ season, category, theme }: { season: number; category: Category; theme: string }) {
  const resource = useResource<Championship>(categoryPath(`/api/championship?season=${season}`, category))
  const data = resource.data
  if (resource.error) return <DataState resource={resource} />
  if (!data) return <Loading />
  return <ChampionshipContent data={data} category={category} theme={theme} />
}

export function ChampionshipContent({ data, category, theme }: { data: Championship; category: Category; theme: string }) {
  const season = data.season
  const visual = seasonCharts(data)
  if (!data.standings.length) return <><div className="page-heading"><div><p className="eyebrow">{season} / SEASON STORY</p><h1>{data.story.headline}</h1><p>{data.story.accent}</p></div></div>
    <DataState empty={data.story.summary} />
    <div className="season-chart-grid" data-story-layout={visual.layout}>{visual.charts.map((chart) =>
      <SeasonChartPanel key={`${season}-${category}-${chart.id}`} chart={chart} theme={theme} />)}</div></>

  const story = data.comeback
  const pointsWarning = data.official_points_inconsistent || Boolean(data.points_warning)
  const featured = !pointsWarning && category === 'premier' && season === 2026 && story?.verified_102
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
            {featured ? '102-point deficit verified in race results' : official ? `Based on ${officialLabel.toLowerCase()}` : 'Based on imported race results'}
          </span>
        </div>
        <div className="comeback-score">
          <span className="ghost-number" aria-hidden="true">{featured ? '93' : leader.number ?? season}</span>
          <span className="eyebrow">{narrative.metric_label}</span>
          <div className="recovery-value">{narrative.metric}<ArrowUpRight size={35} aria-hidden="true" /></div>
          <p>{narrative.metric_note}</p>
          <div className="mini-stats"><div><strong>P{featured && marc ? marc.position : leader.position}</strong><span>{official ? (final ? 'official final rank' : 'official rank to date') : 'in the imported standings'}</span></div><div><strong>{featured && marc ? marc.points : leader.points}</strong><span>{pointsWarning ? 'supplied points' : 'points earned'}</span></div></div>
        </div>
      </div>
      {featured && story && <div className="story-chart" data-season-chart="gap" data-chart-kind="line">
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
      <Stat label={final ? 'OFFICIAL CHAMPION' : 'CHAMPIONSHIP LEADER'} value={leader.rider} note={pointsWarning ? `${leader.points} supplied points` : `${leader.points} points${leader.wins == null ? '' : ` · ${leader.wins} imported Grand Prix wins`}`} />
      {pointsWarning ? <Stat label="OFFICIAL RANK" value={`P${leader.position}`} note="Position in the official standings" /> : <Stat label={featured ? 'MÁRQUEZ / THE GAP' : 'LEAD OVER SECOND'} value={featured ? marginLabel : data.standings[1]?.gap == null ? '—' : `${data.standings[1].gap} pts`} note={featured ? 'Relative to the closest title rival' : official ? `From ${officialLabel.toLowerCase()}` : 'Calculated from imported results'} />}
      <Stat label={official ? 'OFFICIAL CLASSIFICATION' : 'SCORING WEEKENDS'} value={official ? data.standings.length : data.weekends} note={official ? `Riders in the ${final ? 'preserved final' : 'current official'} standings` : `${data.gp_results} GP race results · ${data.scoring_sessions} scoring sessions`} />
    </div>

    {!featured && <div className="season-chart-grid" data-story-layout={visual.layout}>{visual.charts.map((chart) =>
      <SeasonChartPanel key={`${season}-${category}-${chart.id}`} chart={chart} theme={theme} />)}</div>}

    <div className={featured ? 'championship-grid' : 'standings-section'} data-story-layout={visual.layout}>
      <section className="panel"><div className="section-heading"><div><p className="eyebrow">THE ORDER</p><h2>Championship standings</h2></div><span className="quiet-badge">{season}</span></div>
        <div className="table-scroll"><table className="standings-table">
          <thead><tr><th>Pos</th><th>Rider</th><th>Pts</th><th>Gap</th><th>{official ? 'Imported GP wins' : 'Wins'}</th></tr></thead>
          <tbody>{data.standings.map((rider) => <tr key={rider.rider_id} className={featured && rider.rider_id === MARC_ID ? 'featured-row' : ''}>
            <td><span className={`position ${rider.position <= 3 ? 'top-position' : ''}`}>{String(rider.position).padStart(2, '0')}</span></td>
            <td><RiderName rider={rider} linked /><small>{rider.constructor || rider.team || 'Team not recorded'}</small></td>
            <td className="strong numeric">{rider.points}</td><td className="muted numeric">{pointsWarning || rider.gap == null || rider.gap === 0 ? '—' : `−${rider.gap}`}</td><td className="numeric">{rider.wins ?? '—'}</td>
          </tr>)}</tbody></table></div>
        <p className="panel-note">{official ? `${officialLabel}. Official positions and decimal points are preserved independently of race points. Wins, where shown, count only the ${data.gp_results} imported scoring GP races; missing historical wins are not inferred.` : 'GP + Sprint points. Wins and GP finish countback exclude sessions awarding no points. Source adjustments outside the database are not included.'}</p>
      </section>
      {featured && <SeasonChartPanel chart={visual.charts[1]} theme={theme} />}
    </div>
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
            <td><RiderName rider={rider} linked /><small>{rider.team ?? rider.constructor ?? 'Not recorded'}</small>{rider.source_kind !== 'official-api' && <small>{rider.source_kind === 'external' ? 'External archive classification' : 'Official classification · externally augmented'}</small>}</td>
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
    {event?.circuit_name && <CircuitContext name={event.circuit_name} season={season} />}
    {analysis.data?.results.some((row) => row.source_kind !== 'official-api') && <p className="notice">This classification includes verified external archive supplementation. Source labels identify supplemented and external-only rows; no missing timing is invented.</p>}
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
  const view: View = selectedView(params)
  const category = selectedCategory(params.get('category'))
  const resource = useResource<number[]>(category && view !== 'riders' ? categoryPath('/api/seasons', category) : null)
  const seasons = resource.data ?? []
  const season = selectedSeason(params, seasons)
  useEffect(() => {
    document.title = `MotoGP | ${views.find((item) => item.id === view)!.name}`
  }, [view])

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
      <a className="brand" href={profilePath(params, { view: 'riders', rider: MARC_ID })} onClick={(event) => { event.preventDefault(); update({ view: 'riders', rider: MARC_ID }) }}>
        <span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /></span><span>MotoGP<span className="brand-sub">RACE INTELLIGENCE</span></span>
      </a>
      <button className="mobile-menu icon-button" aria-label="Toggle navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}><Menu size={23} /></button>
      <div className="sidebar-content">
        <p className="nav-caption">THE PADDOCK</p>
        <nav aria-label="Main navigation">{views.map(({ id, name, icon: Icon }) => <a key={id} href={navigationPath(params, id)} className={view === id ? 'active' : ''} aria-current={view === id ? 'page' : undefined}
          onClick={(event) => { event.preventDefault(); update({ view: id }); setMenuOpen(false) }}>
          <Icon size={19} /><span>{name}</span>{view === id && <ChevronRight size={15} className="nav-chevron" />}
        </a>)}</nav>
        <div className="sidebar-bottom"><span className="preview-tag">NEW ENGINE / PREVIEW</span><h3>The people behind the points.</h3><p>Rider stories, season battles and race analysis. The complete suite and all languages are still in Classic.</p>
          <a className="classic-link" href={classicUrl} target="_blank" rel="noreferrer">Open Classic<ArrowUpRight size={16} /></a>
          <div className="sidebar-foot"><Gauge size={14} /><span>Read-only · Sources labeled</span></div>
        </div>
      </div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><div className="breadcrumb"><span>{view === 'riders' ? 'The paddock' : category ? categories[category] : 'Unknown category'}</span><ChevronRight size={13} /><strong>{view === 'riders' ? 'Rider stories' : season ?? 'Season'}</strong></div>
        <div className="topbar-actions">
          {view !== 'riders' && <><label className="season-select category-select"><span>CATEGORY</span><select aria-label="Category" value={category ?? ''} onChange={(event) => update({ category: event.target.value })}>
            {!category && <option value="" disabled>Unsupported category</option>}
            {Object.entries(categories).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select></label>
          <label className="season-select"><span>SEASON</span><select aria-label="Season" value={season ?? ''} disabled={!seasons.length} onChange={(event) => update({ season: event.target.value })}>
          {season && !seasons.includes(season) && <option value={season}>{season} · not imported</option>}
          {!seasons.length && <option value="">—</option>}{seasons.map((year) => <option key={year} value={year}>{year}</option>)}
        </select></label></>}
          <button className="icon-button" aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} onClick={toggleTheme}>{theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}</button>
          <button className="icon-button" aria-label="Refresh data" onClick={() => window.location.reload()}><RefreshCw size={17} /></button>
        </div>
      </header>
      <main id="main">
        {view !== 'riders' && category && params.has('season') && seasons.length > 0 && Number(params.get('season')) !== season && <p className="notice" role="status">The requested season value is invalid. Showing {season}.</p>}
        {view === 'riders' ? <RiderPage params={params} update={update} theme={theme} /> : !category ? <DataState resource={{ error: null, retry: () => {} }} empty="This category key is unsupported. Choose a Grand Prix category above." />
          : resource.error ? <DataState resource={resource} /> : resource.loading ? <Loading />
          : !season || !seasons.includes(season) ? <DataState resource={resource} empty={`No data has been imported for ${categories[category]}${season ? ` in ${season}` : ''}. This is not a zero-point result. Choose another season or category; extinct classes remain separate.`} />
            : view === 'championship' ? <ChampionshipPage key={category} season={season} category={category} theme={theme} />
              : <SessionWorkspace key={`${category}:${season}`} season={season} category={category} params={params} update={update} view={view} theme={theme} />}
      </main>
      <footer><span>MotoGP Race Intelligence <span className="footer-divider">/</span> Engine preview · English</span><span>Official API, timing PDFs & labeled archives <ArrowRight size={13} /></span></footer>
    </div>
  </div>
}
