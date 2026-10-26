import { useEffect, useRef, useState } from 'react'
import type { PDFDocumentLoadingTask } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

export function PdfPreview({ encoded }: { encoded: string }) {
  const container = useRef<HTMLDivElement>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    // Each encoded PDF owns a drawing task. Cleanup destroys that task; checks
    // after page load/render also detect effects superseded by a newer preview.
    let cancelled = false
    let task: PDFDocumentLoadingTask | undefined
    const target = container.current
    target?.replaceChildren()
    async function draw() {
      setLoading(true)
      const { getDocument, GlobalWorkerOptions } = await import('pdfjs-dist')
      if (cancelled || !target) return
      GlobalWorkerOptions.workerSrc = workerUrl
      setError('')
      task = getDocument({ data: Uint8Array.from(atob(encoded), c => c.charCodeAt(0)), useSystemFonts: false })
      const pdf = await task.promise
      for (let number = 1; number <= pdf.numPages; number++) {
        const page = await pdf.getPage(number)
        if (cancelled) return
        const viewport = page.getViewport({ scale: 1.5 })
        const canvas = document.createElement('canvas')
        canvas.width = Math.ceil(viewport.width)
        canvas.height = Math.ceil(viewport.height)
        const context = canvas.getContext('2d')
        if (!context) throw new Error('Canvas preview is unavailable.')
        await page.render({ canvas, canvasContext: context, viewport }).promise
        if (cancelled) return
        const text = await page.getTextContent()
        canvas.setAttribute('role', 'img')
        canvas.setAttribute('aria-label', `Page ${number}: ${text.items.map(item => 'str' in item ? item.str : '').join(' ')}`)
        target.append(canvas)
      }
    }
    void draw().catch(() => { if (!cancelled) setError('Unable to display PDF. Use HTML preview or download the PDF.') }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true; void task?.destroy() }
  }, [encoded])
  return <>{loading && <p role="status">Drawing PDF pagesâ€¦</p>}{error && <p role="alert">{error}</p>}<div ref={container} className="pdf-pages" role="region" aria-label="Resume PDF preview" aria-busy={loading} tabIndex={0} /></>
}

