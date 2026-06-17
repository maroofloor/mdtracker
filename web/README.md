# MDTracker — 랜딩페이지

MDTracker 데스크톱 앱을 소개·다운로드·사용법 안내하는 마케팅 랜딩페이지.
Next.js (App Router) + Tailwind CSS, Vercel 배포용.

## 로컬 실행

```bash
cd web
npm install
npm run dev
# http://localhost:3000
```

## 빌드

```bash
npm run build
npm run start
```

## 스크린샷 교체

`public/screenshots/` 의 placeholder PNG를 같은 파일명으로 덮어쓰면 끝.
자세한 건 `public/screenshots/README.md` 참고.

## Vercel 배포

1. 이 저장소를 Vercel에 import
2. **Root Directory** 를 `web` 로 지정
3. Framework: Next.js (자동 감지) → Deploy

> 참고: 루트 `.gitignore`에서 `web/` 가 무시 처리되어 있습니다.
> 웹을 git에 올려 Vercel과 연동하려면 해당 라인을 해제하세요.

## 구조

```
web/
├── app/
│   ├── layout.tsx        # 폰트 · 메타데이터
│   ├── page.tsx          # 섹션 조립
│   └── globals.css       # 테마 · clip-path 유틸
├── components/           # Nav / Hero / Features / HowItWorks / Download / Faq / Footer
├── lib/site.ts           # 다운로드·GitHub 링크 등 상수
└── public/screenshots/   # 교체용 placeholder 이미지
```

## 커스터마이즈 포인트

- 다운로드/GitHub 링크: `lib/site.ts`
- 액센트 색(teal `#00e5c0`): `tailwind.config.ts` 의 `colors.teal`
- 히어로 카피: `components/Hero.tsx`
