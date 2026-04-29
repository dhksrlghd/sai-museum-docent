import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { streamChat } from '../lib/api'

const MODES = [
  { id: 'adult', label: '성인' },
  { id: 'kid', label: '어린이' },
  { id: 'foreign', label: 'Foreign' },
]

const PLACEHOLDERS = {
  adult: '예) 기영회도가 무엇인지 궁금해요',
  kid: '예) 달항아리가 뭐예요?',
  foreign: 'e.g. Tell me about the moon jar',
}

const INTRO = {
  adult: '큐레이터 해설을 바탕으로 답해드립니다. 무엇이 궁금하세요?',
  kid: '안녕! 박물관 작품에 대해 무엇이든 물어봐 주세요.',
  foreign: 'Ask me anything about works in the National Museum of Korea.',
}

export default function AskBox({
  variant = 'standalone',  // 'standalone' | 'panel'
  initialQuery = '',
  initialMode = 'adult',
}) {
  const [mode, setMode] = useState(initialMode)
  const [input, setInput] = useState(initialQuery)
  const [messages, setMessages] = useState([
    { role: 'assistant', text: INTRO[initialMode], sources: [], intro: true },
  ])
  const [streaming, setStreaming] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    setMessages((prev) => {
      const next = [...prev]
      if (next.length && next[0].intro) next[0] = { ...next[0], text: INTRO[mode] }
      return next
    })
  }, [mode])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  async function send(q = input) {
    const text = q.trim()
    if (!text || streaming) return
    setInput('')
    setMessages((prev) => [
      ...prev,
      { role: 'user', text },
      { role: 'assistant', text: '', sources: [], pending: true },
    ])
    setStreaming(true)
    try {
      await streamChat(text, mode, {
        onSources: (s) => setMessages((p) => updateLastBot(p, { sources: s })),
        onToken: (t) => setMessages((p) => updateLastBot(p, { append: t })),
        onError: (err) =>
          setMessages((p) => updateLastBot(p, { text: `(오류: ${err})`, pending: false })),
      })
    } finally {
      setMessages((p) => updateLastBot(p, { pending: false }))
      setStreaming(false)
    }
  }

  const containerCls =
    variant === 'panel'
      ? 'flex flex-col h-full bg-white border border-[var(--color-paper-200)] rounded-lg'
      : 'flex flex-col h-full bg-white border border-[var(--color-paper-200)] rounded-xl shadow-sm'

  return (
    <div className={containerCls}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-paper-200)]">
        <div className="text-sm font-semibold text-[var(--color-ink-900)]">
          AI 도슨트
        </div>
        <div className="inline-flex rounded-full p-1 bg-[var(--color-paper-100)] gap-1 text-xs">
          {MODES.map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={
                'px-3 py-1 rounded-full transition ' +
                (m.id === mode
                  ? 'bg-[var(--color-vermilion-500)] text-white'
                  : 'text-[var(--color-ink-500)] hover:text-[var(--color-ink-900)]')
              }
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4">
        {messages.map((m, i) => (
          <Bubble key={i} m={m} />
        ))}
      </div>

      <Composer value={input} onChange={setInput} onSend={() => send()} disabled={streaming} placeholder={PLACEHOLDERS[mode]} />
    </div>
  )
}

function Bubble({ m }) {
  const isUser = m.role === 'user'
  const showDots = !isUser && m.pending && !m.text
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={
          'max-w-[90%] rounded-2xl px-4 py-3 leading-relaxed whitespace-pre-wrap text-[15px] ' +
          (isUser
            ? 'bg-[var(--color-vermilion-500)] text-white rounded-br-sm'
            : 'bg-[var(--color-paper-100)] text-[var(--color-ink-900)] rounded-bl-sm')
        }
      >
        {showDots ? <Dots /> : m.text}
        {!isUser && m.sources?.length > 0 && <Sources items={m.sources} />}
      </div>
    </div>
  )
}

function Sources({ items }) {
  return (
    <div className="mt-3 pt-3 border-t border-[var(--color-paper-200)]">
      <div className="text-[11px] uppercase tracking-wider text-[var(--color-ink-500)] mb-2">
        참고한 작품
      </div>
      <div className="grid grid-cols-2 gap-2">
        {items.slice(0, 4).map((s) => (
          <Link
            key={s.relic_id}
            to={`/work/${s.relic_id}`}
            className="flex items-center gap-2 p-1.5 rounded-md bg-white border border-[var(--color-paper-200)] hover:border-[var(--color-ink-500)] transition"
          >
            <div className="w-10 h-10 shrink-0 rounded bg-[var(--color-paper-100)] overflow-hidden">
              {s.thumbnail_url && (
                <img
                  src={s.thumbnail_url}
                  alt=""
                  className="w-full h-full object-cover"
                  onError={(e) => { e.currentTarget.style.display = 'none' }}
                />
              )}
            </div>
            <div className="min-w-0 text-[12px]">
              <div className="font-semibold text-[var(--color-ink-900)] line-clamp-1">{s.title}</div>
              <div className="text-[10px] text-[var(--color-ink-500)] line-clamp-1">
                {s.curator || ''}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

function Dots() {
  return (
    <span className="inline-flex gap-1 items-center h-5 align-middle">
      {[0, 150, 300].map((d) => (
        <span
          key={d}
          className="w-1.5 h-1.5 bg-[var(--color-ink-500)] rounded-full inline-block animate-pulse"
          style={{ animationDelay: `${d}ms` }}
        />
      ))}
    </span>
  )
}

function Composer({ value, onChange, onSend, disabled, placeholder }) {
  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }
  return (
    <div className="border-t border-[var(--color-paper-200)] p-3">
      <div className="flex items-end gap-2 bg-[var(--color-paper-100)] border border-[var(--color-paper-200)] rounded-xl px-3 py-2 focus-within:border-[var(--color-vermilion-500)] transition-colors">
        <textarea
          rows={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKey}
          placeholder={placeholder}
          className="flex-1 resize-none bg-transparent outline-none text-[var(--color-ink-900)] py-1 placeholder:text-[var(--color-ink-500)] max-h-32 text-sm"
        />
        <button
          onClick={onSend}
          disabled={disabled || !value.trim()}
          className="shrink-0 rounded-full px-3 py-1.5 text-sm font-medium bg-[var(--color-vermilion-500)] text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[var(--color-vermilion-600)] transition"
        >
          전송
        </button>
      </div>
    </div>
  )
}

function updateLastBot(messages, patch) {
  const next = [...messages]
  for (let i = next.length - 1; i >= 0; i--) {
    if (next[i].role === 'assistant') {
      const m = { ...next[i] }
      if (patch.sources) m.sources = patch.sources
      if (patch.text !== undefined) m.text = patch.text
      if (patch.append) m.text = (m.text || '') + patch.append
      if (patch.pending !== undefined) m.pending = patch.pending
      next[i] = m
      return next
    }
  }
  return messages
}
