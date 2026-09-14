#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$deploy=Join-Path $PackageRoot 'deploy_windows_iis_waitress.ps1'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($deploy,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors.Message -join '; ')}
# Load the exact shipped functions without executing the entry point.
$functions=@($ast.EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.FunctionDefinitionAst]})
foreach($function in $functions){. ([scriptblock]::Create($function.Extent.Text))}
$taskFunctions=@($functions|Where-Object Name -in @('TaskRuntime','Get-TaskLaunch','New-TaskLaunchXml','Get-ConfiguredTask'))
if($taskFunctions.Count -ne 4){throw 'launcher ownership function inventory changed; review required'}
$directAssertions=@($taskFunctions|Where-Object {$_.Extent.Text -match '(?i)waitress'})
if($directAssertions.Count){throw 'task ownership contains a direct backend assertion'}
$old='C:\local qualification\release-old'
$py=Join-Path $old 'runtime\python.exe'
$target='C:\local qualification\release-new'
$targetPy=Join-Path $target 'runtime\python.exe'
$launcher='C:\1-webapp\forwarder-runtime\phase1b_production_cutover_runtime.py'
$xml='<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"><RegistrationInfo><Description>'+ $old +'</Description></RegistrationInfo><Settings><Enabled>true</Enabled></Settings><Actions><Exec><Command>C:\Windows\System32\cmd.exe</Command><Arguments>/d /c set PYTHONPATH='+$old+' &amp;&amp; cd /d &quot;'+$old+'&quot; &amp;&amp; &quot;'+$py+'&quot; &quot;'+$launcher+'&quot; serve --log &quot;'+$old+'\old.log&quot; --port 5101 --repo &quot;'+$old+'&quot; --env &quot;C:\local qualification\production.env&quot; --host 127.0.0.1</Arguments><WorkingDirectory>'+$old+'</WorkingDirectory></Exec></Actions></Task>'
    [xml]$taskDoc=$xml; $taskArgs=[string]$taskDoc.Task.Actions.Exec.Arguments; $taskDoc.Task.Actions.Exec.Arguments='/d /c "'+$taskArgs.Substring(6).Replace('"','""')+'"'; $xml=$taskDoc.OuterXml
