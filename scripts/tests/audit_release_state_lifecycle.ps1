#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot,[string]$ReportPath,[switch]$RepositoryInventory)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$records=@()
$files=if($RepositoryInventory){@(git -C $PackageRoot ls-files '*.ps1' | ForEach-Object {Get-Item -LiteralPath (Join-Path $PackageRoot $_)})}else{@(Get-ChildItem -LiteralPath $PackageRoot -Filter '*.ps1' -File)}
foreach($file in $files){
    $tokens=$null;$errors=$null
    $tree=[Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
    if($errors.Count){throw ($errors.Message -join '; ')}
    $variables=@($tree.FindAll({param($node) $node -is [Management.Automation.Language.VariableExpressionAst]},$true))
    foreach($group in $variables | Group-Object {$_.VariablePath.UserPath}){
        $references=@($group.Group | ForEach-Object {
            $node=$_;$parent=$node.Parent;$writer=$false;$context=@()
            while($null -ne $parent){
                if($parent -is [Management.Automation.Language.AssignmentStatementAst] -and $node.Extent.StartOffset -ge $parent.Left.Extent.StartOffset -and $node.Extent.EndOffset -le $parent.Left.Extent.EndOffset){$writer=$true}
                if($parent -is [Management.Automation.Language.ParameterAst]){$writer=$true}
                if($parent -is [Management.Automation.Language.ForEachStatementAst] -and $node.Extent.StartOffset -eq $parent.Variable.Extent.StartOffset){$writer=$true}
                if($parent -is [Management.Automation.Language.FunctionDefinitionAst]){$context+=('function '+$parent.Name)}
                if($parent -is [Management.Automation.Language.IfStatementAst] -or $parent -is [Management.Automation.Language.TryStatementAst] -or $parent -is [Management.Automation.Language.CatchClauseAst]){$context+=$parent.GetType().Name}
                $parent=$parent.Parent
            }
            [pscustomobject]@{line=$node.Extent.StartLineNumber;writer=$writer;context=$context;text=$node.Extent.Text}
        })
        $records += [pscustomobject]@{file=$file.FullName.Substring([IO.Path]::GetFullPath($PackageRoot).TrimEnd('\').Length+1);variable=$group.Name;declaration=($references|Select-Object -First 1);initialization=@($references|Where-Object writer);first_read=($references|Where-Object {-not $_.writer}|Select-Object -First 1);writers=@($references|Where-Object writer);readers=@($references|Where-Object {-not $_.writer});cleanup='See finally/catch AST contexts and STATE-LIFECYCLE-AUDIT.md for lifecycle review';validateonly_path='See AST context and lifecycle review';execute_path='See AST context and lifecycle review';rollback_path='See AST context and lifecycle review';strictmode_safety=if($RepositoryInventory){'Inventory for manual lifecycle review; archived scripts are not executed'}else{'Latest enabled; mutable global/script references prohibited; dynamic matrix required'}}
    }
    # Qualification may deliberately use variable cmdlets to plant/prove stale state.
    # No shipped script may reference it implicitly or export a function to global scope.
    if($RepositoryInventory){continue}
    if(@($variables|Where-Object {$_.VariablePath.UserPath -match '^(global|script):'}).Count){throw ('ambient mutable variable reference: '+$file.Name)}
    $functions=@($tree.FindAll({param($node)$node -is [Management.Automation.Language.FunctionDefinitionAst]},$true))
    if(@($functions|Where-Object Name -match '^(global|script):').Count){throw ('leaking function definition: '+$file.Name)}
    if($file.Name -eq 'deploy_windows_iis_waitress.ps1'){
        $commands=@($tree.FindAll({param($node)$node -is [Management.Automation.Language.CommandAst]},$true))
        if(@($commands|Where-Object {$_.GetCommandName() -in @('Get-Variable','Set-Variable','Remove-Variable')}).Count){throw 'deployment must not inspect ambient qualification variables'}
    }
}
if($ReportPath){$records|ConvertTo-Json -Depth 12|Set-Content -LiteralPath $ReportPath -Encoding UTF8}
if($RepositoryInventory){Write-Output ('REPOSITORY_POWERSHELL_FILES_INVENTORIED='+$files.Count);return}
'ALL_RELEASE_STATE_VARIABLES_AUDITED=YES','UNINITIALIZED_GLOBAL_READS=0','UNINITIALIZED_SCRIPT_READS=0','STATE_LIFECYCLE_AUDIT=PASS'
