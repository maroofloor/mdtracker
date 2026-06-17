"use client";

import { useEffect, useState } from "react";
import { site } from "@/lib/site";
import DownloadButton from "./DownloadButton";

const links = [
  { href: "#features", label: "기능" },
  { href: "#how", label: "사용법" },
  { href: "#faq", label: "FAQ" },
];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-colors duration-300 ${
        scrolled
          ? "border-b border-white/5 bg-ink/80 backdrop-blur-md"
          : "border-b border-transparent bg-transparent"
      }`}
    >
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <a href="#top" className="flex items-center gap-2.5">
          <span className="grid h-7 w-7 place-items-center bg-teal text-teal-ink clip-slash-sm">
            <span className="font-display text-base font-bold leading-none">M</span>
          </span>
          <span className="font-display text-lg font-bold tracking-wide">
            {site.name}
          </span>
        </a>

        <div className="hidden items-center gap-8 md:flex">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-sm text-mute transition-colors hover:text-white"
            >
              {l.label}
            </a>
          ))}
        </div>

        <DownloadButton className="clip-slash-sm bg-teal px-4 py-2 font-display text-sm font-bold text-teal-ink transition-transform hover:scale-[1.03] active:scale-95">
          다운로드
        </DownloadButton>
      </nav>
    </header>
  );
}
