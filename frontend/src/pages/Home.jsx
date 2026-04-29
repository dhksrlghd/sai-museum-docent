import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listWorks } from '../lib/api'
import WorkCard from '../components/WorkCard'

const HERO_PICKS = [
  { id: 2351292, title: '〈기영회도〉', subtitle: '세 가지 복을 누린 원로 관료들의 잔치', curator: '오다연' },
  { id: 16819, title: '동래부사접왜사도', subtitle: '동래부사가 일본 사신을 맞이하다', curator: '장진아' },
  { id: 16847, title: '단원풍속도첩, 김홍도', subtitle: '조선 풍속화의 정수', curator: '이혜경' },
]

export default function Home() {
  const [hero, setHero] = useState(null)
  const [picks, setPicks] = useState([])
  const [today, setToday] = useState(null)
  const [special, setSpecial] = useState([])
  const [hi, setHi] = useState(0)

  useEffect(() => {
    let cancelled = false
    async function load() {
      const heroData = await Promise.all(
        HERO_PICKS.map(async (p) => {
          try {
            const r = await fetch(`/api/works/${p.id}`)
            if (!r.ok) return null
            const d = await r.json()
            return { ...p, thumbnail_url: d.thumbnail_url || d.title_image_url, period: d.metadata?.period || '' }
          } catch { return null }
        })
      )
      const all = await listWorks({ limit: 12, offset: 0 })
      let exhi = []
      try {
        const r = await fetch('/api/exhibitions')
        if (r.ok) {
          const j = await r.json()
          exhi = j.special || []
        }
      } catch { /* ignore */ }
      let todayData = null
      try {
        const r = await fetch('/api/today')
        if (r.ok) todayData = await r.json()
      } catch { /* ignore */ }
      if (cancelled) return
      setHero(heroData.filter(Boolean))
      setPicks(all.items || [])
      setSpecial(exhi)
      setToday(todayData)
    }
    load()
    return () => { cancelled = true }
  }, [])

  // 5초마다 히어로 자동 전환
  useEffect(() => {
    if (!hero || hero.length < 2) return
    const t = setInterval(() => setHi((i) => (i + 1) % hero.length), 6000)
    return () => clearInterval(t)
  }, [hero])

  return (
    <div className="min-h-full">
      {/* 진행중 특별전 띠 (있을 때만) */}
      {special.length > 0 && (
        <Link
          to="/exhibitions"
          className="block bg-[var(--color-vermilion-50)] border-b border-[var(--color-paper-200)] py-2 px-5 sm:px-8 text-center text-sm hover:bg-[var(--color-vermilion-500)] hover:text-white transition group"
        >
          <span className="font-semibold text-[var(--color-vermilion-600)] group-hover:text-white">
            지금 박물관에서
          </span>
          <span className="mx-2 text-[var(--color-ink-500)] group-hover:text-white/70">·</span>
          <span className="text-[var(--color-ink-700)] group-hover:text-white">
            특별전 {special.length}건 진행중
          </span>
          <span className="ml-3 text-[var(--color-ink-500)] group-hover:text-white/80">→</span>
        </Link>
      )}

      {/* HERO */}
      <section className="relative bg-[var(--color-ink-900)] text-white overflow-hidden">
        <div className="max-w-6xl mx-auto px-5 sm:px-8 py-16 sm:py-24 grid lg:grid-cols-2 gap-10 items-center">
          <div className="break-keep">
            <div className="inline-block text-xs tracking-[0.3em] text-[var(--color-vermilion-500)] mb-4 uppercase">
              Between you & Korean art
            </div>
            <h1
              className="text-4xl sm:text-5xl font-bold leading-[1.15] mb-4 break-keep"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              작품과 당신,
              <br />
              <span className="text-[var(--color-vermilion-500)]">그 사이를 잇다</span>
            </h1>
            <p className="text-base text-white/70 leading-relaxed mb-8 max-w-xl break-keep">
              국립중앙박물관 큐레이터들이 직접 선정·해설한 명품 321선을 가까이서 살펴보고,
              궁금한 부분은 어린이·성인·외국인 톤으로 자연스럽게 물어보세요.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/browse"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-md bg-[var(--color-vermilion-500)] hover:bg-[var(--color-vermilion-600)] text-white text-sm font-semibold transition"
              >
                소장품 둘러보기 →
              </Link>
              <Link
                to="/ask"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-md border border-white/30 hover:border-white text-white text-sm font-semibold transition"
              >
                AI 도슨트에게 묻기
              </Link>
            </div>
          </div>

          {/* 히어로 이미지 카드 */}
          {hero && hero[hi] && (
            <Link to={`/work/${hero[hi].id}`} className="block group">
              <div className="aspect-[4/5] rounded-lg overflow-hidden bg-white/5 ring-1 ring-white/10 shadow-2xl">
                {hero[hi].thumbnail_url && (
                  <img
                    src={hero[hi].thumbnail_url}
                    alt={hero[hi].title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                  />
                )}
              </div>
              <div className="mt-4">
                <div className="text-xs text-white/50 mb-1">
                  {hero[hi].period} · 큐레이터 {hero[hi].curator}
                </div>
                <div
                  className="text-xl font-semibold group-hover:text-[var(--color-vermilion-500)] transition"
                  style={{ fontFamily: 'var(--font-display)' }}
                >
                  {hero[hi].title}
                </div>
                <div className="text-sm text-white/60 mt-1 line-clamp-1">
                  {hero[hi].subtitle}
                </div>
              </div>
              {hero.length > 1 && (
                <div className="flex gap-1.5 mt-4">
                  {hero.map((_, i) => (
                    <button
                      key={i}
                      onClick={(e) => { e.preventDefault(); setHi(i) }}
                      className={
                        'h-1 rounded-full transition-all ' +
                        (i === hi ? 'w-8 bg-[var(--color-vermilion-500)]' : 'w-3 bg-white/30')
                      }
                      aria-label={`히어로 ${i + 1}`}
                    />
                  ))}
                </div>
              )}
            </Link>
          )}
        </div>
      </section>

      {/* 오늘의 큐레이션 */}
      {today?.picks?.length > 0 && (
        <section className="max-w-6xl mx-auto px-5 sm:px-8 py-16">
          <div className="flex items-end justify-between mb-8">
            <div>
              <div className="text-xs tracking-[0.3em] text-[var(--color-vermilion-500)] uppercase mb-2">
                Today's Curation · {today.date}
              </div>
              <h2
                className="text-3xl sm:text-4xl font-bold text-[var(--color-ink-900)]"
                style={{ fontFamily: 'var(--font-display)' }}
              >
                {today.theme.ko}
              </h2>
              <p className="text-sm text-[var(--color-ink-500)] mt-1">
                {today.theme.en}
              </p>
            </div>
            <Link
              to="/browse"
              className="text-sm font-medium text-[var(--color-ink-700)] hover:text-[var(--color-vermilion-500)] transition"
            >
              전체 321점 보기 →
            </Link>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-5">
            {today.picks.map((w) => (
              <Link
                key={w.relic_id}
                to={`/work/${w.relic_id}`}
                className="group block rounded-md overflow-hidden bg-white border border-[var(--color-paper-200)] hover:border-[var(--color-ink-500)] transition"
              >
                <div className="aspect-[4/5] bg-[var(--color-paper-100)] overflow-hidden">
                  {w.thumbnail_url && (
                    <img
                      src={w.thumbnail_url}
                      alt={w.title}
                      loading="lazy"
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                      onError={(e) => { e.currentTarget.style.display = 'none' }}
                    />
                  )}
                </div>
                <div className="p-4">
                  <h3
                    className="text-base font-semibold text-[var(--color-ink-900)] line-clamp-2"
                    style={{ fontFamily: 'var(--font-display)' }}
                  >
                    {w.title}
                  </h3>
                  {w.subtitle && (
                    <p className="text-xs text-[var(--color-ink-500)] mt-1 line-clamp-1">
                      {w.subtitle}
                    </p>
                  )}
                  <div className="mt-2 text-[11px] text-[var(--color-ink-500)]">
                    {w.period && <span>{w.period}</span>}
                    {w.curator && <span> · 큐레이터 {w.curator}</span>}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* 더 보기 (랜덤 12) */}
      <section className="max-w-6xl mx-auto px-5 sm:px-8 pb-16">
        <div className="flex items-end justify-between mb-6">
          <h2
            className="text-2xl font-bold text-[var(--color-ink-900)]"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            더 둘러보기
          </h2>
          <Link
            to="/browse"
            className="text-sm font-medium text-[var(--color-ink-700)] hover:text-[var(--color-vermilion-500)] transition"
          >
            321점 전체 →
          </Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-5">
          {picks.map((w) => (
            <WorkCard key={w.relic_recommend_id} work={w} />
          ))}
        </div>
      </section>

      {/* AI 도슨트 미리보기 */}
      <section className="max-w-6xl mx-auto px-5 sm:px-8 py-16">
        <div className="rounded-xl bg-[var(--color-paper-100)] p-8 sm:p-12 grid sm:grid-cols-3 gap-8 items-center">
          <div className="sm:col-span-2 break-keep">
            <div className="text-xs tracking-[0.3em] text-[var(--color-vermilion-500)] uppercase mb-2">
              AI Docent · 사이
            </div>
            <h3
              className="text-2xl sm:text-3xl font-bold text-[var(--color-ink-900)] mb-3"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              큐레이터의 시선과 당신 사이
            </h3>
            <p className="text-[var(--color-ink-700)] leading-relaxed">
              "조선시대 잔치 그림이 궁금해요"처럼 편하게 물어보세요.
              관련된 큐레이터 해설을 찾아 어린이·성인·외국인 톤으로 풀어드리고,
              자료에 없는 건 만들어내지 않으며 출처도 함께 보여줘요.
            </p>
          </div>
          <Link
            to="/ask"
            className="block text-center px-6 py-4 rounded-md bg-[var(--color-ink-900)] hover:bg-[var(--color-vermilion-500)] text-white font-semibold transition"
          >
            대화 시작하기 →
          </Link>
        </div>
      </section>
    </div>
  )
}
