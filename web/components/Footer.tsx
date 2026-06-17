import { site } from "@/lib/site";

export default function Footer() {
  return (
    <footer className="border-t border-white/8 bg-ink-800">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 px-5 py-10 sm:flex-row">
        <div className="flex items-center gap-2.5">
          <span className="grid h-7 w-7 place-items-center bg-teal text-teal-ink clip-slash-sm">
            <span className="font-display text-base font-bold leading-none">M</span>
          </span>
          <div>
            <div className="font-display text-base font-bold tracking-wide">
              {site.name}
            </div>
            <div className="text-xs text-mute-soft">{site.tagline}</div>
          </div>
        </div>

        <div className="flex items-center gap-7 text-sm text-mute">
          <a href="#features" className="transition-colors hover:text-white">
            기능
          </a>
          <a href="#how" className="transition-colors hover:text-white">
            사용법
          </a>
          <a href="#faq" className="transition-colors hover:text-white">
            FAQ
          </a>
          <a
            href={site.github}
            target="_blank"
            rel="noreferrer"
            className="transition-colors hover:text-white"
          >
            GitHub
          </a>
        </div>
      </div>
      <div className="border-t border-white/5 py-5 text-center text-xs text-mute-soft">
        MDTracker is a fan-made tool and is not affiliated with Konami or
        Yu-Gi-Oh! Master Duel. · MIT License
      </div>
    </footer>
  );
}
