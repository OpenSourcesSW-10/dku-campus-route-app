// 피그마의 모바일 상태바(9:41 · 5G · 87%) 흉내 — 앱 느낌용
export default function StatusBar({ dark = false }: { dark?: boolean }) {
  const c = dark ? 'text-white' : 'text-ink'
  return (
    <div className={`flex h-11 shrink-0 items-center justify-between px-6 text-[15px] font-semibold ${c}`}>
      <span>9:41</span>
      <span className="absolute left-1/2 top-3 h-3 w-3 -translate-x-1/2 rounded-full bg-black" />
      <span className="flex items-center gap-1.5">
        <span>5G</span>
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor">
          <circle cx="12" cy="12" r="9" opacity="0.25" />
          <path d="M12 3a9 9 0 019 9h-9z" />
        </svg>
        <span>87%</span>
      </span>
    </div>
  )
}
