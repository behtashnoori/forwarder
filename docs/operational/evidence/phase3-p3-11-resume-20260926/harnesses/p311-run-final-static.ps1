param([string]$EvidenceDirectory,[string]$ProductSha)
$ErrorActionPreference = 'Stop'
$evidence = $EvidenceDirectory
New-Item -ItemType Directory -Force -Path $evidence | Out-Null
$source = (git rev-parse HEAD).Trim()
if ($source -ne $ProductSha -or (git status --porcelain)) { throw 'Source changed' }
$gates = @(
  @{name='app-types';exe='node';args=@('node_modules/typescript/bin/tsc','-p','tsconfig.app.json','--noEmit')},
  @{name='node-types';exe='node';args=@('node_modules/typescript/bin/tsc','-p','tsconfig.node.json','--noEmit')},
  @{name='lint';exe='node';args=@('node_modules/eslint/bin/eslint.js','.')},
  @{name='build';exe='node';args=@('node_modules/vite/bin/vite.js','build')},
  @{name='architecture';exe='python';args=@('scripts/check_architecture_governance.py')},
  @{name='structure';exe='node';args=@('scripts/check-structure.js')},
  @{name='backend-determinism';exe='node';args=@('scripts/check-backend-determinism.js')},
  @{name='diff';exe='git';args=@('diff','--check')},
  @{name='alembic-head';exe='python';args=@('-m','scripts.browser_migration_contract','repository-head')}
)
$results = @()
$env:PYTHONIOENCODING = 'utf-8'
$env:DATABASE_URL = 'sqlite:///:memory:'
$env:TEST_DATABASE_URL = 'sqlite:///:memory:'
foreach ($gate in $gates) {
  $arguments = $gate.args
  & $gate.exe @arguments *> (Join-Path $evidence ($gate.name+'.log'))
  $code = $LASTEXITCODE
  $results += @{name=$gate.name; product_sha=$source; exit_code=$code; status=$(if($code -eq 0){'PASS'}else{'FAIL'})}
  $results | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $evidence 'result.json') -Encoding utf8
  Write-Output "$($gate.name): $code"
}
if ($results | Where-Object { $_.exit_code -ne 0 }) { exit 1 }

if ((git rev-parse HEAD).Trim() -ne $source -or (git status --porcelain)) { throw 'Source changed during static qualification' }
