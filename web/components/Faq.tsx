const faqs = [
  {
    q: "어떤 게임을 지원하나요?",
    a: "Steam에서 서비스 중인 Yu-Gi-Oh! Master Duel을 지원합니다. Windows 10 / 11 64-bit 환경에서 동작합니다.",
  },
  {
    q: "Python이나 Tesseract를 따로 설치해야 하나요?",
    a: "아니요. 일반 사용자는 설치 파일에 모든 것이 포함되어 있어 별도 설치가 필요 없습니다. 소스에서 직접 빌드하려는 개발자만 Python 3.10+ 와 Tesseract 5.x 가 필요합니다.",
  },
  {
    q: "OCR 인식이 잘 안 될 때는 어떻게 하나요?",
    a: "기본 인식 영역은 1920×1080 기준입니다. 다른 해상도라면 ocr_config.json 의 영역 비율값을 조정하세요. 창 모드라면 window_title 설정으로, 전체화면이라면 monitor 번호로 자동 감지를 맞출 수 있습니다.",
  },
  {
    q: "상대 덱도 자동으로 인식하나요?",
    a: "자동 저장 시 상대 덱은 기본값 '미정'으로 들어갑니다. 화면의 테이블에서 더블클릭해 직접 교정하며, 퍼지 검색이 비슷한 덱 이름을 자동으로 매칭해 줍니다.",
  },
  {
    q: "내 전적 데이터는 어디에 저장되나요?",
    a: "모든 기록은 내 PC의 로컬 SQLite 데이터베이스에 저장됩니다. 언제든 CSV 또는 Excel(.xlsx)로 내보낼 수 있습니다.",
  },
  {
    q: "macOS나 Linux도 지원하나요?",
    a: "현재는 Windows만 지원합니다.",
  },
];

export default function Faq() {
  return (
    <section id="faq" className="relative mx-auto max-w-3xl px-5 py-24">
      <div className="mb-12 text-center">
        <span className="font-display text-sm font-bold tracking-[0.2em] text-teal">
          FAQ
        </span>
        <h2 className="mt-3 text-3xl font-black tracking-tight md:text-4xl">
          자주 묻는 질문
        </h2>
      </div>

      <div className="divide-y divide-white/8 border-y border-white/8">
        {faqs.map((f) => (
          <details key={f.q} className="group py-5">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
              <span className="font-display text-lg font-bold tracking-wide text-white">
                {f.q}
              </span>
              <span className="grid h-7 w-7 shrink-0 place-items-center border border-white/15 text-teal transition-transform group-open:rotate-45">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
                  <path d="M12 5v14M5 12h14" />
                </svg>
              </span>
            </summary>
            <p className="mt-3 pr-10 text-sm leading-relaxed text-mute">{f.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
