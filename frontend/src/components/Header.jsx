import { useEffect, useRef, useState } from 'react'
import { NavLink, Link, useLocation } from 'react-router-dom'

const NAV = [
  { to: '/', label: '홈', end: true },
  { to: '/plan', label: '코스 짜기' },
  { to: '/exhibitions', label: '전시 안내' },
  { to: '/browse', label: '소장품 둘러보기' },
  { to: '/ask', label: 'AI 도슨트' },
]

export default function Header() {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const wrapRef = useRef(null)

  // 라우트 바뀌면 모바일 메뉴 닫기
  useEffect(() => { setOpen(false) }, [location.pathname])

  // 외부 클릭 시 모바일 메뉴 닫기
  useEffect(() => {
    function onDoc(e) {
      if (open && wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('click', onDoc)
    return () => document.removeEventListener('click', onDoc)
  }, [open])

  return (
    <header
      ref={wrapRef}
      className="sticky top-0 z-30 bg-[var(--color-paper-50)]/85 backdrop-blur border-b border-[var(--color-paper-200)]"
    >
      <div className="max-w-6xl mx-auto px-4 sm:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-baseline gap-3 group min-w-0">
          <span
            className="text-xl sm:text-2xl font-bold tracking-tight text-[var(--color-ink-900)] group-hover:text-[var(--color-vermilion-500)] transition"
            style={{ fontFamily: 'var(--font-display)', letterSpacing: '0.5em' }}
            aria-label="사이"
          >
            사이
          </span>
          <span className="hidden md:inline text-xs text-[var(--color-ink-500)] truncate">
            작품과 당신 사이
          </span>
        </Link>

        {/* 데스크톱 가로 메뉴 (md+) */}
        <nav className="hidden md:flex items-center gap-1 lg:gap-3 text-sm">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                'px-3 py-2 rounded-md transition whitespace-nowrap ' +
                (isActive
                  ? 'text-[var(--color-vermilion-500)] font-semibold'
                  : 'text-[var(--color-ink-700)] hover:text-[var(--color-ink-900)]')
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>

        {/* 모바일 햄버거 (md 미만) */}
        <button
          onClick={(e) => { e.stopPropagation(); setOpen((v) => !v) }}
          className="md:hidden p-2 -mr-2 rounded-md hover:bg-[var(--color-paper-100)]"
          aria-label="메뉴 열기"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {open ? (
              <>
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </>
            ) : (
              <>
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </>
            )}
          </svg>
        </button>
      </div>

      {/* 모바일 드롭다운 */}
      {open && (
        <nav className="md:hidden border-t border-[var(--color-paper-200)] bg-[var(--color-paper-50)] px-4 pb-3 pt-2 flex flex-col gap-1 text-sm">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                'px-3 py-3 rounded-md transition ' +
                (isActive
                  ? 'bg-[var(--color-vermilion-50)] text-[var(--color-vermilion-600)] font-semibold'
                  : 'text-[var(--color-ink-700)] hover:bg-[var(--color-paper-100)]')
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  )
}
