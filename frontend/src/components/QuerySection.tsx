import { useState, useRef } from 'react'

interface QuerySectionProps {
  onSubmit: (question: string) => void
  loading: boolean
}

export function QuerySection({ onSubmit, loading }: QuerySectionProps) {
  const [question, setQuestion] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const q = question.trim()
    if (q && !loading) onSubmit(q)
  }

  return (
    <section className="section" aria-labelledby="query-heading">
      <h2 id="query-heading" className="section-title">
        Ask a question
      </h2>
      <form className="query-form" onSubmit={handleSubmit}>
        <label htmlFor="question-input">
          Your question about your labs or general medical terms
        </label>
        <textarea
          id="question-input"
          ref={textareaRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What does elevated creatinine mean?"
          disabled={loading}
          rows={3}
          aria-describedby="question-hint"
        />
        <span id="question-hint" className="visually-hidden">
          Answers are based on the medical dictionary and your uploaded document, with sources cited.
        </span>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={!question.trim() || loading}
          aria-busy={loading}
        >
          {loading ? 'Searching…' : 'Get answer'}
        </button>
      </form>
    </section>
  )
}
