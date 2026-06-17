const features = [
  {
    icon: "scan",
    title: "자동 OCR 기록",
    body: "게임 화면을 실시간 캡처해 코인토스 승패, 선후공, 듀얼 결과를 자동으로 감지합니다. 손댈 필요 없이 한 판이 끝나면 기록이 쌓입니다.",
  },
  {
    icon: "edit",
    title: "수동 기록 · 교정",
    body: "OCR 없이 직접 결과를 입력하거나, 자동 인식된 내용을 한 번에 교정할 수 있습니다. 상대 덱은 더블클릭으로 바로 수정.",
  },
  {
    icon: "chart",
    title: "대시보드 통계",
    body: "전체 승률, 덱별 매치업, 메타 분포, 기간별 추세까지 4개 탭으로 한눈에. 필터바로 기간·내 덱·상대 덱을 좁혀 분석합니다.",
  },
  {
    icon: "deck",
    title: "덱 관리",
    body: "내 덱 목록을 만들고 수정·삭제. 퍼지 검색으로 OCR이 잘못 읽은 덱 이름도 자동으로 매칭해 정리합니다.",
  },
  {
    icon: "export",
    title: "CSV · Excel 내보내기",
    body: "전적 데이터를 .csv 또는 .xlsx로 저장해 원하는 도구에서 추가 분석. 내 기록은 항상 내 손안에.",
  },
  {
    icon: "theme",
    title: "다크 테마 GUI",
    body: "PySide6 기반 커스텀 프레임리스 창. 게임 분위기에 어울리는 다크 인터페이스로 오래 켜둬도 눈이 편합니다.",
  },
];

function Icon({ name }: { name: string }) {
  const common = {
    width: 22,
    height: 22,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  switch (name) {
    case "scan":
      return (
        <svg {...common}>
          <path d="M4 7V5a1 1 0 0 1 1-1h2M17 4h2a1 1 0 0 1 1 1v2M20 17v2a1 1 0 0 1-1 1h-2M7 20H5a1 1 0 0 1-1-1v-2" />
          <path d="M4 12h16" />
        </svg>
      );
    case "edit":
      return (
        <svg {...common}>
          <path d="M12 20h9" />
          <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
        </svg>
      );
    case "chart":
      return (
        <svg {...common}>
          <path d="M3 3v18h18" />
          <rect x="7" y="11" width="3" height="6" />
          <rect x="12" y="7" width="3" height="10" />
          <rect x="17" y="13" width="3" height="4" />
        </svg>
      );
    case "deck":
      return (
        <svg {...common}>
          <rect x="3" y="5" width="13" height="16" rx="1.5" />
          <path d="M8 3h11a1 1 0 0 1 1 1v13" />
        </svg>
      );
    case "export":
      return (
        <svg {...common}>
          <path d="M12 3v12" />
          <path d="m8 7 4-4 4 4" />
          <path d="M5 15v4a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-4" />
        </svg>
      );
    default:
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 3a9 9 0 0 0 0 18Z" fill="currentColor" stroke="none" />
        </svg>
      );
  }
}

export default function Features() {
  return (
    <section id="features" className="relative mx-auto max-w-6xl px-5 py-24">
      <div className="mb-14 max-w-xl">
        <span className="font-display text-sm font-bold tracking-[0.2em] text-teal">
          FEATURES
        </span>
        <h2 className="mt-3 text-3xl font-black tracking-tight md:text-4xl">
          기록은 자동으로, 분석은 한눈에
        </h2>
        <p className="mt-4 text-mute">
          한 번 켜두면 듀얼이 끝날 때마다 노트가 채워집니다. 흩어진 판수가
          승률과 메타가 되어 돌아옵니다.
        </p>
      </div>

      <div className="grid gap-px overflow-hidden border border-white/10 bg-white/10 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((f) => (
          <div
            key={f.title}
            className="group bg-ink-800 p-7 transition-colors hover:bg-ink-700"
          >
            <div className="clip-slash-sm grid h-11 w-11 place-items-center bg-teal/10 text-teal transition-colors group-hover:bg-teal group-hover:text-teal-ink">
              <Icon name={f.icon} />
            </div>
            <h3 className="mt-5 font-display text-xl font-bold tracking-wide">
              {f.title}
            </h3>
            <p className="mt-2.5 text-sm leading-relaxed text-mute">{f.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
