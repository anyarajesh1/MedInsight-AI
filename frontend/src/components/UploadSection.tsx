import { useState, useRef, useCallback } from 'react'
import type { UploadResponse } from '../types'

interface UploadSectionProps {
  onSuccess: (message: string) => void
  uploadStatus: string | null
}

export function UploadSection({ onSuccess, uploadStatus }: UploadSectionProps) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const uploadFile = useCallback(
    async (file: File) => {
      if (!file.type.includes('pdf')) {
        setError('Please upload a PDF file.')
        return
      }
      setError(null)
      setUploading(true)
      try {
        const formData = new FormData()
        formData.append('file', file)
        const res = await fetch('/api/upload', {
          method: 'POST',
          body: formData,
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(data.detail || res.statusText)
        const msg = (data as UploadResponse).message
        onSuccess(msg + (data.used_ocr ? ' (OCR was used for scanned pages.)' : ''))
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Upload failed')
      } finally {
        setUploading(false)
      }
    },
    [onSuccess]
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const file = e.dataTransfer.files?.[0]
      if (file) uploadFile(file)
    },
    [uploadFile]
  )

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(true)
  }, [])

  const onDragLeave = useCallback(() => {
    setDragging(false)
  }, [])

  const onFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) uploadFile(file)
      e.target.value = ''
    },
    [uploadFile]
  )

  const onClick = () => inputRef.current?.click()

  return (
    <section className="section" aria-labelledby="upload-heading">
      <h2 id="upload-heading" className="section-title">
        Upload lab PDF
      </h2>
      <div
        className={`upload-zone ${dragging ? 'dragging' : ''}`}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={onClick}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onClick()
          }
        }}
        role="button"
        tabIndex={0}
        aria-label="Upload PDF file. Drop file here or click to select."
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          onChange={onFileChange}
          disabled={uploading}
          aria-describedby="upload-desc"
        />
        <span id="upload-desc">
          {uploading
            ? 'Uploading…'
            : 'Drop your medical lab PDF here, or click to choose a file'}
        </span>
      </div>
      {error && (
        <p className="status-msg error" role="alert">
          {error}
        </p>
      )}
      {uploadStatus && (
        <p className="status-msg success" role="status">
          {uploadStatus}
        </p>
      )}
    </section>
  )
}
