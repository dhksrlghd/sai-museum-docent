import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getWork } from '../lib/api'
import AskBox from '../components/AskBox'

export default function Work() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setData(null)
    setError(null)
    getWork(id).then(
      (d) => { if (!cancelled) setData(d) },
      (e) => { if (!cancelled) setError(e.message || 'failed') },
    )
    return () => { cancelled = true }
  }, [id])

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-5 sm:px-8 py-20 text-center">
        <div className="text-[var(--color-ink-500)]">작품을 불러오지 못했어요. ({error})</div>
        <Link to="/browse" className="mt-4 inline-block underline text-[var(--color-vermilion-500)]">
          소장품 목록으로 돌아가기
        </Link>
      </div>
    )
  }
  if (!data) {
    return (
      <div className="max-w-3xl mx-auto px-5 sm:px-8 py-20 text-center text-[var(--color-ink-500)]">
        불러오는 중...
      </div>
    )
  }

  const md = data.metadata || {}
  const heroImg =
    data.images?.[0]?.url || data.title_image_url || data.thumbnail_url || ''

  return (
    <article className="max-w-6xl mx-auto px-5 sm:px-8 py-10">
      <Link to="/browse" className="text-sm text-[var(--color-ink-500)] hover:text-[var(--color-vermilion-500)]">
        ← 소장품 목록
      </Link>

      <div className="mt-4 mb-10">
        {data.curator && (
          <div className="text-xs tracking-[0.25em] text-[var(--color-vermilion-500)] uppercase mb-2">
            Curator · {data.curator}
          </div>
        )}
        <h1
          className="text-3xl sm:text-5xl font-bold text-[var(--color-ink-900)] leading-tight mb-3"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          {data.title}
        </h1>
        {data.subtitle && (
          <p className="text-lg sm:text-xl text-[var(--color-ink-500)] leading-snug">
            {data.subtitle}
          </p>
        )}
      </div>

      <div className="grid lg:grid-cols-[1fr_360px] gap-10">
        {/* 본문 영역 */}
        <div>
          {heroImg && (
            <figure className="mb-8">
              <div className="rounded-lg overflow-hidden bg-[var(--color-paper-100)] border border-[var(--color-paper-200)]">
                <img src={heroImg} alt={data.title} className="w-full h-auto block" />
              </div>
              {data.images?.[0]?.caption && (
                <figcaption className="text-xs text-[var(--color-ink-500)] mt-3">
                  {data.images[0].caption}
                </figcaption>
              )}
            </figure>
          )}

          {/* 메타데이터 */}
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-y-3 gap-x-6 mb-10 py-5 border-y border-[var(--color-paper-200)] text-sm">
            <Field label="시대" value={md.period} />
            <Field label="재질" value={md.medium} />
            <Field label="크기" value={md.size} />
            <Field label="등급" value={md.grade} />
            <Field label="소장번호" value={md.collection_no} long />
            <Field label="작가" value={md.artist} />
          </dl>

          {/* 큐레이터 본문 */}
          <div className="prose-curator">
            {(data.body || []).map((b, i) => <BodyBlock key={i} block={b} />)}
          </div>

          {/* 추가 이미지 */}
          {data.images?.length > 1 && (
            <section className="mt-10">
              <h3 className="text-lg font-semibold text-[var(--color-ink-900)] mb-4">
                작품 자세히 보기
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {data.images.slice(1).map((img, i) => (
                  <figure key={i} className="m-0">
                    <div className="aspect-square rounded-md overflow-hidden bg-[var(--color-paper-100)] border border-[var(--color-paper-200)]">
                      <img src={img.url} alt={img.caption} className="w-full h-full object-cover hover:scale-105 transition-transform duration-500" loading="lazy" />
                    </div>
                    {img.caption && (
                      <figcaption className="text-[11px] text-[var(--color-ink-500)] mt-2 line-clamp-2">
                        {img.caption}
                      </figcaption>
                    )}
                  </figure>
                ))}
              </div>
            </section>
          )}

          {data.license && (
            <div className="mt-10 p-4 rounded-md bg-[var(--color-paper-100)] text-xs text-[var(--color-ink-500)] leading-relaxed">
              {data.license}
            </div>
          )}
        </div>

        {/* 우측 AI 도슨트 패널 */}
        <aside className="lg:sticky lg:top-20 lg:self-start lg:h-[calc(100vh-6rem)]">
          <AskBox
            variant="panel"
            initialQuery={data.title ? `${data.title}에 대해 더 자세히 알려주세요` : ''}
          />
        </aside>
      </div>
    </article>
  )
}

function Field({ label, value, long }) {
  if (!value) return null
  return (
    <div className={long ? 'sm:col-span-2' : ''}>
      <dt className="text-[11px] uppercase tracking-wider text-[var(--color-ink-500)]">{label}</dt>
      <dd className="text-[var(--color-ink-900)] mt-0.5">{value}</dd>
    </div>
  )
}

function BodyBlock({ block }) {
  if (block.type === 'heading') return <h3>{block.text}</h3>
  if (block.type === 'quote') return <blockquote>{block.text}</blockquote>
  if (block.type === 'caption') {
    return (
      <figure>
        {block.image_url && (
          <div className="rounded-md overflow-hidden bg-[var(--color-paper-100)] border border-[var(--color-paper-200)]">
            <img src={block.image_url} alt={block.text} className="w-full h-auto" loading="lazy" />
          </div>
        )}
        <figcaption>{block.text}</figcaption>
      </figure>
    )
  }
  return <p>{block.text}</p>
}