Need (SamePath (TaskRuntime $xml) $py) 'launcher runtime parse failed'
$next=New-TaskLaunchXml $xml $target
$parsed=Get-TaskLaunch $next
Need (SamePath $parsed.Runtime $targetPy) 'candidate launcher runtime parse failed'
Need ((SamePath $parsed.PythonPath $target) -and (SamePath $parsed.CdPath $target) -and (SamePath ([string]$parsed.Action.WorkingDirectory) $target)) 'target wrapper paths were not transformed'
Need ([string]$parsed.Action.Arguments -match '^/d /c "set PYTHONPATH=.*&& cd /d "".*""&& ') 'target wrapper shape changed'
Need ($parsed.Tokens -contains ($old+'\old.log')) 'external log option was rewritten'
Need ($parsed.Tokens -contains 'C:\local qualification\production.env') 'external env option was rewritten'
Need ($parsed.Tokens -contains $launcher) 'approved launcher was rewritten'
Need ($parsed.Document.Task.RegistrationInfo.Description -eq $old) 'task metadata was rewritten'
Need (SamePath (TaskRuntime $xml) $py) 'rollback XML changed'
Need (SamePath (Get-TaskLaunch $xml).PythonPath $old) 'rollback baseline wrapper did not reparse'
Need (-not (Get-TaskLaunch ($xml.Replace(' --log ""'+$old+'\old.log""',''))).Tokens.Contains('--log')) 'optional log absent did not parse'
$captured=$xml.Replace($old,'C:\1-webapp\forwarder-production\release-current')
Need (SamePath (TaskRuntime $captured) 'C:\1-webapp\forwarder-production\release-current\runtime\python.exe') 'captured Production wrapper did not parse'
Need (SamePath (TaskRuntime ($xml.Replace($old,$old.ToUpperInvariant().Replace('\','/')))) $py) 'case/slash runtime normalization failed'
function Refuses([scriptblock]$Code,[string]$Expected){
    $message='';try{& $Code|Out-Null}catch{$message=$_.Exception.Message}
    Need ($message -eq ('RELEASE_STOP: '+$Expected)) ('unexpected refusal: '+$message)
}
# Old direct actions must not satisfy the approved launcher contract.
$direct=$xml.Replace('""'+$launcher+'"" serve','-m waitress backend.wsgi:app')
Refuses {TaskRuntime $direct} 'approved runtime launcher required'
Refuses {TaskRuntime ($xml.Replace(' &amp;&amp; ""'+$py,' &amp;&amp; echo unexpected &amp;&amp; ""'+$py))} 'unsupported shell syntax in launcher arguments'
Refuses {TaskRuntime ($xml.Replace(' serve --log',' serve | more --log'))} 'unsupported shell syntax in launcher arguments'
Refuses {TaskRuntime ($xml.Replace(' serve --log',' serve &gt; file --log'))} 'unsupported shell syntax in launcher arguments'
Refuses {TaskRuntime ($xml.Replace('PYTHONPATH='+$old,'PYTHONPATH=C:\wrong'))} 'PYTHONPATH/--repo mismatch'
Refuses {TaskRuntime ($xml.Replace('cd /d ""'+$old,'cd /d ""C:\wrong'))} 'cd/--repo mismatch'
Refuses {TaskRuntime ($xml.Replace($py+'""',$old+'\wrong.exe""'))} 'runtime/--repo mismatch'
Refuses {TaskRuntime ($xml.Replace('--repo ""'+$old,'--repo ""C:\wrong'))} 'PYTHONPATH/--repo mismatch'
Refuses {TaskRuntime ($xml.Replace('<WorkingDirectory>'+$old,'<WorkingDirectory>C:\wrong'))} 'runtime/WorkingDirectory mismatch'
$observed=[pscustomobject]@{Xml=$next;Enabled=$true;State='Ready';Runtime=$targetPy;Command=('"'+$targetPy+'" -m waitress --listen=127.0.0.1:5101 backend.wsgi:app');Owners=@(31415,31415);Stops=0;HealthCalls=0}
function Get-NetTCPConnection {param([string]$State,[int]$LocalPort) foreach($owner in $observed.Owners){[pscustomobject]@{LocalAddress='127.0.0.1';OwningProcess=$owner}}}
function Get-CimInstance {param([string]$ClassName,[string]$Filter) Need ($Filter -eq 'ProcessId=31415') 'unexpected process query';[pscustomobject]@{ExecutablePath=$observed.Runtime;CommandLine=$observed.Command}}
function Get-ScheduledTask {param([string]$TaskName) [xml]$doc=$observed.Xml;[pscustomobject]@{State=$observed.State;Settings=[pscustomobject]@{Enabled=$observed.Enabled};Actions=@([pscustomobject]@{Execute=[string]$doc.Task.Actions.Exec.Command;Arguments=[string]$doc.Task.Actions.Exec.Arguments;WorkingDirectory=[string]$doc.Task.Actions.Exec.WorkingDirectory})}}
function Export-ScheduledTask {param([string]$TaskName) $observed.Xml}
Wait-Listener $targetPy 1
$observed.Command='"'+$targetPy+'" unrelated.py'
Refuses {Wait-Listener $targetPy 1} 'orphan/mismatched listener: process is not the configured Waitress backend'
$observed.Command='"'+$targetPy+'" -m waitress --listen=127.0.0.1:5101 backend.wsgi:app'
$observed.Xml=$xml
Refuses {Wait-Listener $targetPy 1} 'listener/task runtime mismatch'
$observed.Xml=$next;$observed.Enabled=$false
Refuses {Wait-Listener $targetPy 1} 'production scheduled task must be enabled'
$observed.Enabled=$true;$observed.Owners=@(31415,31416)
Refuses {Wait-Listener $targetPy 1} 'multiple listener owners'
$observed.Owners=@(31415)
# Rollback must refuse unrelated code even when its executable is allowlisted.
$FixtureStatePath='';$Timeouts=@{PORT_RELEASE=1;ROLLBACK_RECOVERY=1}
$before=[pscustomobject]@{task_xml=$xml;listener_runtime=$py;iis_path=(Join-Path $old 'dist');enabled=$true}
function Disable-ScheduledTask {param([string]$TaskName) $observed.Enabled=$false}
function Stop-Process {param([int]$Id) Need ($Id -eq 31415) 'unexpected process stop';$observed.Stops++;$observed.Owners=@()}
function Set-IisPhysicalPath {param([string]$Path) Need ($Path -eq $before.iis_path) 'wrong restored IIS path'}
function Register-ScheduledTask {param([string]$TaskName,[string]$Xml) $observed.Xml=$Xml}
function Enable-ScheduledTask {param([string]$TaskName) $observed.Enabled=$true}
function Start-ScheduledTask {param([string]$TaskName) $observed.Runtime=$py;$observed.Command='"'+$py+'" -m waitress --listen=127.0.0.1:5101 backend.wsgi:app';$observed.Owners=@(31415)}
function Assert-Health {param([string]$Uri,[int]$Seconds) $observed.HealthCalls++}
$observed.Command='"'+$targetPy+'" unrelated.py'
Refuses {Rollback $null $before $targetPy} 'orphan/mismatched listener: process is not the configured Waitress backend'
Need ($observed.Stops -eq 0) 'rollback stopped an unrelated process'
$observed.Command='"'+$targetPy+'" -m waitress --listen=127.0.0.1:5101 backend.wsgi:app'
Rollback $null $before $targetPy|Out-Null
Need ($observed.Stops -eq 1 -and $observed.Xml -ceq $xml -and $observed.Enabled -and $observed.HealthCalls -eq 1) 'launcher rollback recovery failed'
Wait-Listener $py 1
'TASK_TRANSFORMATION_PRESERVES_LAUNCHER=PASS','EXECUTE_ROLLBACK_LISTENER_COMMAND_GATES=PASS','LAUNCHER_CHAIN_MODEL=PASS','DIRECT_WAITRESS_TASK_ASSUMPTIONS=0'
