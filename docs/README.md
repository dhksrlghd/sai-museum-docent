# 사이 (SAI) · 문서 모음

> **국립중앙박물관 큐레이터 해설을 기반으로 작품과 관람객 사이를 잇는, 풀스택 RAG·멀티모달 도슨트.**

이 폴더는 프로젝트의 모든 설계·구현·운영 내역을 정리한 곳입니다.
빠르게 훑고 싶다면 [01-overview.md](./01-overview.md), 깊이 보고 싶다면 순서대로.

## 문서 지도

| # | 문서 | 무엇을 담았나 |
|---|---|---|
| 01 | [개요 (Overview)](./01-overview.md) | 왜 만들었나, 누구를 위한 것인가, 한 줄 정의 |
| 02 | [아키텍처 (Architecture)](./02-architecture.md) | 시스템 구성도, 데이터 흐름, 기술 스택 선택 이유 |
| 03 | [데이터 파이프라인 (Data Pipeline)](./03-data-pipeline.md) | 스크래핑 → 청킹 → 임베딩 → Chroma 인덱스 |
| 04 | [API 레퍼런스 (API Reference)](./04-api-reference.md) | 9개 엔드포인트 명세 + 요청/응답 예시 |
| 05 | [핵심 기능 (Features)](./05-features.md) | RAG, 멀티모달, 코스 빌더, 매일 픽 — deep dive |
| 06 | [엔지니어링 결정 (Engineering Decisions)](./06-engineering-decisions.md) | 왜 그 스택, 왜 그 모델, 무엇을 포기했나 |
| 07 | [개발 일지 (Dev Journey)](./07-development-journey.md) | v1.0 → v2.3 변천사, 각 라운드의 회고 |
| 08 | [배포 (Deployment)](./08-deployment.md) | HF Spaces Docker SDK 단일 컨테이너 배포 |
| 09 | [로드맵 (Roadmap)](./09-roadmap.md) | 알려진 한계 + 다음 발전 후보 |

## 한눈에 보는 숫자

| 지표 | 값 |
|---|---|
| 데이터 — 큐레이터 추천 작품 | 321점 |
| 데이터 — 상설전시 작품 | 643점 (7관 36실) |
| 데이터 — 진행중 특별·테마전 | 5건 |
| 텍스트 청크 (Chroma) | **1,265개** |
| 이미지 임베딩 (CLIP) | **733장** |
| 본문 글자 수 | 약 130만 자 |
| 페이지 수 | 6 (홈/코스/전시/소장품/상세/AI도슨트) |
| API 엔드포인트 | 9 |
| 코드 — Python | ~2,200 라인 |
| 코드 — React/JSX | ~1,500 라인 |
| 누적 커밋 | v1.0 → v2.3 (5 마일스톤) |

## 빠른 시작

라이브 데모: [https://wangihong-k-curator.hf.space](https://wangihong-k-curator.hf.space)

로컬 실행: 루트 [`README.md`](../README.md) → "로컬 실행" 섹션
