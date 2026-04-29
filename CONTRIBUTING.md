# Contributing

이 프로젝트는 포트폴리오 사이드 프로젝트로 시작했지만, 의견·이슈·PR 환영합니다.

## 시작하기

1. 저장소 fork → clone
2. `docs/08-deployment.md`의 "로컬 실행" 섹션 따라 환경 구성
3. 새 브랜치 생성:
   ```bash
   git checkout -b feat/your-feature
   ```
4. 작업 후 PR

## 코드 스타일

### Python
- Python 3.12+ 권장 (HF Space 환경)
- 한국어 주석 환영. 영문도 OK
- 함수는 짧고 명확하게, 단일 책임
- 명시적 에러 처리 (try/except에 의미 있는 메시지)
- 출력 메시지에 이모지 자제 (Windows 콘솔 인코딩 이슈)

### TypeScript / JSX
- React 19 + 함수 컴포넌트 + hooks
- Tailwind 우선, 커스텀 CSS 최소화
- 컴포넌트는 한 파일 한 책임

## 변경하면 안 되는 것

- 작품 텍스트·이미지(`data/raw/`) — 공공누리 3유형 라이선스 (변경 금지)
- `LICENSE` 의 데이터 라이선스 조항

## 커밋 메시지

각 마일스톤은 `vX.Y` 태그 + 한글 요약으로:

```
v2.4: 리브랜딩 — K-Curator → 사이 (SAI)

- 헤더 로고 letter-spacing
- 시스템 프롬프트의 자기소개
- 줄바꿈 break-keep
```

## PR 체크리스트

- [ ] 새 기능이라면 `docs/05-features.md` 또는 `docs/09-roadmap.md` 갱신
- [ ] 새 API 엔드포인트라면 `docs/04-api-reference.md` 갱신
- [ ] 새 의존성 — `requirements.txt` 또는 `package.json` 핀 버전
- [ ] CHANGELOG.md 에 항목 추가
- [ ] 로컬에서 `npm run build` + 백엔드 부팅 + 핵심 페이지 200 확인

## 이슈 가이드

가능하면 다음 정보 포함:
- 발생 페이지 / 엔드포인트
- 재현 단계
- 기대한 결과 vs 실제 결과
- 스크린샷 (UX 이슈)
- 콘솔 로그 / 네트워크 응답 (백엔드 이슈)
