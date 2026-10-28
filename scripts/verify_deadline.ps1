$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host '== Backend regression suite ==' -ForegroundColor Cyan
python -m pytest tests -q

Write-Host '== Fixture governance ==' -ForegroundColor Cyan
python tests/fixtures/validate_ai_fixtures.py
python tests/fixtures/validate_review_fixtures.py

Write-Host '== Frontend dependencies ==' -ForegroundColor Cyan
Set-Location (Join-Path $RepoRoot 'frontend')
npm install

Write-Host '== Frontend component/integration tests ==' -ForegroundColor Cyan
npm run test

Write-Host '== Frontend production build ==' -ForegroundColor Cyan
npm run build

Write-Host '== OpenAPI / TypeScript contract synchronization ==' -ForegroundColor Cyan
Set-Location $RepoRoot
python scripts/verify_contracts.py

Write-Host ''
Write-Host 'ALL DEADLINE VERIFICATION CHECKS PASSED.' -ForegroundColor Green
Write-Host 'The production React 18 frontend build is in docs/ ready for FastAPI and GitHub Pages.'
