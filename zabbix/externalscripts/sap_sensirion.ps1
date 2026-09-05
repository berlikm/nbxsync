# SAP ME (Windows) collector — sapcontrol.exe / sapstartsrv, not Promonitor.
# Same JSON keys as zabbix/externalscripts/sap_sensirion.py (openSUSE HANA).
# Stdlib PowerShell 5.1. No passwords. No Groovy on the Zabbix proxy.

param(
    [Parameter(Position = 0)][string]$Metric = 'json',
    [Parameter(Position = 1)][string]$Instance = '',
    [Parameter(Position = 2)][string]$Sid = '',
    [Parameter(Position = 3)][string]$Peer = ''
)

$ErrorActionPreference = 'Stop'
$NotSupported = 'ZBX_NOTSUPPORTED'
$Candidates = @(
    'C:\Program Files\SAP\hostctrl\exe\sapcontrol.exe',
    'C:\usr\sap\hostctrl\exe\sapcontrol.exe',
    'C:\Program Files (x86)\SAP\hostctrl\exe\sapcontrol.exe'
)
$HostCtrlCandidates = @(
    'C:\Program Files\SAP\hostctrl\exe\saphostctrl.exe',
    'C:\usr\sap\hostctrl\exe\saphostctrl.exe',
    'C:\Program Files (x86)\SAP\hostctrl\exe\saphostctrl.exe'
)

function Write-NotSupported([string]$Reason) {
    Write-Output ("{0}: {1}" -f $NotSupported, $Reason)
    exit 0
}

