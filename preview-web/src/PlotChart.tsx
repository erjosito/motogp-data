import Plotly from 'plotly.js-basic-dist-min'
import { useEffect, useRef, useState } from 'react'
import type { Data, Layout } from 'plotly.js'
import { categoryTicks, riderStyle, statisticText } from './data'
import { SourceNote } from './PageNotes'

export interface ChartSeries {
  id: string
  name: string
  x: (number | string)[]
  y: (number | string | null)[]
  text?: string[]
  type?: 'line' | 'scatter' | 'bar' | 'pie'
  orientation?: 'h' | 'v'
  base?: number[]
  colors?: string[]
  hovertemplate?: string
  showValues?: boolean
}

export interface PlotChartProps {
  series: ChartSeries[]
  yTitle: string
  xTitle?: string
  height?: number
  baseline?: boolean
  theme: string
  timing?: boolean
  valueUnit?: string
  stacked?: boolean
  rank?: boolean
}

export default function PlotChart({ series, yTitle, xTitle, height = 340, baseline = false, theme, timing = false, valueUnit = 'points', stacked = false, rank = false }: PlotChartProps) {
  const container = useRef<HTMLDivElement>(null)
  const [error, setError] = useState(false)
  const [compact, setCompact] = useState(false)
  useEffect(() => {
    const element = container.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width > 0) setCompact(entry.contentRect.width < 560)
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  useEffect(() => {
    const element = container.current
    if (!element) return
    let active = true
    const style = getComputedStyle(document.documentElement)
    const color = (token: string) => style.getPropertyValue(token).trim()
    const data: Data[] = series.map((line): Data => {
      const rider = riderStyle(line.id)
      const markerColor = line.colors?.map(color) ?? color(rider.token)
      if (line.type === 'pie') return {
        type: 'pie', name: statisticText(line.name), labels: line.x, values: line.y, hole: 0.58,
        marker: { colors: line.colors?.map(color) }, sort: false,
        textinfo: 'percent', textposition: 'inside',
        hovertemplate: `%{label}<br>%{value:,.3~f} ${valueUnit}<br>%{percent}<extra></extra>`,
      }
      if (line.type === 'bar') {
        const bar: Data & { base?: number[] } = {
          type: 'bar', name: statisticText(line.name), x: line.x, y: line.y,
          text: line.showValues ? (line.orientation === 'h' ? line.x : line.y).map((value) => value == null ? '' : String(value)) : line.text,
          textposition: line.showValues ? 'outside' : 'none', cliponaxis: false,
          orientation: line.orientation ?? 'v', base: line.base,
          marker: { color: markerColor },
          hovertemplate: line.hovertemplate ? statisticText(line.hovertemplate) : (line.orientation === 'h'
            ? `%{y}<br>%{x:,.3~f} ${valueUnit}<extra>%{fullData.name}</extra>`
            : `%{x}<br>%{y:,.3~f} ${valueUnit}<extra>%{fullData.name}</extra>`),
        }
        return bar
      }
      return {
        type: 'scatter', mode: line.type === 'scatter' ? 'markers' : 'lines+markers', name: statisticText(line.name),
        x: line.x, y: line.y, text: line.text,
        line: { color: color(rider.token), width: 3, dash: rider.dash },
        marker: { size: line.type === 'scatter' ? 10 : 5, color: markerColor }, connectgaps: false,
        ...(baseline ? { fill: 'tozeroy', fillcolor: color('--cp-accent-soft') } : {}),
        hovertemplate: line.hovertemplate ? statisticText(line.hovertemplate) : `%{x}<br>${timing ? '%{text}' : `%{y:,.3~f} ${valueUnit}`}<extra>%{fullData.name}</extra>`,
      }
    })
    const ticks = categoryTicks(series, compact ? 4 : 8)
    const layout: Partial<Layout> = {
      height, autosize: true, margin: { t: 20, r: 16, b: series.length > 3 ? 140 : series.some((line) => line.type === 'pie') ? 110 : 76, l: 56 },
      paper_bgcolor: color('--cp-surface'), plot_bgcolor: color('--cp-surface'),
      font: { family: 'Segoe UI, Aptos, Calibri, sans-serif', color: color('--cp-text-muted'), size: 12 },
      xaxis: { title: xTitle ? { text: statisticText(xTitle), standoff: 12 } : undefined, showgrid: false, zeroline: false, nticks: compact ? 4 : 8, automargin: true, fixedrange: true,
        ...(ticks.length ? { tickmode: 'array', tickvals: ticks, ticktext: ticks.map((label) => compact && label.length > 22 ? `${label.slice(0, 20)}…` : label), tickangle: compact ? -25 : 'auto' } : {}),
      },
      yaxis: {
        title: { text: statisticText(yTitle), standoff: 14 }, gridcolor: color('--cp-border'),
        zeroline: false, automargin: true, fixedrange: true, rangemode: timing || baseline || rank ? 'normal' : 'tozero',
        ...(rank ? { autorange: 'reversed', dtick: 1 } : {}),
        ...(series.some((line) => line.orientation === 'h') ? { autorange: 'reversed' } : {}),
      },
      hovermode: series.some((line) => line.type && line.type !== 'line') ? 'closest' : 'x unified',
      dragmode: false,
      hoverlabel: { bgcolor: color('--cp-surface'), bordercolor: color('--cp-border'), font: { color: color('--cp-text') } },
      showlegend: series.length > 1 || series.some((line) => line.type === 'pie'), legend: { orientation: 'h', y: -0.23 },
      barmode: stacked ? 'stack' : 'group',
      uirevision: `${theme}-${series.map((line) => line.id).join('-')}`,
      ...(baseline ? {
        shapes: [{
          type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 0, y1: 0,
          line: { color: color('--cp-text-soft'), dash: 'dot', width: 1 },
        }],
      } : {}),
    }
    Plotly.react(element, data, layout, {
      responsive: true, displaylogo: false, displayModeBar: false, scrollZoom: false, doubleClick: false,
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
  }, [series, yTitle, xTitle, height, baseline, theme, timing, valueUnit, stacked, rank, compact])
  return <>
    {error && <p role="alert">This chart could not be rendered. The values remain available in the tables.</p>}
    <div ref={container} style={{ width: '100%', height }} />
    {compact && <SourceNote><p>Axis labels are reduced on narrow charts; every point remains plotted. Full labels are available on hover or tap.</p></SourceNote>}
  </>
}
