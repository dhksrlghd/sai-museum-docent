import { useEffect, useMemo, useState } from 'react'
import { listWorks } from '../lib/api'
import WorkCard from '../components/WorkCard'

const PAGE_SIZE = 24

export default function Browse() {
  const [allItems, setAllItems] = useState([])
  const [total, setTotal] = useState(0)
  const [q, setQ] = useState('')
  const [visible, setVisible] = useState(PAGE_SIZE)

  useEffect(() => {
    let cancelled = false
    async function load() {
      const data = await listWorks({ limit: 0 })
      if (cancelled) return
      setAllItems(data.items || [])
      setTotal(data.total || 0)
    }
    load()
    return () => { cancelled = true }
  }, [])

  const filtered = useMemo(() => {
    if (!q.trim()) return allItems
    const ql = q.trim().toLowerCase()
    return allItems.filter((it) => (it.title_full || '').toLowerCase().includes(ql))
  }, [allItems, q])

  const shown = filtered.slice(0, visible)

  return (
    <div className="max-w-6xl mx-auto px-5 sm:px-8 py-12">
      <div className="mb-10">
        <div className="text-xs tracking-[0.3em] text-[var(--color-vermilion-500)] uppercase mb-2">
          Collection · 321
        </div>
        <h1
          className="text-3xl sm:text-4xl font-bold text-[var(--color-ink-900)] mb-4"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          소장품 둘러보기
        </h1>
        <p className="text-[var(--color-ink-700)] max-w-2xl leading-relaxed">
          국립중앙박물관 큐레이터가 추천한 전 작품 {total}점입니다. 작품명을 입력해 검색해보세요.
        </p>
      </div>

      <div className="mb-8 flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex-1 relative">
          <input
            type="text"
            value={q}
            onChange={(e) => { setQ(e.target.value); setVisible(PAGE_SIZE) }}
            placeholder="작품 이름으로 검색  (예: 백자, 김홍도, 토우)"
            className="w-full px-4 py-3 pr-10 rounded-md border border-[var(--color-paper-200)] bg-white text-[var(--color-ink-900)] placeholder:text-[var(--color-ink-500)] focus:outline-none focus:border-[var(--color-vermilion-500)] transition"
          />
          {q && (
            <button
              onClick={() => setQ('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-ink-500)] hover:text-[var(--color-ink-900)]"
            >
              ✕
            </button>
          )}
        </div>
        <div className="text-sm text-[var(--color-ink-500)]">
          {filtered.length}점 검색됨
        </div>
      </div>

      {shown.length === 0 ? (
        <div className="py-20 text-center text-[var(--color-ink-500)]">
          {allItems.length === 0 ? '불러오는 중...' : '검색 결과가 없어요.'}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-5">
            {shown.map((w) => (
              <WorkCard key={w.relic_recommend_id} work={w} />
            ))}
          </div>
          {visible < filtered.length && (
            <div className="mt-10 text-center">
              <button
                onClick={() => setVisible((v) => v + PAGE_SIZE)}
                className="px-6 py-3 rounded-md border border-[var(--color-ink-700)] text-[var(--color-ink-700)] hover:bg-[var(--color-ink-900)] hover:text-white hover:border-[var(--color-ink-900)] transition text-sm font-medium"
              >
                더 보기 ({filtered.length - visible}점 남음)
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
