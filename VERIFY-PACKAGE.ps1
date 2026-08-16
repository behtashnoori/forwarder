$ErrorActionPreference = "Stop"
$manifestPath = Join-Path $PSScriptRoot "release-manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath)) { throw "Missing release-manifest.json" }
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
if ($manifest.application_version -ne "1.9.5" -or $manifest.previous_version -ne "1.9.4") { throw "Version mismatch" }
if ($manifest.git_tag -ne "v1.9.5" -or $manifest.git_commit -ne $manifest.backend_revision -or -not $manifest.git_tree -or -not $manifest.git_tag_object) { throw "Git identity mismatch" }
$expectedRevisions = @("20260827_org_hostname")
if ($manifest.database_revision -ne "20260827_org_hostname" -or $manifest.production_baseline_revision -ne "20260826_org_document_policy" -or $manifest.previous_database_revision -ne "20260826_org_document_policy" -or -not $manifest.database_migration_included) { throw "Database metadata mismatch" }
if ((@($manifest.upgrade_revisions) -join "|") -ne ($expectedRevisions -join "|")) { throw "Migration path mismatch" }
if ($manifest.rollback_release -ne "v1.9.4" -or $null -ne $manifest.rollback_restore_required_from_revision) { throw "Rollback metadata mismatch" }
if ($manifest.production_seed_executed -ne $false) { throw "Seed metadata mismatch" }
if ($manifest.milestone_type_catalog_apply_status -ne "not applied") { throw "Catalog apply metadata mismatch" }
$python = (Get-Command python -ErrorAction Stop).Source
$actualHash = & $python -c "import hashlib,pathlib,sys;r=pathlib.Path(sys.argv[1]);s=''.join(p.relative_to(r).as_posix()+chr(0)+hashlib.sha256(p.read_bytes()).hexdigest()+chr(10) for p in sorted(x for x in r.rglob('*') if x.is_file() and x.name!='release-manifest.json'));print(hashlib.sha256(s.encode()).hexdigest())" $PSScriptRoot
if ($actualHash -ne $manifest.package_hash) { throw "Package hash mismatch: actual=$actualHash expected=$($manifest.package_hash)" }
$required = @("index.html", $manifest.frontend_entry_js, $manifest.frontend_entry_css, "web.config", "manage.py", "requirements.txt", "Dockerfile", "docker-compose.production.yml", "DEPLOYMENT.md", "SMOKE-TEST.md", "ROLLBACK.md", "MIGRATION-PREFLIGHT.md", "VERIFY-PACKAGE.ps1", "VERIFY-SERVER.ps1", "verify_package_secrets.py", $manifest.milestone_type_catalog_filename)
foreach ($migration in @($manifest.migration_files)) { $required += $migration.path }
foreach ($item in $required) { if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $item))) { throw "Missing required file: $item" } }
$index = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot "index.html")
if ($index -match '/src/main\.tsx' -or $index -notmatch '/assets/.+\.js') { throw "Frontend index is not a production build" }
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot "assets") -PathType Container)) { throw "Missing production assets directory" }
$requirementsHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $PSScriptRoot "requirements.txt")).Hash.ToLowerInvariant()
if ($requirementsHash -ne $manifest.requirements_sha256) { throw "Requirements checksum mismatch" }
$requirements = @(Get-Content -LiteralPath (Join-Path $PSScriptRoot "requirements.txt") | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith("#") })
if ($requirements -notcontains "psycopg2-binary==2.9.11") { throw "Missing exact PostgreSQL runtime driver declaration: psycopg2-binary==2.9.11" }
$catalogHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $PSScriptRoot $manifest.milestone_type_catalog_filename)).Hash.ToLowerInvariant()
if ($catalogHash -ne $manifest.milestone_type_catalog_sha256) { throw "Catalog checksum mismatch" }
foreach ($migration in @($manifest.migration_files)) { $migrationHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $PSScriptRoot $migration.path)).Hash.ToLowerInvariant(); if ($migrationHash -ne $migration.sha256) { throw "Migration checksum mismatch: $($migration.revision)" } }
$forbiddenNames = @(".env", "node_modules", "venv", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".git", ".github", ".codex", "tests")
$forbidden = Get-ChildItem -LiteralPath $PSScriptRoot -Recurse -Force | Where-Object { $_.Name -in $forbiddenNames -or $_.Extension -in @(".map", ".pyc", ".tsbuildinfo", ".log", ".db", ".sqlite") -or ($_.PSIsContainer -and $_.Name -like "release-v*") }
if ($forbidden) { throw "Forbidden package content detected: $($forbidden[0].FullName)" }
& $python (Join-Path $PSScriptRoot "verify_package_secrets.py") $PSScriptRoot
if ($LASTEXITCODE -ne 0) { throw "Package secret policy failed" }
[xml]$config = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot "web.config")
$rules = @($config.configuration.'system.webServer'.rewrite.rules.rule)
if ($rules[0].match.url -ne '^api/(.*)' -or $rules[1].name -notmatch 'SPA') { throw "Rewrite order mismatch" }
$outbound = @($config.configuration.'system.webServer'.rewrite.outboundRules.rule)
if (-not ($outbound.action.value -contains "no-cache, no-store, must-revalidate") -or -not ($outbound.action.value -contains "public, max-age=31536000, immutable") -or -not ($outbound.action.value -contains "public, max-age=0, must-revalidate")) { throw "Cache policy mismatch" }
$seedControlFiles = @("VERIFY-PACKAGE.ps1", "VERIFY-SERVER.ps1")
$seedAutoRun = Get-ChildItem -LiteralPath $PSScriptRoot -Recurse -File | Where-Object { $_.Extension -in @('.ps1','.bat','.cmd','.yml','.yaml') -and $_.Name -notin $seedControlFiles } | Select-String -Pattern '(?i)(reference.*seed.*apply|seed.*--apply|milestone.*catalog.*apply)' -List -ErrorAction SilentlyContinue
if ($seedAutoRun) { throw "Possible automatic Seed execution detected" }
$files = @(Get-ChildItem -LiteralPath $PSScriptRoot -Recurse -File)
$bytes = ($files | Measure-Object -Property Length -Sum).Sum
Write-Output "package=PASS hash=$actualHash files=$($files.Count) bytes=$bytes"
