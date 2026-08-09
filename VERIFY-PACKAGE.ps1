$ErrorActionPreference = "Stop"
$manifestPath = Join-Path $PSScriptRoot "release-manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath)) { throw "Missing release-manifest.json" }
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
if ($manifest.application_version -ne "1.8.0" -or $manifest.previous_version -ne "1.7.0") { throw "Version mismatch" }
if ($manifest.git_tag -ne "v1.8.0" -or $manifest.git_commit -ne $manifest.backend_revision) { throw "Git identity mismatch" }
if ($manifest.database_revision -ne "20260811_project_configuration" -or $manifest.previous_database_revision -ne "20260810_logistics_network" -or -not $manifest.database_migration_included) { throw "Database metadata mismatch" }
if ($manifest.production_seed_executed -ne $false) { throw "Seed metadata mismatch" }
if ($manifest.milestone_type_catalog_apply_status -ne "not applied") { throw "Catalog apply metadata mismatch" }
$python = (Get-Command python -ErrorAction Stop).Source
$actualHash = & $python -c "import hashlib,pathlib,sys;r=pathlib.Path(sys.argv[1]);s=''.join(p.relative_to(r).as_posix()+chr(0)+hashlib.sha256(p.read_bytes()).hexdigest()+chr(10) for p in sorted(x for x in r.rglob('*') if x.is_file() and x.name!='release-manifest.json'));print(hashlib.sha256(s.encode()).hexdigest())" $PSScriptRoot
if ($actualHash -ne $manifest.package_hash) { throw "Package hash mismatch: actual=$actualHash expected=$($manifest.package_hash)" }
$required = @("index.html", $manifest.frontend_entry_js, $manifest.frontend_entry_css, "web.config", "manage.py", "requirements.txt", "DEPLOYMENT.md", "SMOKE-TEST.md", "ROLLBACK.md", "MIGRATION-PREFLIGHT.md", "VERIFY-SERVER.ps1", "backend/migrations/versions/20260810_logistics_network.py", "backend/migrations/versions/20260811_project_configuration.py", $manifest.milestone_type_catalog_filename)
foreach ($item in $required) { if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $item))) { throw "Missing required file: $item" } }
$requirements = @(Get-Content -LiteralPath (Join-Path $PSScriptRoot "requirements.txt") | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith("#") })
if ($requirements -notcontains "psycopg2-binary==2.9.11") { throw "Missing exact PostgreSQL runtime driver declaration: psycopg2-binary==2.9.11" }
$catalogHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $PSScriptRoot $manifest.milestone_type_catalog_filename)).Hash.ToLowerInvariant()
if ($catalogHash -ne $manifest.milestone_type_catalog_sha256) { throw "Catalog checksum mismatch" }
$forbiddenNames = @(".env", "node_modules", "venv", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".git", ".github", ".codex", "tests")
$forbidden = Get-ChildItem -LiteralPath $PSScriptRoot -Recurse -Force | Where-Object { $_.Name -in $forbiddenNames -or $_.Extension -in @(".map", ".pyc", ".tsbuildinfo", ".log", ".db", ".sqlite") -or ($_.PSIsContainer -and $_.Name -like "release-v*") }
if ($forbidden) { throw "Forbidden package content detected: $($forbidden[0].FullName)" }
$secretPatterns = '(?i)(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|postgres(?:ql)?://[^\s:@]+:[^\s@]+@|(?:password|secret|api[_-]?key)\s*[=:]\s*["''][^"'']+["''])'
$secretHit = Get-ChildItem -LiteralPath $PSScriptRoot -Recurse -File | Where-Object { $_.Extension -notin @('.png','.jpg','.jpeg','.ico','.woff','.woff2') } | Select-String -Pattern $secretPatterns -List -ErrorAction SilentlyContinue | Select-Object -First 1
if ($secretHit) { throw "Potential secret pattern detected in $($secretHit.Path)" }
[xml]$config = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot "web.config")
$rules = @($config.configuration.'system.webServer'.rewrite.rules.rule)
if ($rules[0].match.url -ne '^api/(.*)' -or $rules[1].name -notmatch 'SPA') { throw "Rewrite order mismatch" }
$outbound = @($config.configuration.'system.webServer'.rewrite.outboundRules.rule)
if (-not ($outbound.action.value -contains "no-cache, no-store, must-revalidate") -or -not ($outbound.action.value -contains "public, max-age=31536000, immutable") -or -not ($outbound.action.value -contains "public, max-age=0, must-revalidate")) { throw "Cache policy mismatch" }
$seedAutoRun = Get-ChildItem -LiteralPath $PSScriptRoot -Recurse -File -Include *.ps1,*.bat,*.cmd,*.yml,*.yaml | Select-String -Pattern '(?i)(reference.*seed.*apply|seed.*--apply|milestone.*catalog.*apply)' -List -ErrorAction SilentlyContinue | Where-Object { $_.Path -notlike '*MIGRATION-PREFLIGHT.md' }
if ($seedAutoRun) { throw "Possible automatic Seed execution detected" }
$files = @(Get-ChildItem -LiteralPath $PSScriptRoot -Recurse -File)
$bytes = ($files | Measure-Object -Property Length -Sum).Sum
Write-Output "package=PASS hash=$actualHash files=$($files.Count) bytes=$bytes"
