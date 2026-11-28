import type { Category } from './selection'

export interface GrandPrix {
  event_id: string
  short_name: string
  event_name: string
  circuit_name: string | null
  country_name: string | null
  date_end: string | null
}

export interface Session {
  session_id: string
  session_type: string
  session_label: string
  session_date: string | null
  weather: string | null
  air_temp: string | null
  ground_temp: string | null
}

export interface Rider {
  rider_id: string
  rider: string
  number: number | null
  number_source?: 'rider-record' | 'latest-classification' | 'reviewed-identity' | null
  number_season?: number | null
  number_category?: string | null
}

export interface RiderSeason {
  season: number
  category: Category
  gp_appearances: number
  gp_wins: number
  gp_podiums: number
  sprint_wins: number
  sprint_appearances: number
  position: number | null
  points: number | null
  is_final: boolean
  source_url: string | null
}

export interface RiderProfile {
  rider: Rider
  headline: string
  summary: string
  totals: Pick<RiderSeason, 'gp_appearances' | 'gp_wins' | 'gp_podiums' | 'sprint_wins' | 'sprint_appearances'> & { titles: number }
  seasons: RiderSeason[]
  titles: RiderSeason[]
  best_season: RiderSeason | null
  venues: { venue: string; appearances: number; wins: number; podiums: number }[]
  first_season: number
  latest_season: number
}

export interface Result extends Rider {
  source_kind: 'official-api' | 'official-api+external' | 'external'
  position: number | null
  team: string | null
  constructor: string | null
  total_laps: number | null
  time_text: string | null
  gap_first: string | null
  best_lap_seconds: number | null
  top_speed: number | null
  points: number | null
  status: string | null
  finish_gap_seconds?: number | null
  finish_gap_reason?: string | null
}

export interface Lap extends Rider {
  lap_number: number
  lap_seconds: number | null
  sectors: (number | null)[]
  speed_kmh: number | null
  is_pit: boolean
  run_number: number | null
  front_tyre: string | null
  rear_tyre: string | null
}

export interface Analysis {
  session: Session & Omit<GrandPrix, 'date_end'> & { season_year: number }
  results: Result[]
  laps: Lap[]
}

export interface Round {
  session_id: string
  event_id: string
  event: string
  type: string
  label: string
  date: string | null
}

export interface ComebackPoint extends Round {
  points: number
  margin: number
}

export interface Standing extends Rider {
  source_url?: string
  position: number
  points: number
  gap: number | null
  wins: number | null
  podiums: number | null
  team: string | null
  constructor: string | null
  series: number[]
}

export interface Championship {
  season: number
  category: Category
  standings: Standing[]
  rounds: Round[]
  gp_results: number
  weekends: number
  scoring_sessions: number
  standings_source: 'official' | 'computed'
  is_final: boolean
  external_sources_used: boolean
  official_points_inconsistent: boolean
  points_warning: string | null
  points_correction?: { note: string; source_url: string; corroborating_url: string } | null
  coverage?: {
    sessions: number
    classified_sessions: number
    classification_rows: number
    lap_rows: number
  }
  story: {
    kind: 'standings' | 'coverage' | 'comeback' | 'dominance' | 'consistency' | 'late-surge' | 'close-finish' | 'tie-break'
    headline: string
    accent: string
    summary: string
    metric_label: string
    metric: number
    metric_note: string
    context_url: string | null
  }
  comeback: {
    rider_id: string
    history: ComebackPoint[]
    low: ComebackPoint
    max_deficit: number
    current_margin: number
    recovered: number
    verified_102: boolean
  } | null
}
