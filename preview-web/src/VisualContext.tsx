import { useResource } from './api'
import { useState } from 'react'
import { appPath } from './paths'
import type { Rider } from './types'

export interface RiderEnrichment {
  status: 'available' | 'not_collected'
  profile: {
    rider_id: string
    biography: { birth_date: string | null; birth_city: string | null; birth_country: string | null; height_cm: number | null }
    source: { source_url: string; retrieved_at: string }
  } | null
}

export interface RiderPortrait {
  status: 'available' | 'not_collected'
  portrait: {
    rider_id: string; season: number; team_name: string; credit: string; source_page: string
    license: string; license_url: string; changes: string
    images: { url: string; width: number; height: number }[]
  } | null
}

export interface NumberArtwork {
  artwork: { season: number; category: string; number: number; source_url: string; url: string }[]
}

function NumberArtworkImage({ item, name }: { item: NumberArtwork['artwork'][number]; name: string }) {
  const [failed, setFailed] = useState(false)
  return failed ? <span role="alert">Artwork unavailable</span> : <img src={appPath(item.url)}
    alt={`${name}, number ${item.number}, ${item.season} ${item.category}`} onError={() => setFailed(true)} />
}

export function RiderNumberArtwork({ data, name }: { data: NumberArtwork; name: string }) {
  if (!data.artwork.length) return null
  return <details className="number-artwork">
    <summary>Rider number artwork</summary>
    <div className="number-artwork-grid">{data.artwork.map((item) =>
      <figure key={`${item.season}-${item.category}-${item.number}`}>
        <NumberArtworkImage item={item} name={name} />
        <figcaption>{item.season} · {item.category} · #{item.number} · <a href={item.source_url} target="_blank" rel="noreferrer">Source</a></figcaption>
      </figure>)}</div>
  </details>
}

export function RiderIdentity({ rider, enrichment, media, season }: {
  rider: Rider; enrichment?: RiderEnrichment | null; media?: RiderPortrait | null; season?: number
}) {
  const [failedImage, setFailedImage] = useState<string | null>(null)
  const profile = enrichment?.status === 'available' && enrichment.profile?.rider_id === rider.rider_id ? enrichment.profile : null
  const portrait = media?.status === 'available' && media.portrait?.rider_id === rider.rider_id
    && (season == null || season === media.portrait.season) ? media.portrait : null
  const image = portrait?.images.at(-1)
  const initials = rider.rider.trim().split(/\s+/).map((part) => part[0]).slice(0, 2).join('')
  const bio = profile?.biography
  const birthday = bio?.birth_date ? new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${bio.birth_date}T00:00:00Z`)) : null
  return <figure className="rider-identity">
    <div className="rider-portrait">
      {image && portrait && failedImage !== image.url ? <img src={appPath(image.url)}
        srcSet={portrait.images.map((item) => `${appPath(item.url)} ${item.width}w`).join(',')} sizes="(max-width: 600px) 108px, 128px"
        width={image.width} height={image.height} alt={`${rider.rider}, ${portrait.season} portrait`}
        onError={() => setFailedImage(image.url)} /> : <div className="rider-initials" aria-label={`${rider.rider}, initials`}>{initials}<small>#{rider.number ?? '—'}</small></div>}
    </div>
    <div><p className="eyebrow">THE PERSON BEHIND THE NUMBER</p>
      <dl className="visual-facts">
        <div><dt>Race number</dt><dd>{rider.number ?? '—'}</dd></div>
        {birthday && <div><dt>Born</dt><dd className="fact-text">{birthday}</dd></div>}
        {(bio?.birth_city || bio?.birth_country) && <div><dt>Hometown</dt><dd className="fact-text">{[bio.birth_city, bio.birth_country].filter(Boolean).join(', ')}</dd></div>}
        {bio?.height_cm != null && <div><dt>Reported height</dt><dd>{bio.height_cm} <small>cm</small></dd></div>}
      </dl>
      {profile && <p className="visual-credit"><a href={profile.source.source_url} target="_blank" rel="noreferrer">Biography source</a> · retrieved {profile.source.retrieved_at.slice(0, 10)}.<br />Height is reported at retrieval, not a historical measurement.</p>}
    </div>
    {portrait && image && <figcaption className="visual-credit">{portrait.season} · {portrait.team_name} ·{' '}
      <a href={portrait.source_page} target="_blank" rel="noreferrer">{portrait.credit}</a> · <a href={portrait.license_url} target="_blank" rel="noreferrer">{portrait.license}</a>
      <details><summary>Image adapted: oriented, cropped, resized and converted to WebP</summary>{portrait.changes}</details>
      {failedImage === image.url && <span role="alert">Portrait unavailable; showing initials.</span>}
    </figcaption>}
  </figure>
}

export function RiderVisualContext({ rider }: { rider: Rider }) {
  const enrichment = useResource<RiderEnrichment>(`/api/riders/${encodeURIComponent(rider.rider_id)}/enrichment`)
  const portrait = useResource<RiderPortrait>(`/api/riders/${encodeURIComponent(rider.rider_id)}/portrait?season=2026&category=premier`)
  const numbers = useResource<NumberArtwork>(`/api/riders/${encodeURIComponent(rider.rider_id)}/number-art`)
  return <>
    <RiderIdentity key={rider.rider_id} rider={rider} enrichment={enrichment.data} media={portrait.data} />
    {numbers.data && <RiderNumberArtwork data={numbers.data} name={rider.rider} />}
    {enrichment.error && <p className="panel-note" role="alert">Biography could not be loaded. <button className="text-button" onClick={enrichment.retry}>Try again</button></p>}
    {portrait.error && <p className="panel-note" role="alert">Portrait could not be loaded. <button className="text-button" onClick={portrait.retry}>Try again</button></p>}
    {numbers.error && <p className="panel-note" role="alert">Number artwork could not be loaded. <button className="text-button" onClick={numbers.retry}>Try again</button></p>}
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
      <p className="panel-note">{season === c.reference_season ? 'Current-layout context' : `Current-layout reference, not a reconstruction of the ${season} track`}. No sector boundaries, start line or direction inferred.</p>
      <p className="visual-credit"><a href={c.facts_source} target="_blank" rel="noreferrer">Circuit facts</a> · verified {c.facts_verified}<br />
        Outline: <a href={c.outline_source} target="_blank" rel="noreferrer">© OpenStreetMap contributors</a> · <a href={c.outline_license_url} target="_blank" rel="noreferrer">ODbL 1.0</a> · projected and scaled</p>
    </div>
  </section>
}

export function CircuitContext({ name, season }: { name: string; season: number }) {
  const resource = useResource<CircuitContextData>(`/api/circuit-context?name=${encodeURIComponent(name)}`)
  if (resource.error) return <p className="panel-note" role="alert">Circuit context could not be loaded. <button className="text-button" onClick={resource.retry}>Try again</button></p>
  return resource.data ? <CircuitGraphic data={resource.data} season={season} /> : null
}
