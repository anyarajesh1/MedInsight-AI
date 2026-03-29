import { useState } from 'react'
import type { QueryResult } from '../types'

interface ResultSectionProps {
  result: QueryResult
}

type ViewMode = 'simplified' | 'technical'

export function ResultSection({ result }: ResultSectionProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('simplified')

  const hasError = !!result.error
  const displayAnswer = hasError
    ? result.error
    : result.answer
  const displaySources = result.sources ?? []

  return (
    <section
      className="section"
      aria-labelledby="result-heading"
      aria-live="polite"
    >
      <h2 id="result-heading" className="section-title">
        Result
      </h2>

      <div className="view-toggle" role="group" aria-label="Result view">
        <button
          type="button"
          aria-pressed={viewMode === 'simplified'}
          onClick={() => setViewMode('simplified')}
        >
          Simplified view
        </button>
        <button
          type="button"
          aria-pressed={viewMode === 'technical'}
          onClick={() => setViewMode('technical')}
        >
          Technical view
        </button>
      </div>

      <div
        className={`result-answer ${viewMode}`}
        role="region"
        aria-label={viewMode === 'simplified' ? 'Answer in plain language' : 'Answer with technical context'}
      >
        {viewMode === 'simplified'
          ? displayAnswer
          : result.technical_context_preview || displayAnswer}
      </div>

      {!hasError && displaySources.length > 0 && (
        <div className="sources-block" role="region" aria-label="Sources">
          <h3 className="sources-title">Source</h3>
          <ul className="sources-list">
            {displaySources.map((s, i) => (
              <li key={i}>
                {s.term ? `${s.term}: ` : ''}{s.source}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
