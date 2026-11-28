import { confirmedFinal, MARC_ID, riderStyle } from './data'
import type { ChartSeries } from './PlotChart'
import type { Championship, Standing } from './types'

export interface SeasonChart {
  id: string
  title: string
  description: string
  note: string
  kind: 'line' | 'bar' | 'bridge' | 'scatter' | 'doughnut' | 'lollipop' | 'stacked' | 'comparison'
  series: ChartSeries[]
  yTitle: string
  xTitle?: string
  valueUnit?: string
  baseline?: boolean
  rank?: boolean
  stacked?: boolean
}

function label(rider: Standing) {
  return `P${rider.position} ${rider.rider.split(' ').at(-1)}`
}

function pointsBars(data: Championship): SeasonChart {
  const riders = data.standings.slice(0, 10)
  return {
    id: 'points', title: 'The points that set them apart',
    description: 'The leading ten, in the preserved championship order.',
    note: data.standings_source === 'official'
      ? `Official ${confirmedFinal(data.lifecycle) ? 'final' : 'snapshot'} points; period counting rules and decimal totals are preserved.`
      : 'Imported championship totals; unrecorded results or adjustments are not included.',
    kind: 'bar', xTitle: 'Championship points', yTitle: '',
    series: [{
      id: riders[0].rider_id, name: 'Championship points', type: 'bar', orientation: 'h',
      x: riders.map((rider) => rider.points), y: riders.map(label),
      text: riders.map((rider) => rider.rider), colors: riders.map((rider) => riderStyle(rider.rider_id).token),
      hovertemplate: '%{text}<br>%{x:,.3~f} points<extra></extra>',
    }],
  }
}

function margins(data: Championship): SeasonChart {
  const riders = data.standings.filter((rider): rider is Standing & { gap: number } =>
    rider.gap != null && Number.isFinite(rider.gap)).slice(0, 8)
  return {
    id: 'margins', title: 'How close was the field?',
    description: 'Each gap is measured against the rider ranked first, not against the next rider.',
    note: 'Equal points remain equal. Gaps never replace the official ranks or imply a race-by-race history.',
    kind: 'bar', xTitle: 'Gap to first (points)', yTitle: '',
    series: [{ id: riders[0].rider_id, name: 'Gap to first', type: 'bar', orientation: 'h', showValues: true,
      x: riders.map((rider) => rider.gap), y: riders.map((rider) => `P${rider.position} ${rider.rider}`),
      text: riders.map((rider) => rider.rider), colors: riders.map((rider) => riderStyle(rider.rider_id).token),
      hovertemplate: '%{y}<br>%{x:,.3~f} points behind<extra></extra>',
    }],
  }
}

function suppliedScores(data: Championship): [SeasonChart, SeasonChart] {
  const official = data.standings_source === 'official'
  const riders = data.standings.slice(0, 10)
  const corrected = Boolean(data.points_correction)
  const note = corrected
    ? 'Official ranks with two independently sourced point corrections; other totals remain unverified.'
    : 'Source ranks and supplied scores are shown unchanged.'
  const pointsLabel = corrected ? 'Reported points' : 'Supplied points'
  const bars = pointsBars(data)
  return [{
    ...bars, id: 'supplied-scores', title: corrected ? 'Reported scores, in official order' : 'Supplied scores, in source order',
    description: corrected ? 'The leading ten by official rank, including two independent corrections.' : 'The leading ten by source rank, not sorted or corrected by supplied score.',
    note, xTitle: pointsLabel,
    series: bars.series.map((series) => ({
      ...series, name: pointsLabel,
      hovertemplate: `%{text}<br>%{x:,.3~f} ${pointsLabel.toLowerCase()}<extra></extra>`,
    })),
  }, {
    id: 'rank-versus-supplied-score', title: official ? 'Official rank versus reported score' : 'Imported rank versus supplied score',
    description: corrected ? 'Official ranks paired with reported totals, including two independent corrections.' : 'Each source rank paired with its unchanged supplied point total.',
    note, kind: 'scatter', xTitle: pointsLabel, yTitle: official ? 'Official rank' : 'Imported rank', rank: true,
    series: riders.map((rider) => ({
      id: rider.rider_id, name: rider.rider, type: 'scatter', x: [rider.points], y: [rider.position],
      hovertemplate: `%{x:,.3~f} ${pointsLabel.toLowerCase()}<br>Source rank %{y}<extra>%{fullData.name}</extra>`,
    })),
  }]
}

