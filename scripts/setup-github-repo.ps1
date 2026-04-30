# 사이 (SAI) — GitHub 저장소 메타데이터 일괄 설정 헬퍼
#
# About 사이드바의 description, homepage, topics 를
# GitHub API 한 번 호출로 채워넣습니다.
#
# 사용법:
#   1. fine-grained 또는 classic 토큰 (Contents: RW + Administration: RW 권한)
#   2. PowerShell:
#        $env:GITHUB_TOKEN = "ghp_... 또는 github_pat_..."
#        .\scripts\setup-github-repo.ps1
#   3. 끝나면 환경변수 정리: Remove-Item env:GITHUB_TOKEN

$ErrorActionPreference = "Stop"

$owner = "dhksrlghd"
$repo  = "sai-museum-docent"
$token = $env:GITHUB_TOKEN

if (-not $token) {
    Write-Host "❌ GITHUB_TOKEN 환경변수가 없습니다." -ForegroundColor Red
    Write-Host '   $env:GITHUB_TOKEN = "github_pat_..." 먼저 설정하세요.'
    exit 1
}

$headers = @{
    "Authorization" = "Bearer $token"
    "Accept"        = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

# 1) 저장소 description + homepage 설정
Write-Host "→ 저장소 description / homepage 설정..."
$repoBody = @{
    description = "작품과 당신 사이를 잇다 — 국립중앙박물관 큐레이터 해설 기반 RAG·멀티모달 박물관 도슨트"
    homepage    = "https://wangihong-k-curator.hf.space"
    has_issues  = $true
    has_projects = $false
    has_wiki    = $false
} | ConvertTo-Json

Invoke-RestMethod -Method Patch `
  -Uri "https://api.github.com/repos/$owner/$repo" `
  -Headers $headers `
  -Body $repoBody `
  -ContentType "application/json" | Out-Null
Write-Host "  ✓ description / homepage 적용"

# 2) Topics 설정
Write-Host "→ Topics 설정..."
$topicsBody = @{
    names = @(
        "rag",
        "multimodal",
        "museum",
        "korean-art",
        "fastapi",
        "react",
        "chroma",
        "clip",
        "openai",
        "sentence-transformers",
        "huggingface-spaces",
        "portfolio"
    )
} | ConvertTo-Json

Invoke-RestMethod -Method Put `
  -Uri "https://api.github.com/repos/$owner/$repo/topics" `
  -Headers $headers `
  -Body $topicsBody `
  -ContentType "application/json" | Out-Null
Write-Host "  ✓ Topics 12개 적용"

Write-Host ""
Write-Host "✅ 완료. 확인: https://github.com/$owner/$repo" -ForegroundColor Green