function Find-Exe([string[]]$Paths, [string]$Name) {
    foreach ($path in $Paths) {
        if (Test-Path -LiteralPath $path) { return $path }
    }
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Normalize-Status([string]$Value) {
    $text = ([string]$Value).Trim().ToUpper().Replace('SAPCONTROL-', '')
    if ($text -eq 'GREY') { return 'GRAY' }
    if (@('GREEN', 'YELLOW', 'GRAY', 'RED') -contains $text) { return $text }
    return 'GRAY'
}

function Parse-KvBody([string]$Text) {
    $rows = @()
    $header = $null
    foreach ($raw in ($Text -split "`r?`n")) {
        $line = $raw.Trim()
        if (-not $line) { continue }
        if ($line -match '^\s*\d+\s*:\s*(.+)$') {
            $row = @{}
            [regex]::Matches($Matches[1], '(\w+)\s*:\s*(.*?)(?=,\s*\w+\s*:|$)') | ForEach-Object {
                $row[$_.Groups[1].Value.Trim().ToLower()] = $_.Groups[2].Value.Trim()
            }
            if ($row.ContainsKey('name')) { $rows += $row }
            continue
        }
        if ($line.Contains(',') -and -not $header -and $line.ToLower().Contains('name')) {
            $header = @($line.Split(',') | ForEach-Object { $_.Trim().ToLower() })
            continue
        }
        if ($header -and $line.Contains(',')) {
            $parts = @($line.Split(',') | ForEach-Object { $_.Trim() })
            $row = @{}
            for ($i = 0; $i -lt $header.Count -and $i -lt $parts.Count; $i++) {
                $row[$header[$i]] = $parts[$i]
            }
            if ($row.ContainsKey('name') -and $row['name'] -ne 'name') { $rows += $row }
        }
    }
    return $rows
}

function Get-Kind($Processes) {
    $names = @($Processes | ForEach-Object { ([string]$_.name).ToLower() })
    $hana = $names | Where-Object { $_ -like 'hdb*' }
    $abap = $names | Where-Object { $_ -match 'disp\+work|msg_server|enserver|gwrd|icman' }
    $java = $names | Where-Object { $_ -like 'jstart*' -or $_ -like 'jcontrol*' -or $_ -like 'jc0*' }
    $hits = @()
    if ($hana) { $hits += 'hana' }
    if ($abap) { $hits += 'abap' }
    if ($java) { $hits += 'java' }
    if ($hits.Count -eq 1) { return $hits[0] }
    if ($hits.Count -gt 1) { return 'mixed' }
    return 'unknown'
}

function Test-InstanceUp($Processes) {
    if (-not $Processes -or $Processes.Count -eq 0) { return 0 }
    $kind = Get-Kind $Processes
    $critical = @()
    foreach ($proc in $Processes) {
        $n = ([string]$proc.name).ToLower()
        $isCrit = $false
        if ($kind -in @('hana', 'mixed', 'unknown') -and ($n -like 'hdbnameserver*' -or $n -like 'hdbindexserver*' -or $n -like 'hdbdaemon*')) { $isCrit = $true }
        if ($kind -in @('abap', 'mixed', 'unknown') -and ($n -like 'disp+work*' -or $n -like 'msg_server*')) { $isCrit = $true }
        if ($kind -in @('java', 'mixed', 'unknown') -and ($n -like 'jstart*' -or $n -like 'jcontrol*')) { $isCrit = $true }
        if ($isCrit) { $critical += $proc }
    }
    $watch = $(if ($critical.Count) { $critical } else { $Processes })
    foreach ($proc in $watch) {
        $st = Normalize-Status $proc.dispstatus
        if ($st -in @('GRAY', 'RED')) { return 0 }
    }
    foreach ($proc in $watch) {
        if ((Normalize-Status $proc.dispstatus) -in @('GREEN', 'YELLOW')) { return 1 }
    }
    return 0
}

function Test-RfcUp($Processes, [int]$InstanceUp) {
    $gw = @($Processes | Where-Object { ([string]$_.name).ToLower().StartsWith('gwrd') })
    if ($gw.Count) {
        foreach ($proc in $gw) {
            if ((Normalize-Status $proc.dispstatus) -notin @('GREEN', 'YELLOW')) { return 0 }
        }
        return 1
    }
    return $InstanceUp
}

function Count-Alerts($Alerts, [string[]]$Keys) {
    $total = 0
    foreach ($alert in $Alerts) {
        $blob = ('{0} {1} {2}' -f $alert.name, $alert.description, $alert.value).ToLower()
        $hit = $false
        foreach ($key in $Keys) {
            if ($blob.Contains($key)) { $hit = $true; break }
        }
        if (-not $hit) { continue }
        if ([string]$alert.value -match '^\d+$') { $total += [int]$alert.value } else { $total += 1 }
    }
    return $total
}

function New-EmptyMetrics {
    return [ordered]@{
        promonitor = 0
        instance_status = 0
        abap_errors = 0
        idoc_errors = 0
        job_alerts = 0
        locks = 0
        qrfc_in = 0
        qrfc_out = 0
        rfc_status = 0
        spool_errors = 0
        syslog_alerts = 0
        trfc_errors = 0
        update_requests = 0
        kind = 'unknown'
        source = 'none'
    }
}

function Metrics-FromSnapshot($Processes, $Alerts, [string]$Source) {
    $up = Test-InstanceUp $Processes
    $data = New-EmptyMetrics
    $data.promonitor = 1
    $data.instance_status = $up
    $data.rfc_status = Test-RfcUp $Processes $up
    $data.kind = Get-Kind $Processes
    $data.source = $Source
    $map = @{
        abap_errors = @('shortdump', 'short dump', 'runtime error', 'abap dump', 'r3abap')
        idoc_errors = @('idoc')
        job_alerts = @('background job', 'job alert', 'btc job', 'job cancelled')
        locks = @('enqueue', 'lock entry', 'sm12', 'r3enqueue')
        qrfc_in = @('qrfc in', 'inbound queue', 'inbound qrfc')
        qrfc_out = @('qrfc out', 'outbound queue', 'outbound qrfc')
        spool_errors = @('spool', 'temse')
        syslog_alerts = @('syslog', 'r3syslog', 'system log')
        trfc_errors = @('trfc', 'transactional rfc', 'sm58')
        update_requests = @('update request', 'update record', 'sm13', 'v1 update', 'v2 update')
    }
    foreach ($field in $map.Keys) {
        $data[$field] = Count-Alerts $Alerts $map[$field]
    }
    return $data
}

function Invoke-Sapcontrol([string]$Nr, [string]$Function, [string]$HostName) {
    $bin = Find-Exe $Candidates 'sapcontrol.exe'
    if (-not $bin) { return $null }
    $args = @('-nr', $Nr, '-function', $Function)
    if ($HostName -and $HostName -notin @('127.0.0.1', 'localhost', '')) {
        $args += @('-host', $HostName)
    }
    try {
        $out = & $bin @args 2>$null | Out-String
    } catch {
        return $null
    }
    if ($out -match '(?m)^\s*FAIL\b') { return $null }
    if ($out -match '(?m)^\s*OK\b' -or ($out.ToLower().Contains('name') -and $out.ToLower().Contains('dispstatus'))) {
        return $out
    }
    return $null
}

function Invoke-Soap([string]$HostName, [int]$Port, [string]$Function) {
    $body = @"
<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:s="urn:SAPControl">
  <SOAP-ENV:Body><s:$Function/></SOAP-ENV:Body>
</SOAP-ENV:Envelope>
"@
    try {
        $resp = Invoke-WebRequest -Uri ("http://{0}:{1}/" -f $HostName, $Port) -Method POST -ContentType 'text/xml; charset=utf-8' -Body $body -UseBasicParsing -TimeoutSec 5
        return [string]$resp.Content
    } catch {
        return $null
    }
}

function Parse-SoapItems([string]$XmlText) {
    $rows = @()
    if (-not $XmlText) { return $rows }
    try {
        [xml]$doc = $XmlText
    } catch {
        return $rows
    }
    $nodes = $doc.SelectNodes('//*[local-name()="item"]')
    foreach ($node in $nodes) {
        $row = @{}
        foreach ($child in $node.ChildNodes) {
            $row[$child.LocalName.ToLower()] = [string]$child.InnerText
        }
        if ($row.ContainsKey('name') -or $row.ContainsKey('description')) { $rows += $row }
    }
    return $rows
}

function Get-Instances([string]$WantSid) {
    $bin = Find-Exe $HostCtrlCandidates 'saphostctrl.exe'
    if (-not $bin) { return @() }
    try {
        $out = & $bin -function ListInstances 2>$null | Out-String
    } catch {
        return @()
    }
    $rows = @()
    foreach ($m in [regex]::Matches($out, 'Inst Info\s*:\s*(\S+)\s*-\s*(\d{1,2})\s*-\s*(\S+)', 'IgnoreCase')) {
        $row = @{ sid = $m.Groups[1].Value.ToUpper(); nr = $m.Groups[2].Value.PadLeft(2, '0') }
        if ($WantSid -and $row.sid -ne $WantSid.ToUpper()) { continue }
        $rows += $row
    }
    return $rows
}

function Collect-Instance([string]$Nr, [string]$HostName) {
    $peer = $(if ($HostName) { $HostName } else { '127.0.0.1' })
    $text = Invoke-Sapcontrol $Nr 'GetProcessList' $HostName
    $alertsText = $null
    $source = 'sapcontrol'
    if ($null -ne $text) {
        $alertsText = Invoke-Sapcontrol $Nr 'GetAlerts' $HostName
    }
    $procs = @(Parse-KvBody ([string]$text) | Where-Object { $_.name -and $_.name -ne 'name' } | ForEach-Object {
        [pscustomobject]@{ name = $_.name; description = $_.description; dispstatus = (Normalize-Status $_.dispstatus) }
    })
    $alerts = @(Parse-KvBody ([string]$alertsText) | Where-Object { $_.name -and $_.name -ne 'name' })
    if (-not $procs.Count) {
        $port = 50013 + ([int]$Nr * 100)
        $xmlP = Invoke-Soap $peer $port 'GetProcessList'
        $xmlA = Invoke-Soap $peer $port 'GetAlerts'
        $procs = @(Parse-SoapItems $xmlP | ForEach-Object {
            [pscustomobject]@{ name = $_.name; description = $_.description; dispstatus = (Normalize-Status $_.dispstatus) }
        } | Where-Object { $_.name })
        $alerts = @(Parse-SoapItems $xmlA)
        $source = 'soap'
    }
    if (-not $procs.Count -and -not $alerts.Count) { return $null }
    return Metrics-FromSnapshot $procs $alerts $source
}

if ($Metric -eq '-h' -or $Metric -eq '--help') {
    Write-Error 'usage: sap_sensirion.ps1 <json|metric> [instance] [sid] [host]'
    exit 2
}

foreach ($name in @('Instance', 'Sid', 'Peer')) {
    $val = Get-Variable $name -ValueOnly
    if ($val -in @('-', '--', '{$SAP.INSTANCE}', '{$SAP.SID}', '{$SAP.CONTROL.HOST}')) {
        Set-Variable $name ''
    }
}
if ($Peer -eq 'localhost') { $Peer = '127.0.0.1' }
if ($Instance -and $Instance -notmatch '^\d{1,2}$') { Write-NotSupported 'bad instance' }
if ($Sid -and $Sid -notmatch '^[A-Za-z0-9]{0,3}$') { Write-NotSupported 'bad sid' }
if ($Peer -and $Peer -notmatch '^[A-Za-z0-9._-]+$') { Write-NotSupported 'bad host' }

$targets = @()
if ($Instance) {
    $targets += @{ nr = $Instance.PadLeft(2, '0') }
} else {
    $targets = @(Get-Instances $Sid)
    if (-not $targets.Count) {
        $targets = @(@{ nr = '00' }, @{ nr = '01' }, @{ nr = '02' })
    }
}

$merged = $null
foreach ($target in $targets) {
    $row = Collect-Instance $target.nr $Peer
    if (-not $row) { continue }
    if (-not $merged) {
        $merged = $row
        continue
    }
    $merged.instance_status = [int]($merged.instance_status -and $row.instance_status)
    $merged.rfc_status = [int]($merged.rfc_status -and $row.rfc_status)
    foreach ($field in @('abap_errors', 'idoc_errors', 'job_alerts', 'locks', 'qrfc_in', 'qrfc_out', 'spool_errors', 'syslog_alerts', 'trfc_errors', 'update_requests')) {
        $merged[$field] = [int]$merged[$field] + [int]$row[$field]
    }
    if ($merged.kind -ne $row.kind) { $merged.kind = 'mixed' }
}

if (-not $merged) { Write-NotSupported 'sapcontrol not available' }

$cli = @{
    'promonitor' = 'promonitor'
    'instance.status' = 'instance_status'
    'abap.errors' = 'abap_errors'
    'idoc.errors' = 'idoc_errors'
    'job.alerts' = 'job_alerts'
    'locks' = 'locks'
    'qrfc.in' = 'qrfc_in'
    'qrfc.out' = 'qrfc_out'
    'rfc.status' = 'rfc_status'
    'spool.errors' = 'spool_errors'
    'syslog.alerts' = 'syslog_alerts'
    'trfc.errors' = 'trfc_errors'
    'update.requests' = 'update_requests'
}

if ($Metric -eq 'json') {
    $payload = [ordered]@{}
    foreach ($key in @('promonitor', 'instance_status', 'abap_errors', 'idoc_errors', 'job_alerts', 'locks', 'qrfc_in', 'qrfc_out', 'rfc_status', 'spool_errors', 'syslog_alerts', 'trfc_errors', 'update_requests', 'kind', 'source')) {
        $payload[$key] = $merged[$key]
    }
    Write-Output ($payload | ConvertTo-Json -Compress)
    exit 0
}
if (-not $cli.ContainsKey($Metric)) { Write-NotSupported 'unknown metric' }
Write-Output ([int]$merged[$cli[$Metric]])
exit 0
