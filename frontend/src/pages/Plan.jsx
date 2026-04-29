import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { streamPlan } from '../lib/api'

const DURATIONS = [
  { v: 30, label: '30분 가볍게' },
  { v: 60, label: '1시간' },
  { v: 90, label: '1시간 30분' },
  { v: 120, label: '2시간 깊이' },
]

const COMPANIONS = [
  { v: 'self', label: '혼자', hint: '차분한 큐레이터 톤' },
  { v: 'kid', label: '어린이와', hint: '쉽고 재밌게' },
  { v: 'foreign', label: '외국인 친구', hint: '영어 안내' },
]

const SAMPLE_INTERESTS = [
  '조선 왕실 그림과 도자기',
  '불교 미술의 정수',
  '일제강점기 우리 미술',
  '한국의 자연과 풍속화',
]

export default function Plan() {
  const [duration, setDuration] = useState(60)
  const [companion, setCompanion] = useState('self')
  const [interests, setInterests] = useState('')
  const [course, setCourse] = useState('')
  const [candidates, setCandidates] = useState([])
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState('')
  const resultRef = useRef(null)

  async function build() {
    if (streaming) return
    setStreaming(true)
    setCourse('')
    setCandidates([])
    setError('')
    try {
      await streamPlan(
        { duration_min: duration, companion, interests, k: 18 },
        {
          onCandidates: setCandidates,
          onToken: (t) => setCourse((c) => c + t),
          onError: (e) => setError(e),
        }
      )
    } finally {
      setStreaming(false)
      // 결과로 스크롤
      requestAnimationFrame(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-5 sm:px-8 py-12">
      <header className="mb-10">
        <div className="text-xs tracking-[0.3em] text-[var(--color-vermilion-500)] uppercase mb-2">
          Tour Builder
        </div>
        <h1
          className="text-3xl sm:text-4xl font-bold text-[var(--color-ink-900)]"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          오늘의 관람 코스 짜기
        </h1>
        <p className="text-[var(--color-ink-700)] mt-2 max-w-2xl leading-relaxed">
          시간·동반자·관심사를 알려주시면 AI 큐레이터가 동선까지 고려해
          작품 4~7점을 골라 코스를 만들어 드립니다. 박물관에서 그대로 따라가시면 돼요.
        </p>
      </header>

      <section className="rounded-xl bg-white border border-[var(--color-paper-200)] p-6 sm:p-8 space-y-6">
        {/* 시간 */}
        <Field label="가용 시간">
          <div className="flex flex-wrap gap-2">
            {DURATIONS.map((d) => (
              <Pill key={d.v} active={duration === d.v} onClick={() => setDuration(d.v)}>
                {d.label}
              </Pill>
            ))}
          </div>
        </Field>

        {/* 동반자 */}
        <Field label="누구와 함께">
          <div className="grid sm:grid-cols-3 gap-2">
            {COMPANIONS.map((c) => (
              <button
                key={c.v}
                onClick={() => setCompanion(c.v)}
                className={
                  'rounded-lg border p-3 text-left transition ' +
                  (companion === c.v
                    ? 'bg-[var(--color-vermilion-500)] text-white border-[var(--color-vermilion-500)]'
                    : 'bg-[var(--color-paper-50)] border-[var(--color-paper-200)] hover:border-[var(--color-ink-500)]')
                }
              >
                <div className="font-semibold">{c.label}</div>
                <div
                  className={
                    'text-xs mt-0.5 ' +
                    (companion === c.v ? 'text-white/80' : 'text-[var(--color-ink-500)]')
                  }
                >
                  {c.hint}
                </div>
              </button>
            ))}
          </div>
        </Field>

        {/* 관심사 */}
        <Field label="관심사 (자유롭게)">
          <textarea
            rows={2}
            value={interests}
            onChange={(e) => setInterests(e.target.value)}
            placeholder="예) 조선 왕실의 의례와 도자기, 한국 풍속화 등"
            className="w-full resize-none bg-[var(--color-paper-50)] border border-[var(--color-paper-200)] rounded-lg px-4 py-3 outline-none focus:border-[var(--color-vermilion-500)] transition"
          />
          <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
            <span className="text-[var(--color-ink-500)] mr-1">예시:</span>
            {SAMPLE_INTERESTS.map((s) => (
              <button
                key={s}
                onClick={() => setInterests(s)}
                className="px-2 py-0.5 rounded-full border border-[var(--color-paper-200)] text-[var(--color-ink-700)] hover:border-[var(--color-vermilion-500)] hover:text-[var(--color-vermilion-500)] transition"
              >
                {s}
              </button>
            ))}
          </div>
        </Field>

        <button
          onClick={build}
          disabled={streaming}
          className="w-full rounded-lg bg-[var(--color-ink-900)] hover:bg-[var(--color-vermilion-500)] disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 transition"
        >
          {streaming ? '코스를 짜는 중…' : '코스 짜기 →'}
        </button>
      </section>

      {/* 결과 */}
      {(course || streaming || error) && (
        <section ref={resultRef} className="mt-10 space-y-6">
          {error && (
            <div className="rounded-lg bg-red-50 border border-red-200 text-red-700 p-4 text-sm">
              오류: {error}
            </div>
          )}

          {course && (
            <div className="rounded-xl bg-white border border-[var(--color-paper-200)] p-6 sm:p-8">
              <CourseRenderer text={course} />
            </div>
          )}

          {candidates.length > 0 && course && (
            <div>
              <h3 className="text-sm font-semibold text-[var(--color-ink-700)] mb-3">
                참고한 작품 후보 {candidates.length}점
              </h3>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                {candidates.slice(0, 12).map((c) => (
                  <CandidateThumb key={(c.relic_id || c.title) + c.category} c={c} />
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      <div className="mt-10 text-center text-sm text-[var(--color-ink-500)]">
        만족스럽지 않으면 입력 바꿔서 다시 짜보세요. 또는{' '}
        <Link to="/ask" className="underline hover:text-[var(--color-vermilion-500)]">
          AI 도슨트
        </Link>
        에서 자유롭게 물어볼 수 있어요.
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-[var(--color-ink-900)] mb-2">
        {label}
      </label>
      {children}
    </div>
  )
}

function Pill({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={
        'rounded-full px-4 py-2 text-sm font-medium border transition ' +
        (active
          ? 'bg-[var(--color-vermilion-500)] text-white border-[var(--color-vermilion-500)]'
          : 'bg-[var(--color-paper-50)] border-[var(--color-paper-200)] text-[var(--color-ink-700)] hover:border-[var(--color-ink-500)]')
      }
    >
      {children}
    </button>
  )
}

function CandidateThumb({ c }) {
  const isRecommend = c.category === 'recommend' && c.relic_id
  const Wrap = isRecommend ? Link : 'div'
  const props = isRecommend ? { to: `/work/${c.relic_id}` } : {}
  return (
    <Wrap
      {...props}
      title={c.title}
      className="aspect-square rounded-md bg-[var(--color-paper-100)] border border-[var(--color-paper-200)] overflow-hidden block hover:border-[var(--color-ink-500)] transition"
    >
      {c.thumbnail_url ? (
        <img
          src={c.thumbnail_url}
          alt={c.title}
          loading="lazy"
          className="w-full h-full object-cover"
          onError={(e) => { e.currentTarget.style.display = 'none' }}
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-[10px] text-[var(--color-ink-500)] p-1 text-center leading-tight">
          {c.title.slice(0, 12)}
        </div>
      )}
    </Wrap>
  )
}

/* 마크다운-라이크 텍스트를 간단히 렌더링.
 *  ## H2, ### H3, **bold**, → 화살표 줄, 일반 텍스트 단락
 */
function CourseRenderer({ text }) {
  const lines = text.split('\n')
  const out = []
  let buf = []
  const flush = () => {
    if (buf.length) {
      const p = buf.join(' ').trim()
      if (p) out.push({ type: 'p', text: p })
      buf = []
    }
  }
  for (const raw of lines) {
    const line = raw.trim()
    if (!line) { flush(); continue }
    if (line.startsWith('## ')) {
      flush()
      out.push({ type: 'h2', text: line.slice(3) })
    } else if (line.startsWith('### ')) {
      flush()
      out.push({ type: 'h3', text: line.slice(4) })
    } else if (line.startsWith('→') || line.startsWith('▶')) {
      flush()
      out.push({ type: 'arrow', text: line })
    } else {
      buf.push(line)
    }
  }
  flush()

  return (
    <article className="prose-curator">
      {out.map((b, i) => {
        if (b.type === 'h2') {
          return (
            <h2
              key={i}
              className="text-2xl font-bold text-[var(--color-ink-900)] mb-4 pb-2 border-b border-[var(--color-paper-200)]"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              {b.text}
            </h2>
          )
        }
        if (b.type === 'h3') {
          return (
            <h3
              key={i}
              className="text-base font-bold text-[var(--color-vermilion-600)] mt-6 mb-2"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              {b.text}
            </h3>
          )
        }
        if (b.type === 'arrow') {
          return (
            <div
              key={i}
              className="my-3 inline-flex items-center text-xs px-3 py-1.5 rounded-full bg-[var(--color-paper-100)] text-[var(--color-ink-700)]"
            >
              {b.text}
            </div>
          )
        }
        return (
          <p key={i} className="text-[15px] leading-relaxed text-[var(--color-ink-700)]">
            {renderInline(b.text)}
          </p>
        )
      })}
    </article>
  )
}

function renderInline(text) {
  // **bold** 처리
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) {
      return <strong key={i} className="text-[var(--color-ink-900)]">{p.slice(2, -2)}</strong>
    }
    return <span key={i}>{p}</span>
  })
}
