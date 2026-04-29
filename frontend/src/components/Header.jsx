import { NavLink, Link } from 'react-router-dom'

const NAV = [
  { to: '/', label: '홈', end: true },
  { to: '/exhibitions', label: '전시 안내' },
  { to: '/browse', label: '소장품 둘러보기' },
  { to: '/ask', label: 'AI 도슨트' },
]

export default function Header() {
  return (
    <header className="sticky top-0 z-30 bg-[var(--color-paper-50)]/85 backdrop-blur border-b border-[var(--color-paper-200)]">
      <div className="max-w-6xl mx-auto px-5 sm:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-baseline gap-2 group">
          <span
            className="text-2xl font-bold tracking-tight text-[var(--color-ink-900)] group-hover:text-[var(--color-vermilion-500)] transition"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            K-Curator
          </span>
          <span className="hidden sm:inline text-xs text-[var(--color-ink-500)]">
            국립중앙박물관 큐레이터 추천 321선
          </span>
        </Link>
        <nav className="flex items-center gap-1 sm:gap-3 text-sm">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                'px-3 py-2 rounded-md transition ' +
                (isActive
                  ? 'text-[var(--color-vermilion-500)] font-semibold'
                  : 'text-[var(--color-ink-700)] hover:text-[var(--color-ink-900)]')
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  )
}
