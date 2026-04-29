export default function Footer() {
  return (
    <footer className="border-t border-[var(--color-paper-200)] bg-white/40 mt-20">
      <div className="max-w-6xl mx-auto px-5 sm:px-8 py-10 grid sm:grid-cols-2 gap-6 text-sm text-[var(--color-ink-500)]">
        <div>
          <div className="flex items-baseline gap-3 mb-2">
            <span
              className="text-base font-semibold text-[var(--color-ink-900)]"
              style={{ fontFamily: 'var(--font-display)', letterSpacing: '0.4em' }}
            >
              사이
            </span>
            <span className="text-xs text-[var(--color-ink-500)]">
              작품과 당신 사이
            </span>
          </div>
          <p className="leading-relaxed">
            국립중앙박물관 큐레이터들이 작성한 작품 해설과 전시실 안내를 RAG·멀티모달로 엮어,
            관람 전 코스 추천부터 작품 마주봄까지 한 자리에서 안내하는 도슨트 프로젝트입니다.
          </p>
        </div>
        <div className="sm:text-right">
          <div className="font-medium text-[var(--color-ink-700)] mb-2">출처 / 라이선스</div>
          <p className="leading-relaxed">
            모든 작품 텍스트와 이미지는{' '}
            <a
              href="https://www.museum.go.kr/MUSEUM/contents/M0501000000.do"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-[var(--color-vermilion-500)]"
            >
              국립중앙박물관 큐레이터 추천 소장품
            </a>
            의 공공누리 3유형(출처표시+변경금지) 자료를 사용합니다.
          </p>
        </div>
      </div>
    </footer>
  )
}
