export const categories = {
  premier: 'MotoGP / 500cc',
  intermediate: 'Moto2 / 250cc',
  lightweight: 'Moto3 / 125cc',
  '350cc': '350cc',
  '50cc': '50cc',
  '80cc': '80cc',
} as const

export type Category = keyof typeof categories

export function seasonCategory(category: Category, season: number) {
  if (category === 'premier') return season < 2002 ? '500cc' : 'MotoGP'
  if (category === 'intermediate') return season < 2010 ? '250cc' : 'Moto2'
  if (category === 'lightweight') return season < 2012 ? '125cc' : 'Moto3'
  return categories[category]
}

export function selectedView(params: URLSearchParams) {
  const requested = params.get('view')
  if (requested && ['riders', 'championship', 'results', 'laps', 'sectors'].includes(requested)) return requested as 'riders' | 'championship' | 'results' | 'laps' | 'sectors'
  if (params.has('event') || params.has('session')) return 'results'
  return params.has('season') || params.has('category') ? 'championship' : 'riders'
}

export function profilePath(current: URLSearchParams, values: Record<string, string>) {
  const next = new URLSearchParams(values)
  const theme = current.get('clawpilotTheme')
  if (theme) next.set('clawpilotTheme', theme)
  return `?${next}`
}

export function selectedCategory(value: string | null): Category | null {
  if (value === null) return 'premier'
  return Object.hasOwn(categories, value) ? value as Category : null
}

export function categoryPath(path: string, category: Category) {
  const url = new URL(path, 'https://paddock.invalid')
  url.searchParams.set('category', category)
  return `${url.pathname}${url.search}`
}

export function selectionParams(current: URLSearchParams, values: Record<string, string | null>) {
  const next = new URLSearchParams(current)
  const updates = { ...values }
  if ('category' in values) Object.assign(updates, { season: null, event: null, session: null })
  else if ('season' in values) Object.assign(updates, { event: null, session: null })
  else if ('event' in values && !('session' in values)) updates.session = null
  for (const [key, value] of Object.entries(updates)) {
    if (value == null) next.delete(key)
    else next.set(key, value)
  }
  return next
}

export function selectedSeason(params: URLSearchParams, seasons: number[]) {
  const requested = Number(params.get('season'))
  return params.has('season') && Number.isInteger(requested) && requested >= 1949 && requested <= 3000
    ? requested : seasons[0]
}

export function navigationPath(current: URLSearchParams, view: string) {
  const next = selectionParams(current, { view })
  if (!next.has('category')) next.set('category', 'premier')
  return `?${next}`
}
