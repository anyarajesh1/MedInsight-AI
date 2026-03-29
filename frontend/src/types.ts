export interface SourceItem {
  source: string
  term?: string
}

export interface QueryResult {
  answer: string
  sources: SourceItem[]
  technical_context_preview?: string
  error?: string
}

export interface UploadResponse {
  doc_id: string
  chunks_indexed: number
  used_ocr: boolean
  message: string
}