export function seasonCharts(data: Championship): { layout: string; charts: [SeasonChart, SeasonChart] } {
  if (!data.standings.length) {
    if (!data.coverage) throw new Error('Championship coverage evidence is missing.')
    const coverage = data.coverage
    return {
      layout: 'coverage',
      charts: [{
        id: 'record-coverage', title: 'The season at a glance',
        description: 'Available records are evidence, not a reconstructed championship.',
        note: 'These are actual counts for finished sessions in this season/category. Zero means no rows are stored.',
        kind: 'bar', yTitle: 'Stored rows', valueUnit: 'rows',
        series: [{ id: 'records', name: 'Stored rows', type: 'bar', showValues: true,
          x: ['Classification rows', 'Lap records'], y: [coverage.classification_rows, coverage.lap_rows] }],
      }, {
        id: 'session-coverage', title: 'Where the classifications are missing',
        description: 'Finished imported sessions, with and without classification rows.',
        note: 'The archive can be incomplete. A missing classification is not a zero-point finish.',
        kind: 'bar', yTitle: 'Imported sessions', valueUnit: 'sessions',
        series: [{ id: 'sessions', name: 'Finished sessions', type: 'bar', showValues: true,
          x: ['With classification', 'Without classification'],
          y: [coverage.classified_sessions, coverage.sessions - coverage.classified_sessions] }],
      }],
    }
  }
  const [leader, second] = data.standings
  const official = data.standings_source === 'official'
  const flagged = official && (data.official_points_inconsistent || Boolean(data.points_warning))
  const gapsAvailable = data.standings.every((rider) => rider.gap != null && Number.isFinite(rider.gap) && rider.gap >= 0)
  if (flagged || !gapsAvailable) {
    return { layout: flagged ? 'source-verification' : 'standings', charts: suppliedScores(data) }
  }
  const kind = data.story.kind
  const featured = kind === 'comeback' && data.comeback?.rider_id === MARC_ID && data.comeback.verified_102
  const history = featured ? data.comeback!.history : (!official && leader.series.length === data.rounds.length
    ? data.rounds.map((round, index) => {
      const rivals = data.standings.slice(1).map((rider) => rider.series[index])
      return { ...round, points: leader.series[index], margin: leader.series[index] - (rivals.length ? Math.max(...rivals) : 0) }
    }) : [])

  if ((kind === 'comeback' && history.length > 0) || (kind === 'late-surge' && history.length > 1)) {
    const low = history.reduce((best, point) => point.margin < best.margin ? point : best)
    const latest = history.at(-1)!
    const subjectId = featured ? MARC_ID : leader.rider_id
    const subjectName = featured ? data.standings.find((rider) => rider.rider_id === MARC_ID)?.rider ?? 'Marc Marquez' : leader.rider
    const curve: SeasonChart = {
      id: 'gap', title: featured ? 'The comeback curve' : 'The lead changed hands',
      description: 'Points relative to the strongest imported rival after each scoring session.',
      note: 'This is an imported race-points curve, independent of any official standings snapshot.',
      kind: 'line', yTitle: 'Points vs strongest rival', baseline: true,
      series: [{ id: subjectId, name: subjectName, x: history.map((point) => point.label), y: history.map((point) => point.margin) }],
    }
    if (kind === 'late-surge' && second && !official && second.series.length === data.rounds.length) {
      const start = Math.max(0, data.rounds.length - 3)
      return { layout: 'late-surge', charts: [curve, {
        id: 'decisive-sessions', title: 'The sessions that swung the lead',
        description: 'Points added by the leading pair in the last three sessions.',
        note: 'Actual changes in imported cumulative points; these are not inferred from official final totals.',
        kind: 'bar', yTitle: 'Imported session points',
        series: [leader, second].map((rider) => ({
          id: rider.rider_id, name: rider.rider, type: 'bar',
          x: data.rounds.slice(start).map((round) => round.label),
          y: rider.series.slice(start).map((value, index) => value - (rider.series[start + index - 1] ?? 0)),
        })),
      }] }
    }
    return { layout: 'comeback', charts: [curve, {
      id: 'recovery-bridge', title: 'From the low to the latest gap',
      description: 'The floating middle bar bridges the lowest margin and the latest margin.',
      note: `${latest.margin - low.margin} points of net gap improvement. This is not points earned or a forecast.`,
      kind: 'bridge', yTitle: 'Points vs strongest rival', baseline: true,
      series: [{ id: subjectId, name: 'Championship gap', type: 'bar',
        x: [`Low / ${low.event}`, 'Gap recovered', `Latest / ${latest.event}`],
        y: [low.margin, latest.margin - low.margin, latest.margin],
        base: [0, low.margin, 0], colors: ['--cp-danger', '--cp-accent', latest.margin >= 0 ? '--cp-success' : '--cp-danger'] }],
    }] }
  }

  const winRiders = data.standings.filter((rider) => rider.wins != null)
  const totalWins = winRiders.reduce((sum, rider) => sum + rider.wins!, 0)
  const consistency = kind === 'consistency' || (second?.wins != null && leader.wins != null && second.wins > leader.wins)
  if (consistency && leader.wins != null && leader.podiums != null && second?.wins != null && second.podiums != null) {
    const pair = [leader, second]
    return { layout: 'consistency', charts: [{
      id: 'wins-versus-points', title: 'Winning races is not the same as winning points',
      description: 'The leading riders placed by their GP wins and championship points.',
      note: 'Win counts come from imported scoring GP classifications and may be incomplete. Points keep their original standings source.',
      kind: 'scatter', xTitle: 'Imported GP wins', yTitle: 'Championship points',
      series: winRiders.slice(0, 10).map((rider) => ({
        id: rider.rider_id, name: rider.rider, type: 'scatter', x: [rider.wins!], y: [rider.points],
        hovertemplate: '%{x} imported GP wins<br>%{y:,.3~f} championship points<extra>%{fullData.name}</extra>',
      })),
    }, {
      id: 'podium-recipe', title: 'Two different routes to the podium',
      description: 'Wins and other podium finishes for the top two in the standings.',
      note: 'Only imported scoring GP finishes are counted. Sprint podiums and unknown historical finishes are not added.',
      kind: 'stacked', yTitle: 'Imported GP podiums', valueUnit: 'podiums', stacked: true,
      series: [{
        id: leader.rider_id, name: 'Wins', type: 'bar', x: pair.map((rider) => rider.rider), y: pair.map((rider) => rider.wins!),
      }, {
        id: second.rider_id, name: 'Other podiums', type: 'bar', x: pair.map((rider) => rider.rider),
        y: pair.map((rider) => rider.podiums! - rider.wins!),
      }],
    }] }
  }
  if (totalWins > 0 && leader.wins != null && (kind === 'dominance' || leader.wins >= totalWins / 2)) {
    const winners = winRiders.filter((rider) => rider.wins! > 0).sort((a, b) => b.wins! - a.wins!).slice(0, 8)
    return { layout: 'dominance', charts: [{
      id: 'victories', title: 'Who took the victories?',
      description: 'The riders with the most GP victories, rather than championship rank.',
      note: 'Imported scoring GP classifications only; the count is not a guarantee of full-season coverage.',
      kind: 'bar', xTitle: 'Imported GP wins', yTitle: '', valueUnit: 'wins',
      series: [{ id: leader.rider_id, name: 'Imported GP wins', type: 'bar', orientation: 'h',
        x: winners.map((rider) => rider.wins!), y: winners.map(label),
        text: winners.map((rider) => rider.rider), colors: winners.map((rider) => riderStyle(rider.rider_id).token),
        hovertemplate: '%{text}<br>%{x} imported GP wins<extra></extra>' }],
    }, {
      id: 'wins-share', title: 'One rider against the rest',
      description: 'The share of victories belonging to the top-ranked rider.',
      note: `${totalWins} imported GP wins form this denominator, not the number of scheduled weekends or official title points.`,
      kind: 'doughnut', yTitle: '', valueUnit: 'wins',
      series: [{ id: leader.rider_id, name: 'Wins', type: 'pie',
        x: [leader.rider, 'All other riders'], y: [leader.wins, totalWins - leader.wins],
        colors: ['--cp-accent', '--cp-text-muted'] }],
    }] }
  }
  if (second && second.gap != null && (kind === 'tie-break' || kind === 'close-finish' || second.gap <= 10)) {
    const historical = official && data.season < 1990 && data.rounds.length === 0
    return { layout: kind === 'tie-break' || second.gap === 0 ? 'tie-break' : 'close-finish', charts: [{
      id: 'leading-pair', title: second.gap === 0
        ? leader.position === second.position ? 'Same points. Shared rank.' : 'Same points. Different ranks.'
        : 'The separation at the top',
      description: official ? 'The official leading pair, with their ranks left intact.' : 'The leading pair in the imported standings.',
      note: official ? 'These are official positions, not a tie-break recalculated from the incomplete race archive.' : 'Imported totals; the comparison does not certify final championship positions.',
      kind: historical ? 'comparison' : 'scatter', xTitle: 'Championship points', yTitle: 'Championship rank', rank: true,
      series: [leader, second].map((rider) => ({
        id: rider.rider_id, name: rider.rider, type: 'scatter', x: [rider.points], y: [rider.position],
        hovertemplate: '%{x:,.3~f} points<br>Rank %{y}<extra>%{fullData.name}</extra>',
      })),
    }, margins(data)] }
  }
  const totalPoints = data.standings.reduce((sum, rider) => sum + rider.points, 0)
  if (totalPoints > 0 && data.standings.every((rider) => rider.points >= 0)) {
    const top = data.standings.slice(0, 3)
    const others = totalPoints - top.reduce((sum, rider) => sum + rider.points, 0)
    return { layout: 'standings', charts: [pointsBars(data), {
      id: 'points-share', title: 'The weight of the leading scores',
      description: 'The top three compared with the rest of the classified field.',
      note: 'Share of points in this standings table, not share of all points awarded in races. Historical dropped-score rules are preserved.',
      kind: 'doughnut', yTitle: '',
      series: [{ id: leader.rider_id, name: 'Classified points', type: 'pie',
        x: [...top.map(label), 'Rest of field'], y: [...top.map((rider) => rider.points), others],
        colors: [...top.map((rider) => riderStyle(rider.rider_id).token), '--cp-text-soft'] }],
    }] }
  }
  return { layout: 'standings', charts: [pointsBars(data), margins(data)] }
}
