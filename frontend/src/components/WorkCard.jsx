import { Link } from 'react-router-dom'

export default function WorkCard({ work, size = 'md' }) {
  const aspect = size === 'lg' ? 'aspect-[4/5]' : 'aspect-square'
  const titleSize = size === 'lg' ? 'text-base' : 'text-sm'

  return (
    <Link
      to={`/work/${work.relic_recommend_id}`}
      className="group block rounded-md overflow-hidden bg-white border border-[var(--color-paper-200)] hover:border-[var(--color-ink-500)] transition"
    >
      <div className={`${aspect} bg-[var(--color-paper-100)] overflow-hidden`}>
        {work.thumbnail_url ? (
          <img
            src={work.thumbnail_url}
            alt={work.title_full || work.title}
            loading="lazy"
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            onError={(e) => { e.currentTarget.style.display = 'none' }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[var(--color-paper-200)] text-xs">
            no image
          </div>
        )}
      </div>
      <div className="p-3">
        <div className={`${titleSize} font-semibold text-[var(--color-ink-900)] line-clamp-2 leading-snug`}>
          {work.title_full || work.title}
        </div>
        {work.curator && (
          <div className="text-xs text-[var(--color-ink-500)] mt-1">
            큐레이터 {work.curator}
          </div>
        )}
      </div>
    </Link>
  )
}
