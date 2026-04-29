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
      if (cancelled) return
      setHero(heroData.filter(Boolean))
      setPicks(all.items || [])
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
      {/* HERO */}
      <section className="relative bg-[var(--color-ink-900)] text-white overflow-hidden">
        <div className="max-w-6xl mx-auto px-5 sm:px-8 py-16 sm:py-24 grid lg:grid-cols-2 gap-10 items-center">
          <div>
            <div className="inline-block text-xs tracking-[0.3em] text-[var(--color-vermilion-500)] mb-4 uppercase">
              National Museum · Curators' Picks
            </div>
            <h1
              className="text-4xl sm:text-5xl font-bold leading-tight mb-4"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              큐레이터의 시선으로 보는<br />
              <span className="text-[var(--color-vermilion-500)]">한국의 명품 321선</span>
            </h1>
            <p className="text-base text-white/70 leading-relaxed mb-8 max-w-xl">
              국립중앙박물관 큐레이터들이 직접 선정·해설한 작품을 가까이서 살펴보고,
              궁금한 부분은 AI 도슨트에게 어린이·성인·외국인 톤으로 물어보세요.
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

      {/* 추천 그리드 */}
      <section className="max-w-6xl mx-auto px-5 sm:px-8 py-16">
        <div className="flex items-end justify-between mb-8">
          <div>
            <div className="text-xs tracking-[0.3em] text-[var(--color-vermilion-500)] uppercase mb-2">
              Curators' Picks
            </div>
            <h2
              className="text-3xl sm:text-4xl font-bold text-[var(--color-ink-900)]"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              지금 만나보세요
            </h2>
          </div>
          <Link
            to="/browse"
            className="text-sm font-medium text-[var(--color-ink-700)] hover:text-[var(--color-vermilion-500)] transition"
          >
            전체 321점 보기 →
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
          <div className="sm:col-span-2">
            <div className="text-xs tracking-[0.3em] text-[var(--color-vermilion-500)] uppercase mb-2">
              AI Docent
            </div>
            <h3
              className="text-2xl sm:text-3xl font-bold text-[var(--color-ink-900)] mb-3"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              321명의 큐레이터가 답해드려요
            </h3>
            <p className="text-[var(--color-ink-700)] leading-relaxed">
              "조선시대 잔치 그림이 궁금해요" 같이 자연스럽게 물어보세요.
              관련된 큐레이터 해설을 찾아 어린이·성인·외국인 톤으로 풀어드립니다.
              본문에 없는 내용은 만들어내지 않고, 출처도 함께 보여줘요.
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
