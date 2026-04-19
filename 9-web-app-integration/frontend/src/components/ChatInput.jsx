import { useState } from 'react'

const TONES = ['Professional', 'Friendly', 'Formal', 'Casual', 'Confident']

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState('')
  const [tone, setTone] = useState('Professional')

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

 function submit() {
  if (!text.trim() || disabled) return
  onSend(text.trim(), tone)
  setText('')
}

  return (
    <div className="input-area">
      <label style={{ marginBottom: '8px', display: 'block' }}>
        Select tone:
      </label>

      <select
        value={tone}
        onChange={(e) => setTone(e.target.value)}
        disabled={disabled}
        style={{ marginBottom: '12px', padding: '8px', width: '100%' }}
      >
        {TONES.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Paste your message here..."
        disabled={disabled}
        rows={5}
        autoFocus
      />

      <button
        onClick={submit}
        disabled={disabled || !text.trim()}
        className="btn-send"
      >
        {disabled ? 'Rewriting...' : 'Rewrite Message'}
      </button>
    </div>
  )
}