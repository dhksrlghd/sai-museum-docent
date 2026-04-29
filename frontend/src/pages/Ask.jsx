import AskBox from '../components/AskBox'

export default function Ask() {
  return (
    <div className="max-w-4xl mx-auto px-5 sm:px-8 py-10">
      <div className="mb-6">
        <div className="text-xs tracking-[0.3em] text-[var(--color-vermilion-500)] uppercase mb-2">
          AI Docent · 사이
        </div>
        <h1
          className="text-3xl sm:text-4xl font-bold text-[var(--color-ink-900)]"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          작품과 당신 사이를 잇다
        </h1>
        <p className="text-[var(--color-ink-700)] mt-2 max-w-2xl">
          국립중앙박물관 큐레이터들의 해설 1,200여 단락에서 맥락을 찾아 답합니다.
          어린이·성인·외국인 톤을 토글로 바꿔 가며 물어보세요.
        </p>
      </div>
      <div className="h-[70vh]">
        <AskBox variant="standalone" />
      </div>
    </div>
  )
}
