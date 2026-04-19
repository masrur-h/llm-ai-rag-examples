import { useState } from 'react'
import ChatInput from './components/ChatInput'

const API_BASE = 'http://localhost:8000'

export default function App() {
  const [result, setResult] = useState('')
  const [originalText, setOriginalText] = useState('')
  const [selectedTone, setSelectedTone] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [formKey, setFormKey] = useState(0)
  const [copied, setCopied] = useState(false)

  async function handleRewrite(text, tone) {
    if (!text.trim() || loading) return

    setLoading(true)
    setError('')
    setResult('')
    setCopied(false)
    setOriginalText(text)
    setSelectedTone(tone)

    try {
      const response = await fetch(`${API_BASE}/rewrite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, tone }),
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || `Server error: ${response.status}`)
      }

      const data = await response.json()
      setResult(data.rewritten_text)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function clearAll() {
    setResult('')
    setOriginalText('')
    setSelectedTone('')
    setError('')
    setCopied(false)
    setFormKey((prev) => prev + 1)
  }

  async function copyResult() {
    if (!result) return
    await navigator.clipboard.writeText(result)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="app-shell">
      <div className="app">
        <header className="hero">
          <div>
            <p className="eyebrow">AI-Powered Web App</p>
            <h1>Message Rewriter</h1>
            <p className="hero-text">
              Rewrite any message in a different tone using Gemini.
            </p>
          </div>

          <div className="page-actions">
            <button onClick={clearAll} className="btn-clear" disabled={loading}>
              Clear
            </button>
          </div>
        </header>

        {error && <div className="error-banner">{error}</div>}

        <section className="panel">
          <div className="panel-header">
            <h2>Rewrite a message</h2>
            <p>Choose a tone, paste your text, and generate a cleaner version.</p>
          </div>

          <ChatInput key={formKey} onSend={handleRewrite} disabled={loading} />
        </section>

        {(originalText || result) && (
          <section className="output-grid">
            <div className="output-card">
              <div className="card-header">
                <h3>Original Message</h3>
                {selectedTone && <span className="tone-badge">{selectedTone}</span>}
              </div>
              <div className="message user-message">{originalText}</div>
            </div>

            <div className="output-card">
              <div className="card-header">
                <h3>Rewritten Message</h3>
                {result && (
                  <button onClick={copyResult} className="btn-clear" type="button">
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                )}
              </div>
              <div className="message assistant-message">
                {loading ? 'Rewriting your message...' : result || 'Your rewritten message will appear here.'}
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  )
}