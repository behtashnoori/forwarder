#requires -Version 5.1
[CmdletBinding()]param([Parameter(Mandatory=$true)][string[]]$Paths)
Set-StrictMode -Version Latest;$ErrorActionPreference='Stop'
$reserved=@('pid','error','host','home','matches','args','input','psitem','lastexitcode','executioncontext','myinvocation','psscriptroot')
$failures=[Collections.Generic.List[string]]::new()
foreach($pathValue in $Paths){
    $tokens=$null;$parseErrors=$null;$tree=[Management.Automation.Language.Parser]::ParseFile((Resolve-Path $pathValue),[ref]$tokens,[ref]$parseErrors)
    foreach($parseError in @($parseErrors)){$failures.Add("$pathValue parse: $($parseError.Message)")}
    $assignments=$tree.FindAll({param($node)$node -is [Management.Automation.Language.AssignmentStatementAst]},$true)
    foreach($assignment in @($assignments)){if($assignment.Left -is [Management.Automation.Language.VariableExpressionAst] -and $reserved -contains $assignment.Left.VariablePath.UserPath.ToLowerInvariant()){$failures.Add("$pathValue reserved write: $($assignment.Left.Text)")}}
    $content=Get-Content -Raw -LiteralPath $pathValue
    foreach($forbidden in @('v1.9.5','20260827_org_hostname','20260828_referral_state_compat','docker-compose.production.yml','20260907_direct_shipment_responsibility')){if($content.Contains($forbidden)){$failures.Add("$pathValue stale constant: $forbidden")}}
    if($content -match 'while\s*\(\s*\$true\s*\)' -or $content -match 'for\s*\(\s*;;'){$failures.Add("$pathValue unbounded loop")}
}
if($failures.Count -gt 0){$failures|ForEach-Object {Write-Error $_};exit 1}
Write-Output 'POWERSHELL_PARSE=PASS';Write-Output 'FINAL_SCRIPT_AUDIT=PASS'
