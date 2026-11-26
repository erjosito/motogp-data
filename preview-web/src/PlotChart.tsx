import Plotly from 'plotly.js-basic-dist-min'
import { useEffect, useRef, useState } from 'react'
import type { Data, Layout } from 'plotly.js'
import { riderStyle } from './data'

export interface LineSeries {
  id: string
  name: string
  x: (number | string)[]
  y: (number | null)[]
  text?: string[]
}

export default function PlotChart({ series, yTitle, height = 340, baseline = false, theme, timing = false }: {
  series: LineSeries[]
  yTitle: string
  height?: number
  baseline?: boolean
  theme: string
  timing?: boolean
}) {
  const container = useRef<HTMLDivElement>(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    const element = container.current
    if (!element) return
    let active = true
    const style = getComputedStyle(document.documentElement)
    const color = (token: string) => style.getPropertyValue(token).trim()
    const data: Data[] = series.map((line) => {
      const rider = riderStyle(line.id)
      return {
        type: 'scatter', mode: 'lines+markers', name: line.name,
        x: line.x, y: line.y, text: line.text,
        line: { color: color(rider.token), width: 3, dash: rider.dash },
        marker: { size: 5 }, connectgaps: false,
        ...(baseline ? { fill: 'tozeroy', fillcolor: color('--cp-accent-soft') } : {}),
        hovertemplate: `%{x}<br>${timing ? '%{text}' : '%{y:.0f} points'}<extra>%{fullData.name}</extra>`,
      }
    })
    const layout: Partial<Layout> = {
      height, autosize: true, margin: { t: 20, r: 16, b: 76, l: 56 },
      paper_bgcolor: color('--cp-surface'), plot_bgcolor: color('--cp-surface'),
      font: { family: 'Segoe UI, Aptos, Calibri, sans-serif', color: color('--cp-text-muted'), size: 12 },
      xaxis: { showgrid: false, zeroline: false, nticks: 8, automargin: true, fixedrange: false },
      yaxis: {
        title: { text: yTitle, standoff: 14 }, gridcolor: color('--cp-border'),
        zeroline: false, automargin: true, rangemode: timing || baseline ? 'normal' : 'tozero',
      },
      hovermode: 'x unified',
      hoverlabel: { bgcolor: color('--cp-surface'), bordercolor: color('--cp-border'), font: { color: color('--cp-text') } },
      showlegend: series.length > 1, legend: { orientation: 'h', y: -0.23 },
      uirevision: `${theme}-${series.map((line) => line.id).join('-')}`,
      ...(baseline ? {
        shapes: [{
          type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 0, y1: 0,
          line: { color: color('--cp-text-soft'), dash: 'dot', width: 1 },
        }],
      } : {}),
    }
    Plotly.react(element, data, layout, {
      responsive: true, displaylogo: false, displayModeBar: false, scrollZoom: false,
    }).then(() => {
      if (active) setError(false)
    }).catch((failure: unknown) => {
      console.error('Chart rendering failed', failure)
      if (active) setError(true)
    })
    return () => {
      active = false
      Plotly.purge(element)
    }
  }, [series, yTitle, height, baseline, theme, timing])
  return <>
    {error && <p role="alert">This chart could not be rendered. The recorded values remain available in the tables.</p>}
    <div ref={container} style={{ width: '100%', height }} />
  </>
}
