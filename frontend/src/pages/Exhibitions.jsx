import { useEffect, useState } from 'react'

export default function Exhibitions() {
  const [data, setData] = useState(null)

  useEffect(() => {
    fetch('/api/exhibitions')
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData({ halls: [], special: [] }))
  }, [])

  if (!data) {
    return (
      <div className="max-w-6xl mx-auto px-5 sm:px-8 py-20 text-center text-[var(--color-ink-500)]">
        불러오는 중...
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-5 sm:px-8 py-12">
      <header className="mb-12">
        <div className="text-xs tracking-[0.3em] text-[var(--color-vermilion-500)] uppercase mb-2">
          Exhibitions Now
        </div>
        <h1
          className="text-3xl sm:text-4xl font-bold text-[var(--color-ink-900)]"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          지금 박물관에서
        </h1>
        <p className="text-[var(--color-ink-700)] mt-2 max-w-2xl">
          오늘 국립중앙박물관에서 만날 수 있는 특별전과 상설관 안내입니다.
          궁금한 것이 있으면 AI 도슨트에게 자연스럽게 물어보세요.
        </p>
      </header>

      {/* 진행중인 특별전 */}
      <section className="mb-16">
        <div className="flex items-baseline gap-3 mb-6">
          <h2
            className="text-2xl font-bold text-[var(--color-ink-900)]"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            진행 중인 특별전
          </h2>
          <span className="text-sm text-[var(--color-ink-500)]">
            {data.special.length}건
          </span>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {data.special.map((ex) => (
            <SpecialCard key={ex.exhi_id} exhi={ex} />
          ))}
        </div>
      </section>

      {/* 상설관 트리 */}
      <section>
        <div className="flex items-baseline gap-3 mb-6">
          <h2
            className="text-2xl font-bold text-[var(--color-ink-900)]"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            상설관 안내
          </h2>
          <span className="text-sm text-[var(--color-ink-500)]">
            {data.halls.length}관
          </span>
        </div>

        <div className="space-y-8">
          {['1F', '2F', '3F'].map((floor) => {
            const halls = data.halls.filter((h) => h.floor === floor)
            if (!halls.length) return null
            return (
              <FloorBlock key={floor} floor={floor} halls={halls} />
            )
          })}
        </div>
      </section>
    </div>
  )
}

function SpecialCard({ exhi }) {
  const labels = exhi.labels || []
  return (
    <a
      href={exhi.detail_url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block rounded-lg overflow-hidden bg-white border border-[var(--color-paper-200)] hover:border-[var(--color-ink-500)] transition"
    >
      <div className="aspect-[4/3] bg-[var(--color-paper-100)] overflow-hidden">
        {exhi.thumbnail_url ? (
          <img
            src={exhi.thumbnail_url}
            alt={exhi.title}
            loading="lazy"
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            onError={(e) => { e.currentTarget.style.display = 'none' }}
          />
        ) : null}
      </div>
      <div className="p-4">
        <div className="flex flex-wrap gap-1 mb-2">
          {labels.map((lbl) => (
            <span
              key={lbl}
              className="text-[10px] font-semibold tracking-wider px-2 py-0.5 rounded-sm bg-[var(--color-vermilion-50)] text-[var(--color-vermilion-600)]"
            >
              {lbl}
            </span>
          ))}
        </div>
        <h3
          className="text-base font-bold text-[var(--color-ink-900)] line-clamp-2 leading-snug"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          {exhi.title}
        </h3>
        <div className="text-xs text-[var(--color-ink-500)] mt-2 space-y-0.5">
          {exhi.period && <div>· 기간 {exhi.period}</div>}
          {exhi.location && <div>· 장소 {exhi.location}</div>}
        </div>
      </div>
    </a>
  )
}

function FloorBlock({ floor, halls }) {
  return (
    <div>
      <div className="flex items-baseline gap-3 mb-3 pb-2 border-b border-[var(--color-paper-200)]">
        <span
          className="text-2xl font-bold text-[var(--color-vermilion-500)]"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          {floor}
        </span>
        <span className="text-sm text-[var(--color-ink-500)]">
          {halls.length}관
        </span>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {halls.map((h) => (
          <HallCard key={h.name} hall={h} />
        ))}
      </div>
    </div>
  )
}

function HallCard({ hall }) {
  const [open, setOpen] = useState(false)
  const totalWorks = hall.rooms.reduce((s, r) => s + (r.works_count || 0), 0)
  return (
    <div className="rounded-lg bg-white border border-[var(--color-paper-200)] p-4 hover:border-[var(--color-ink-500)] transition">
      <div className="flex items-baseline justify-between mb-2">
        <h3
          className="text-lg font-bold text-[var(--color-ink-900)]"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          {hall.name}
        </h3>
        <span className="text-xs text-[var(--color-ink-500)]">
          {hall.rooms.length}실 · {totalWorks}점
        </span>
      </div>
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-xs text-[var(--color-vermilion-500)] hover:underline"
      >
        {open ? '접기 −' : '실 목록 보기 +'}
      </button>
      {open && (
        <ul className="mt-3 space-y-1 text-sm">
          {hall.rooms.map((r) => (
            <li key={r.showroom_code} className="flex items-center justify-between">
              <a
                href={r.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--color-ink-700)] hover:text-[var(--color-vermilion-500)] hover:underline"
              >
                {r.name}
              </a>
              <span className="text-xs text-[var(--color-ink-500)]">
                {r.works_count}점
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
