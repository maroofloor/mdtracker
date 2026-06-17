"use client";

import { useEffect, useState } from "react";
import { site } from "@/lib/site";

type Props = {
  className?: string;
  children: React.ReactNode;
};

/**
 * 최신 릴리스의 .exe 자산으로 바로 다운로드되는 버튼.
 * - 서버 렌더링/JS 비활성 시: 릴리스 페이지(href 기본값)로 폴백 (점진적 향상)
 * - 마운트 후: GitHub API로 최신 .exe 직링크를 받아 href 교체
 */
export default function DownloadButton({ className, children }: Props) {
  const [href, setHref] = useState<string>(site.releasesLatest);
  const [direct, setDirect] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetch(site.releasesApiLatest, {
      headers: { Accept: "application/vnd.github+json" },
      signal: controller.signal,
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        const assets: Array<{ name?: string; browser_download_url?: string }> =
          data?.assets ?? [];
        const exe = assets.find((a) =>
          a.name?.toLowerCase().endsWith(".exe")
        );
        if (exe?.browser_download_url) {
          setHref(exe.browser_download_url);
          setDirect(true);
        }
      })
      .catch(() => {
        /* 네트워크 실패·레이트리밋 시 릴리스 페이지 폴백 유지 */
      });
    return () => controller.abort();
  }, []);

  return (
    <a
      href={href}
      // 직링크를 받았으면 같은 탭에서 다운로드, 폴백(릴리스 페이지)이면 새 탭
      {...(direct ? {} : { target: "_blank", rel: "noreferrer" })}
      className={className}
    >
      {children}
    </a>
  );
}
