import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'

const NotesTarget = createContext<HTMLDivElement | null | undefined>(undefined)

export function PageNotes({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<HTMLDivElement | null>(null)
  return <NotesTarget.Provider value={target}>
    {children}
    <section className="page-notes" id="page-notes" aria-labelledby="page-notes-title">
      <h2 id="page-notes-title">Sources, credits &amp; data notes</h2>
      <p>Data: official MotoGP results API, timing PDFs and labeled historical archives.
        Statistics describe the available archive, not certified complete-career totals.
        Missing values are not zero results. Final standings and standings to date remain distinct.</p>
      <div ref={setTarget} />
    </section>
  </NotesTarget.Provider>
}

export function SourceNote({ children }: { children: ReactNode }) {
  const target = useContext(NotesTarget)
  const note = <div className="source-note">{children}</div>
  return target === undefined ? note : target ? createPortal(note, target) : null
}
