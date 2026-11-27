import { profilePath } from './selection'
import type { Analysis, Result } from './types'

function measured(row: Result) {
  return row.finish_gap_seconds != null && Number.isFinite(row.finish_gap_seconds) && row.finish_gap_seconds >= 0
}

function resultStory(data: Analysis) {
  const race = ['RAC', 'SPR'].includes(data.session.session_type)
  const ranked = data.results.filter((row) => row.position != null && row.position > 0)
  const first = ranked.filter((row) => row.position === 1 && row.status === 'INSTND')
  const winner = first.length === 1 && ranked.filter((row) => row.position === 1).length === 1 ? first[0] : null
  const seconds = ranked.filter((row) => row.position === 2)
  const thirds = ranked.filter((row) => row.position === 3)
  const second = seconds.length === 1 ? seconds[0] : null
  const third = thirds.length === 1 ? thirds[0] : null
  let headline = race ? 'The recorded race classification.' : 'The session classification.'
  let takeaway = 'Comparable finish times are unavailable; recorded ranks and source gaps remain below.'
  if (!race) takeaway = 'This is not a race finish. Practice and qualifying times remain in the full classification.'
  else if (winner) {
    headline = `${winner.rider} is classified first.`
    if (measured(winner) && second && measured(second)) {
      takeaway = second.finish_gap_seconds === 0
        ? 'P1 and P2 have equal recorded elapsed times; the source classification order is preserved.'
        : `P2 is +${second.finish_gap_seconds!.toFixed(3)} s on elapsed time.`
      if (third && measured(third)) takeaway += ` P3 is +${third.finish_gap_seconds!.toFixed(3)} s to P1.`
    }
  }
  return { race, headline, takeaway, podium: race ? ranked.filter((row) => row.position! <= 3 && row.status === 'INSTND') : [], field: ranked.slice(0, 6) }
}

function Identity({ row }: { row: Result }) {
  const initials = row.rider.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('')
  return <a className="finish-identity" href={profilePath(new URLSearchParams(typeof window === 'undefined' ? '' : window.location.search), { view: 'riders', rider: row.rider_id })}>
    <span className="finish-number" aria-label={row.number == null ? `${row.rider}, initials` : `Rider number ${row.number}`}>{row.number == null ? initials : `#${row.number}`}</span>
    <span>{row.rider}</span>
  </a>
}

export default function ResultStory({ data }: { data: Analysis }) {
  const story = resultStory(data)
  const supported = story.race ? story.field.filter(measured) : []
  const maximum = Math.max(0, ...supported.map((row) => row.finish_gap_seconds!))
  return <section className="panel result-story" aria-labelledby="result-story-title">
    <p className="eyebrow accent">{story.race ? 'THE FINISH / CLASSIFICATION STORY' : 'THE SESSION / SOURCE CLASSIFICATION'}</p>
    <h2 id="result-story-title">{story.headline}</h2><p className="result-takeaway">{story.takeaway}</p>
    {!!story.podium.length && <ol className="finish-podium" aria-label="Recorded podium positions">
      {story.podium.map((row) => <li key={row.rider_id}><span className="eyebrow">P{row.position}</span><Identity row={row} /><span className="finish-team">{row.constructor || row.team || 'Team not recorded'}</span></li>)}
    </ol>}
    {story.race && story.field.length > 0 && <div className="finish-comparison">
      <h3>Elapsed-time difference to P1 (s)</h3><p className="panel-note">Leading six recorded ranks · same-lap classified finishers only.</p>
      <ol className="finish-gaps">{story.field.map((row) => {
        const valid = measured(row)
        const gap = row.finish_gap_seconds
        return <li key={row.rider_id}>
          <div className="finish-label"><span>P{row.position}</span><strong>{row.rider}</strong><b>{valid ? gap === 0 ? '0.000 s' : `+${gap!.toFixed(3)} s` : 'Unscaled'}</b></div>
          {valid ? <div className="finish-track" aria-hidden="true"><i style={{ left: `${maximum > 0 ? gap! / maximum * 100 : 0}%` }} /></div>
            : <p className="finish-unavailable">{row.finish_gap_reason || 'Comparable elapsed time unavailable.'}</p>}
          <small>Source gap: {row.gap_first || 'not recorded'} · status: {row.status || 'not recorded'}</small>
        </li>
      })}</ol>
      <p className="panel-note">Differences use recorded elapsed durations, not an official adjusted winning margin. Source ranks are never reordered. Lapped, non-finish and conflicting records are not placed on the time scale; full source times, gaps and statuses remain in the classification.</p>
    </div>}
    {!data.results.length && <p className="panel-note">No classification has been recorded for this session.</p>}
  </section>
}
