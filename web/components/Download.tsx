import { site } from "@/lib/site";

const points = [
  "Python · Tesseract 설치 불필요 — 설치 파일에 모두 포함",
  "관리자 권한 없이 설치, 시작 메뉴에서 바로 실행",
  "새 버전이 나오면 앱에서 자동 업데이트 알림",
];

export default function Download() {
  return (
    <section className="relative mx-auto max-w-6xl px-5 py-24">
      <div className="clip-slash relative overflow-hidden border border-teal/30 bg-ink-700 px-8 py-14 md:px-14">
        <div className="pointer-events-none absolute -right-20 -top-20 h-72 w-72 rounded-full bg-teal/15 blur-[120px]" />
        <div className="relative grid items-center gap-10 md:grid-cols-[1.1fr_0.9fr]">
          <div>
            <span className="font-display text-sm font-bold tracking-[0.2em] text-teal">
              DOWNLOAD
            </span>
            <h2 className="mt-3 text-3xl font-black tracking-tight md:text-4xl">
              지금 바로 기록을 시작하세요
            </h2>
            <p className="mt-4 max-w-md text-mute">
              일반 사용자는 설치 파일 하나면 끝. 개발자용 소스 실행 방법은
              GitHub 저장소를 참고하세요.
            </p>

            <ul className="mt-7 space-y-3">
              {points.map((p) => (
                <li key={p} className="flex items-start gap-3 text-sm text-white/85">
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#00e5c0"
                    strokeWidth="2.4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="mt-0.5 shrink-0"
                  >
                    <path d="m5 12 5 5 9-11" />
                  </svg>
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="flex flex-col gap-3">
            <a
              href={site.releasesLatest}
              target="_blank"
              rel="noreferrer"
              className="clip-slash bg-teal px-7 py-4 text-center font-display text-lg font-bold tracking-wide text-teal-ink transition-transform hover:scale-[1.02] active:scale-95"
            >
              Windows용 다운로드
            </a>
            <a
              href={site.github}
              target="_blank"
              rel="noreferrer"
              className="border border-white/15 px-7 py-4 text-center font-display text-base font-bold tracking-wide text-white/90 transition-colors hover:border-teal/60 hover:text-teal"
            >
              GitHub 저장소
            </a>
            <p className="mt-2 text-center text-xs leading-relaxed text-mute-soft">
              {site.platform}
              <br />
              SmartScreen 경고 시 &ldquo;추가 정보 → 실행&rdquo;
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
