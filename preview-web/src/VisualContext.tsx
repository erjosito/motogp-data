import { useResource } from './api'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { appPath } from './paths'
import { SourceNote } from './PageNotes'
import type { Rider } from './types'
import type { Category } from './selection'

export interface RiderEnrichment {
  status: 'available' | 'not_collected'
  profile: {
    rider_id: string
    biography: { birth_date: string | null; birth_city: string | null; birth_country: string | null; height_cm: number | null }
    source: { source_url: string; retrieved_at: string }
  } | null
}

export interface NumberArtwork {
  artwork: { season: number; category: string; number: number; source_url: string; url: string }[]
}

interface NumberScope { rider: Rider; season?: number; category?: Category; fallback?: ReactNode }

function selectedNumberArtwork(data?: NumberArtwork | null) {
  return [...(data?.artwork ?? [])].sort((a, b) => b.season - a.season
    || a.category.localeCompare(b.category) || a.number - b.number || a.url.localeCompare(b.url))[0]
}

export function NumberArtworkAccent({ data }: { data?: NumberArtwork | null }) {
  const [failedImage, setFailedImage] = useState<string | null>(null)
  const item = selectedNumberArtwork(data)
  if (!item || failedImage === item.url) return null
  return <div className="number-artwork-accent" aria-hidden="true">
    <img src={appPath(item.url)} alt="" draggable={false} onError={() => {
      console.error('Decorative number artwork could not be loaded')
      setFailedImage(item.url)
    }} />
  </div>
}

export function NumberMark({ rider, data, fallback }: NumberScope & { data?: NumberArtwork | null }) {
  const [failedImage, setFailedImage] = useState<string | null>(null)
  const item = selectedNumberArtwork(data)
  const failed = item && failedImage === item.url
  return <>
    {item && !failed ? <img className="number-mark" src={appPath(item.url)}
      alt={`${rider.rider}, number ${item.number}, ${item.season} ${item.category} design`}
      onError={() => setFailedImage(item.url)} /> : fallback !== undefined ? fallback : <span aria-label={rider.number == null ? 'Race number unavailable' : `Rider number ${rider.number}`}>{rider.number == null ? '—' : `#${rider.number}`}</span>}
    {item && <SourceNote><p>{rider.rider} · number design: {item.season} · {item.category} · #{item.number} · <a href={item.source_url} target="_blank" rel="noreferrer">Source</a></p>
      {failed && <p role="alert">Number design could not be loaded; showing the plain number.</p>}</SourceNote>}
  </>
}

export function RiderNumber({ rider, fallback }: NumberScope) {
  const resource = useResource<NumberArtwork>(`/api/riders/${encodeURIComponent(rider.rider_id)}/number-identity`)
  return <><NumberMark rider={rider} data={resource.data} fallback={fallback} />
    {resource.error && <SourceNote><p role="alert">{rider.rider}: number design could not be loaded; showing the plain number. <button className="text-button" onClick={resource.retry}>Try again</button></p></SourceNote>}
  </>
}

export function RiderIdentity({ rider, enrichment }: {
  rider: Rider; enrichment?: RiderEnrichment | null
}) {
  const profile = enrichment?.status === 'available' && enrichment.profile?.rider_id === rider.rider_id ? enrichment.profile : null
  const bio = profile?.biography
  const birthday = bio?.birth_date ? new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${bio.birth_date}T00:00:00Z`)) : null
  return <div className="rider-identity">
    <div><p className="eyebrow">THE PERSON BEHIND THE NUMBER</p>
      <dl className="visual-facts">
        <div><dt>Race number</dt><dd>{rider.number ?? '—'}</dd></div>
        {birthday && <div><dt>Born</dt><dd className="fact-text">{birthday}</dd></div>}
        {(bio?.birth_city || bio?.birth_country) && <div><dt>Hometown</dt><dd className="fact-text">{[bio.birth_city, bio.birth_country].filter(Boolean).join(', ')}</dd></div>}
        {bio?.height_cm != null && <div><dt>Height</dt><dd>{bio.height_cm} <small>cm</small></dd></div>}
      </dl>
      {profile && <SourceNote><p>{rider.rider} · <a href={profile.source.source_url} target="_blank" rel="noreferrer">Biography source</a> · retrieved {profile.source.retrieved_at.slice(0, 10)}.<br />Height is reported at retrieval, not a historical measurement.</p></SourceNote>}
    </div>
  </div>
}

export function RiderVisualContext({ rider }: { rider: Rider }) {
  const enrichment = useResource<RiderEnrichment>(`/api/riders/${encodeURIComponent(rider.rider_id)}/enrichment`)
  return <>
    <RiderIdentity key={rider.rider_id} rider={rider} enrichment={enrichment.data} />
    {enrichment.error && <p className="panel-note" role="alert">Biography could not be loaded. <button className="text-button" onClick={enrichment.retry}>Try again</button></p>}
  </>
}

export interface CircuitContextData {
  status: 'available' | 'not_collected'
  circuit: {
    id: string; name: string; length_km: number; turns: number; reference_season: number
    facts_source: string; facts_verified: string; outline_source: string; outline_license_url: string
    outline: [number, number][]
  } | null
}

export function CircuitGraphic({ data, season }: { data: CircuitContextData; season: number }) {
  const c = data.circuit
  if (!c || data.status !== 'available') return null
  return <section className="panel circuit-context" aria-label="Circuit context">
    <svg viewBox="0 0 320 320" role="img" aria-label={`${c.name}: current circuit outline, not a sector map`}>
      <polyline points={c.outline.map((point) => point.join(',')).join(' ')} />
    </svg>
    <div><p className="eyebrow">KNOW THE VENUE / {c.reference_season} REFERENCE</p><h2>{c.name}</h2>
      <dl className="visual-facts"><div><dt>Length</dt><dd>{c.length_km.toFixed(3)} <small>km</small></dd></div>
        <div><dt>Corners</dt><dd>{c.turns}</dd></div></dl>
      <SourceNote><p>{c.name}: {season === c.reference_season ? 'Current-layout context' : `Current-layout reference, not a reconstruction of the ${season} track`}. No sector boundaries, start line or direction inferred.</p>
      <p className="visual-credit"><a href={c.facts_source} target="_blank" rel="noreferrer">Circuit facts</a> · verified {c.facts_verified}<br />
        Outline: <a href={c.outline_source} target="_blank" rel="noreferrer">© OpenStreetMap contributors</a> · <a href={c.outline_license_url} target="_blank" rel="noreferrer">ODbL 1.0</a> · projected and scaled</p></SourceNote>
    </div>
  </section>
}

export function CircuitContext({ name, season }: { name: string; season: number }) {
  const resource = useResource<CircuitContextData>(`/api/circuit-context?name=${encodeURIComponent(name)}`)
  if (resource.error) return <p className="panel-note" role="alert">Circuit context could not be loaded. <button className="text-button" onClick={resource.retry}>Try again</button></p>
  return resource.data ? <CircuitGraphic data={resource.data} season={season} /> : null
}
