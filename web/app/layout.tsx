import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MDTracker — 듀얼리스트의 전적 노트",
  description:
    "Steam Yu-Gi-Oh! Master Duel 플레이 화면을 자동 인식해 코인토스·선후공·승패를 기록하고 통계로 정리하는 데스크톱 트래커.",
  keywords: [
    "마스터 듀얼",
    "Master Duel",
    "유희왕",
    "전적",
    "트래커",
    "승률",
    "코인토스",
    "OCR",
  ],
  openGraph: {
    title: "MDTracker — 듀얼리스트의 전적 노트",
    description:
      "켜두면 알아서 쌓이는 Master Duel 자동 전적 트래커. 코인토스·선후공·승률을 화면 인식으로 기록한다.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&family=Rajdhani:wght@500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
