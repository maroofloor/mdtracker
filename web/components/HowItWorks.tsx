const steps = [
  {
    no: "01",
    title: "내 덱 등록",
    body: "덱 관리 탭에서 현재 사용 중인 덱을 추가합니다.",
  },
  {
    no: "02",
    title: "OCR 켜기",
    body: "기록 탭에서 내 덱을 선택하고 ● OCR 버튼을 누릅니다.",
  },
  {
    no: "03",
    title: "그냥 플레이",
    body: "게임을 합니다. 코인토스·선후공·승패가 자동 감지됩니다.",
  },
  {
    no: "04",
    title: "통계 확인",
    body: "대시보드에서 승률·매치업·메타·추세를 확인합니다.",
  },
];

const shots = [
  {
    src: "/screenshots/record.png",
    title: "기록 탭",
    body: "자동 인식된 결과를 확인·교정하고, 수동으로도 추가합니다.",
    w: 900,
    h: 600,
  },
  {
    src: "/screenshots/dashboard.png",
    title: "대시보드 탭",
    body: "요약 KPI · 매치업 · 메타 분포 · 기간별 추세를 한 화면에.",
    w: 1221,
    h: 872,
  },
  {
    src: "/screenshots/deck.png",
    title: "덱 관리 탭",
    body: "내 덱을 관리하고 퍼지 검색으로 OCR 오인식을 바로잡습니다.",
    w: 900,
    h: 600,
  },
];

export default function HowItWorks() {
  return (
    <section id="how" className="relative border-y border-white/5 bg-ink-800">
      <div className="bg-grid pointer-events-none absolute inset-0 opacity-30" />
      <div className="relative mx-auto max-w-6xl px-5 py-24">
        <div className="mb-14 max-w-xl">
          <span className="font-display text-sm font-bold tracking-[0.2em] text-teal">
            HOW IT WORKS
          </span>
          <h2 className="mt-3 text-3xl font-black tracking-tight md:text-4xl">
            네 단계면 끝
          </h2>
          <p className="mt-4 text-mute">
            설정은 한 번, 그다음부터는 켜두기만 하면 됩니다.
          </p>
        </div>

        {/* steps */}
        <div className="grid gap-px overflow-hidden border border-white/10 bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((s) => (
            <div key={s.no} className="bg-ink-700 p-7">
              <div className="font-display text-4xl font-bold text-teal/30">
                {s.no}
              </div>
              <h3 className="mt-4 font-display text-lg font-bold tracking-wide">
                {s.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-mute">{s.body}</p>
            </div>
          ))}
        </div>

        {/* OCR flow note */}
        <div className="clip-slash mt-8 flex flex-wrap items-center gap-3 border border-teal/20 bg-teal/[0.06] px-6 py-4 font-display text-sm font-bold tracking-wide">
          <span className="text-mute">자동 인식 흐름</span>
          <span className="text-white">코인토스</span>
          <span className="text-teal">→</span>
          <span className="text-white">선·후공</span>
          <span className="text-teal">→</span>
          <span className="text-white">승·패 배너</span>
          <span className="text-teal">→</span>
          <span className="text-teal">결과 팝업</span>
        </div>

        {/* screenshots */}
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {shots.map((sh) => (
            <figure key={sh.title} className="group">
              <div className="clip-slash relative border border-white/10 bg-ink-600 p-1.5 transition-colors group-hover:border-teal/40">
                <img
                  src={sh.src}
                  alt={sh.title}
                  width={sh.w}
                  height={sh.h}
                  className="block h-auto w-full border border-white/5"
                />
              </div>
              <figcaption className="mt-4">
                <h3 className="font-display text-base font-bold tracking-wide text-white">
                  {sh.title}
                </h3>
                <p className="mt-1 text-sm leading-relaxed text-mute">
                  {sh.body}
                </p>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}
