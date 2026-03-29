import { useState, useCallback } from 'react'
import './App.css'
import { UploadSection } from './components/UploadSection'
import { QuerySection } from './components/QuerySection'
import { ResultSection } from './components/ResultSection'
import type { QueryResult } from './types'

function App() {
  const [uploadStatus, setUploadStatus] = useState<string | null>(null)
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null)
  const [queryLoading, setQueryLoading] = useState(false)

  const onUploadSuccess = useCallback((message: string) => {
    setUploadStatus(message)
    setQueryResult(null)
  }, [])

  const onQuerySubmit = useCallback(async (question: string) => {
    setQueryLoading(true)
    setQueryResult(null)
    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || res.statusText)
      }
      const data = await res.json()
      setQueryResult(data)
    } catch (e) {
      setQueryResult({
        answer: '',
        sources: [],
        technical_context_preview: '',
        error: e instanceof Error ? e.message : 'Query failed',
      })
    } finally {
      setQueryLoading(false)
    }
  }, [])

  return (
    <div className="app">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <header className="app-header" role="banner">
        <h1 className="app-title">Med Insight AI</h1>
        <p className="app-tagline">
          Privacy-first medical document analysis with cited sources
        </p>
      </header>

      <div className="privacy-notice" role="region" aria-label="Privacy notice">
        <strong>Privacy-first:</strong> Your documents are processed with PII redaction before analysis.
        We do not store your original PDFs; only anonymized text is used to answer your questions.
      </div>

      <main id="main-content" role="main">
        <UploadSection onSuccess={onUploadSuccess} uploadStatus={uploadStatus} />
        <QuerySection onSubmit={onQuerySubmit} loading={queryLoading} />
        {queryResult && <ResultSection result={queryResult} />}
      </main>
    </div>
  )
}

export default App
