import { useState } from 'react'
import type { ReactNode } from 'react'

export default function DetailSection({ title, note, children, className = '' }: {
  title: string; note: string; children: ReactNode; className?: string
}) {
  const [expanded, setExpanded] = useState(() => typeof window === 'undefined' || typeof window.matchMedia !== 'function' || !window.matchMedia('(max-width: 800px)').matches)
  return <details className={`panel detail-section ${className}`} open={expanded}
    onToggle={(event) => setExpanded(event.currentTarget.open)}>
    <summary aria-expanded={expanded}><span>{expanded ? 'Hide' : 'Show'} {title}</span><small>{note}</small></summary>
    <div className="detail-content">{children}</div>
  </details>
}
