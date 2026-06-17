import { site } from "@/lib/site";

const stats = [
  { value: "자동", label: "OCR 인식" },
  { value: "4탭", label: "통계 분석" },
  { value: "무료", label: "Windows" },
];

export default function Hero() {
  return (
    <section id="top" className="relative overflow-hidden">
      <div className="bg-grid animate-grid-pan pointer-events-none absolute inset-0 opacity-60" />
      {/* teal glow accent */}
      <div className="pointer-events-none absolute -left-32 top-10 h-72 w-72 rounded-full bg-teal/20 blur-[120px]" />
      <div className="pointer-events-none absolute right-0 top-40 h-80 w-80 rounded-full bg-teal/10 blur-[140px]" />

      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-5 pb-20 pt-32 md:grid-cols-[1.05fr_0.95fr] md:pt-40">
        {/* left: copy */}
        <div className="animate-fade-up">
          <span className="clip-slash-sm inline-block bg-teal px-3 py-1 font-display text-xs font-bold tracking-[0.2em] text-teal-ink">
            STEAM · MASTER DUEL
          </span>

          <h1 className="mt-6 text-5xl font-black leading-[1.08] tracking-tight md:text-6xl">
            듀얼리스트의
            <br />
            <span className="text-teal">전적 노트.</span>
          </h1>

          <p className="mt-6 max-w-md text-base leading-relaxed text-mute">
            켜두면 알아서 쌓인다. 플레이 화면을 인식해 코인토스·선후공·승패를
            자동으로 기록하고, 승률과 메타를 한눈에 정리하는 데스크톱 트래커.
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-3">
            <a
              href={site.releasesLatest}
              target="_blank"
              rel="noreferrer"
              className="clip-slash bg-teal px-7 py-3.5 font-display text-base font-bold tracking-wide text-teal-ink transition-transform hover:scale-[1.03] active:scale-95"
            >
              지금 다운로드
            </a>
            <a
              href="#how"
              className="border border-white/15 px-7 py-3.5 font-display text-base font-bold tracking-wide text-white/90 transition-colors hover:border-teal/60 hover:text-teal"
            >
              사용법 보기
            </a>
          </div>

          <div className="mt-10 flex gap-10">
            {stats.map((s) => (
              <div key={s.label}>
                <div className="font-display text-2xl font-bold text-white">
                  {s.value}
                </div>
                <div className="mt-0.5 text-xs uppercase tracking-wider text-mute-soft">
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* right: app shot */}
        <div className="animate-fade-up [animation-delay:120ms]">
          <div className="relative">
            <div className="absolute -inset-px bg-teal/30 clip-slash" />
            <div className="clip-slash relative border border-white/10 bg-ink-700 p-2">
              <div className="overflow-hidden border border-white/5">
                <img
                  src="/screenshots/app-hero.png"
                  alt="MDTracker 메인 화면"
                  width={1280}
                  height={820}
                  className="block h-auto w-full"
                />
              </div>
            </div>
            {/* floating badge */}
            <div className="clip-slash-sm absolute -bottom-4 -left-4 hidden items-center gap-2 border border-teal/40 bg-ink-800 px-4 py-2 sm:flex">
              <span className="h-2 w-2 animate-pulse rounded-full bg-teal" />
              <span className="font-display text-sm font-bold tracking-wide text-teal">
                OCR 인식 중
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
