#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$EnvironmentFile = 'C:\1-webapp\forwarder-runtime\production.env',
    [string]$ApprovedBackupRoot = 'C:\1-webapp\forwarder-backups',
    [string]$PgDumpPath = 'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe',
    [string]$PgRestorePath = 'C:\Program Files\PostgreSQL\18\bin\pg_restore.exe',
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$RestoreOwner,
    [ValidateRange(1,3650)][int]$RetentionDays = 30,
    [switch]$ValidateOnly,
    [switch]$CreateBackup,
    [switch]$ConfirmBackup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
function Stop-Backup([string]$Message) { throw "BACKUP_BLOCKED: $Message" }
function Hash-Text([string]$Value) { $a=[Security.Cryptography.SHA256]::Create();try{return([BitConverter]::ToString($a.ComputeHash([Text.Encoding]::UTF8.GetBytes($Value)))).Replace('-','').ToLowerInvariant()}finally{$a.Dispose()} }
function Read-Map([string]$Path){$m=@{};if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){Stop-Backup 'environment file missing'};foreach($line in Get-Content -LiteralPath $Path){if($line.Trim() -and -not $line.TrimStart().StartsWith('#') -and $line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$'){$m[$Matches[1]]=$Matches[2].Trim().Trim('"').Trim("'")}};return $m}
function Connection([hashtable]$Map){if(-not $Map.ContainsKey('DATABASE_URL')){Stop-Backup 'DATABASE_URL absent'};try{$u=[Uri][string]$Map['DATABASE_URL'];$ui=$u.UserInfo.Split(':',2);$name=[Uri]::UnescapeDataString($u.AbsolutePath.Trim('/'));$user=[Uri]::UnescapeDataString($ui[0]);$password=if($ui.Count-eq 2){[Uri]::UnescapeDataString($ui[1])}else{''};if($u.Scheme-notin@('postgres','postgresql')-or$u.Host-notmatch'^[A-Za-z0-9_.:-]+$'-or$name-notmatch'^[A-Za-z0-9_.-]+$'-or$user-notmatch'^[A-Za-z0-9_.-]+$'){Stop-Backup 'database connection identity invalid'};return [pscustomobject]@{Host=$u.Host;Port=$(if($u.Port-gt 0){$u.Port}else{5432});Database=$name;User=$user;Password=$password}}catch{Stop-Backup 'database connection identity unavailable'}}
function Run-Tool([string]$File,[string]$Arguments,[object]$Db,[int]$TimeoutSeconds){$s=New-Object Diagnostics.ProcessStartInfo;$s.FileName=$File;$s.Arguments=$Arguments;$s.UseShellExecute=$false;$s.CreateNoWindow=$true;$s.RedirectStandardOutput=$true;$s.RedirectStandardError=$true;if($Db.Password){$s.EnvironmentVariables['PGPASSWORD']=$Db.Password};$p=New-Object Diagnostics.Process;$p.StartInfo=$s;try{if(-not$p.Start()){Stop-Backup 'tool start failed'};$stdout=$p.StandardOutput.ReadToEndAsync();$stderr=$p.StandardError.ReadToEndAsync();if(-not$p.WaitForExit($TimeoutSeconds*1000)){$p.Kill();Stop-Backup 'tool timeout'};return [pscustomobject]@{ExitCode=$p.ExitCode;Stdout=[string]$stdout.Result;Stderr=[string]$stderr.Result}}finally{if($s.EnvironmentVariables.ContainsKey('PGPASSWORD')){$s.EnvironmentVariables.Remove('PGPASSWORD')};$p.Dispose()}}

if($ValidateOnly -and $CreateBackup){Stop-Backup 'choose one mode'}
if(-not $ValidateOnly -and -not $CreateBackup){$ValidateOnly=$true}
if($CreateBackup -and -not $ConfirmBackup){Stop-Backup 'explicit backup confirmation required'}
foreach($path in @($ApprovedBackupRoot,$PgDumpPath,$PgRestorePath,$EnvironmentFile)){if(-not(Test-Path -LiteralPath $path)){Stop-Backup "required path unavailable: $path"}}
$db=Connection (Read-Map $EnvironmentFile)
$drive=Get-PSDrive -PSProvider FileSystem | Where-Object {$ApprovedBackupRoot.StartsWith($_.Root,[StringComparison]::OrdinalIgnoreCase)} | Select-Object -First 1
if(-not$drive -or $drive.Free -le 0){Stop-Backup 'backup destination capacity unavailable'}
$dumpVersion=Run-Tool $PgDumpPath '--version' ([pscustomobject]@{Password=''}) 30
$restoreVersion=Run-Tool $PgRestorePath '--version' ([pscustomobject]@{Password=''}) 30
if($dumpVersion.ExitCode-ne 0 -or $restoreVersion.ExitCode-ne 0){Stop-Backup 'backup tooling unavailable'}
if($ValidateOnly){Write-Output 'BACKUP_VALIDATE_ONLY=PASS';Write-Output ('BACKUP_DESTINATION_FREE_BYTES='+[int64]$drive.Free);Write-Output 'PRODUCTION_MUTATION_PERFORMED=NO';exit 0}

$stamp=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$dump=Join-Path $ApprovedBackupRoot "forwarder-v1.10.0-predeploy-$stamp.dump"
$catalog=$dump+'.list.txt';$hashFile=$dump+'.sha256.txt';$evidence=$dump+'.evidence.json'
foreach($path in @($dump,$catalog,$hashFile,$evidence)){if(Test-Path -LiteralPath $path){Stop-Backup 'backup output collision'}}
$args='-Fc -w -h "'+$db.Host+'" -p '+$db.Port+' -U "'+$db.User+'" -d "'+$db.Database+'" -f "'+$dump+'"'
$created=Run-Tool $PgDumpPath $args $db 3600
if($created.ExitCode-ne 0 -or -not(Test-Path -LiteralPath $dump -PathType Leaf) -or (Get-Item -LiteralPath $dump).Length-le 0){Stop-Backup 'pg_dump failed or produced an empty dump'}
$listed=Run-Tool $PgRestorePath ('--list "'+$dump+'"') ([pscustomobject]@{Password=''}) 300
if($listed.ExitCode-ne 0 -or [string]::IsNullOrWhiteSpace($listed.Stdout)){Stop-Backup 'pg_restore catalog verification failed'}
$utf8=New-Object Text.UTF8Encoding($false);[IO.File]::WriteAllText($catalog,$listed.Stdout,$utf8)
$hash=(Get-FileHash -Algorithm SHA256 -LiteralPath $dump).Hash.ToLowerInvariant()
[IO.File]::WriteAllText($hashFile,"$hash  $([IO.Path]::GetFileName($dump))`n",[Text.Encoding]::ASCII)
$record=[ordered]@{schema='forwarder-v1.10.0-predeployment-backup-evidence-v1';created_utc=[DateTime]::UtcNow.ToString('o');database_name_sha256=Hash-Text $db.Database;database_role_sha256=Hash-Text $db.User;backup_path=$dump;dump_size_bytes=(Get-Item -LiteralPath $dump).Length;dump_sha256=$hash;pg_dump_exit_code=$created.ExitCode;pg_restore_list_exit_code=$listed.ExitCode;catalog_path=$catalog;sha256_sidecar_path=$hashFile;approved_backup_root=(Resolve-Path -LiteralPath $ApprovedBackupRoot).Path;destination_free_bytes_before=[int64]$drive.Free;retention_days=$RetentionDays;restore_owner=$RestoreOwner;verified=$true}
[IO.File]::WriteAllText($evidence,(($record|ConvertTo-Json -Depth 6)+"`n"),$utf8)
$db.Password=$null
Write-Output 'PREDEPLOYMENT_BACKUP=PASS'
Write-Output ('BACKUP_EVIDENCE='+$evidence)
Write-Output ('BACKUP_SHA256='+$hash)
