param(
  [switch]$SkipRemote
)

$ErrorActionPreference = 'Stop'
$packageRoot = Split-Path -Parent $PSScriptRoot
$schemaPath = Join-Path $packageRoot 'contracts/schemas/task.schema.json'
$exampleRoot = Join-Path $packageRoot 'contracts/examples/repair'
$artifactRoot = Join-Path $packageRoot 'contracts/artifacts/a06-b06'
$schemaText = Get-Content -LiteralPath $schemaPath -Raw
$failures = [System.Collections.Generic.List[string]]::new()

function Test-SchemaDocument {
  param(
    [string]$RelativePath,
    [bool]$ExpectedValid
  )

  $documentPath = Join-Path $packageRoot $RelativePath
  $actualValid = $false
  try {
    $actualValid = (Get-Content -LiteralPath $documentPath -Raw) |
      Test-Json -Schema $schemaText -ErrorAction Stop
  } catch {
    $actualValid = $false
  }

  if ($actualValid -ne $ExpectedValid) {
    $failures.Add("schema expectation failed: $RelativePath expected=$ExpectedValid actual=$actualValid")
  }

  [pscustomobject]@{
    Check = 'schema'
    File = $RelativePath
    Expected = $ExpectedValid
    Actual = $actualValid
    Passed = ($actualValid -eq $ExpectedValid)
  }
}

function Get-RepairSemanticCode {
  param([object]$Request)

  $inputObject = $Request.input
  if ($inputObject.finding.type -ne 'MISSING') {
    return 'REPAIR_7001'
  }

  $requestCommit = $inputObject.repository.commit
  if (
    $requestCommit -ne $inputObject.error_report.artifact.repository_commit -or
    $requestCommit -ne $inputObject.finding.commit
  ) {
    return 'REPAIR_7002'
  }

  $requestConfiguration = $inputObject.configuration.configuration_id
  if (
    $requestConfiguration -ne $inputObject.error_report.artifact.configuration_id -or
    $requestConfiguration -ne $inputObject.finding.configuration_id
  ) {
    return 'REPAIR_7003'
  }

  if ($inputObject.error_report.artifact.uri -ne $inputObject.error_report.read_method.url) {
    return 'REPAIR_7004'
  }

  if (
    [System.IO.Path]::IsPathRooted($inputObject.makefile_path) -or
    $inputObject.makefile_path -match '(^|[\\/])\.\.([\\/]|$)'
  ) {
    return 'REQUEST_1001'
  }

  return 'OK'
}

function Test-SemanticCase {
  param(
    [string]$RequestFile,
    [string]$ExpectedCode
  )

  $requestPath = Join-Path $exampleRoot $RequestFile
  $requestObject = Get-Content -LiteralPath $requestPath -Raw | ConvertFrom-Json -Depth 100
  $actualCode = Get-RepairSemanticCode -Request $requestObject
  if ($actualCode -ne $ExpectedCode) {
    $failures.Add("semantic expectation failed: $RequestFile expected=$ExpectedCode actual=$actualCode")
  }

  [pscustomobject]@{
    Check = 'semantic'
    File = $RequestFile
    Expected = $ExpectedCode
    Actual = $actualCode
    Passed = ($actualCode -eq $ExpectedCode)
  }
}

function Test-ResponseCode {
  param(
    [string]$ResponseFile,
    [string]$ExpectedCode
  )

  $responsePath = Join-Path $exampleRoot $ResponseFile
  $responseObject = Get-Content -LiteralPath $responsePath -Raw | ConvertFrom-Json -Depth 100
  $actualCode = $responseObject.error.code
  if ($actualCode -ne $ExpectedCode) {
    $failures.Add("response code failed: $ResponseFile expected=$ExpectedCode actual=$actualCode")
  }

  [pscustomobject]@{
    Check = 'response-code'
    File = $ResponseFile
    Expected = $ExpectedCode
    Actual = $actualCode
    Passed = ($actualCode -eq $ExpectedCode)
  }
}

function Test-LocalArtifact {
  param(
    [string]$FileName,
    [string]$ExpectedSha256,
    [long]$ExpectedSize
  )

  $artifactPath = Join-Path $artifactRoot $FileName
  $artifact = Get-Item -LiteralPath $artifactPath
  $actualHash = (Get-FileHash -LiteralPath $artifactPath -Algorithm SHA256).Hash.ToLowerInvariant()
  $passed = ($actualHash -eq $ExpectedSha256 -and $artifact.Length -eq $ExpectedSize)
  if (-not $passed) {
    $failures.Add("artifact metadata failed: $FileName")
  }

  [pscustomobject]@{
    Check = 'artifact'
    File = $FileName
    Expected = "$ExpectedSha256 / $ExpectedSize bytes"
    Actual = "$actualHash / $($artifact.Length) bytes"
    Passed = $passed
  }
}

$results = [System.Collections.Generic.List[object]]::new()

$results.Add((Test-SchemaDocument 'contracts/examples/repair/repair-request.json' $true))
$results.Add((Test-SchemaDocument 'contracts/examples/repair/repair-result-success.json' $true))
$results.Add((Test-SchemaDocument 'contracts/examples/repair/repair-response-reject-redundant.json' $true))
$results.Add((Test-SchemaDocument 'contracts/examples/repair/repair-response-reject-commit-mismatch.json' $true))
$results.Add((Test-SchemaDocument 'contracts/examples/repair/repair-response-reject-configuration-mismatch.json' $true))
$results.Add((Test-SchemaDocument 'contracts/artifacts/a06-b06/repair-report.json' $true))
$results.Add((Test-SchemaDocument 'contracts/examples/repair/repair-request-reject-redundant.json' $false))
$results.Add((Test-SchemaDocument 'contracts/examples/repair/repair-request-reject-commit-mismatch.json' $true))
$results.Add((Test-SchemaDocument 'contracts/examples/repair/repair-request-reject-configuration-mismatch.json' $true))

$results.Add((Test-SemanticCase 'repair-request.json' 'OK'))
$results.Add((Test-SemanticCase 'repair-request-reject-redundant.json' 'REPAIR_7001'))
$results.Add((Test-SemanticCase 'repair-request-reject-commit-mismatch.json' 'REPAIR_7002'))
$results.Add((Test-SemanticCase 'repair-request-reject-configuration-mismatch.json' 'REPAIR_7003'))

$results.Add((Test-ResponseCode 'repair-response-reject-redundant.json' 'REPAIR_7001'))
$results.Add((Test-ResponseCode 'repair-response-reject-commit-mismatch.json' 'REPAIR_7002'))
$results.Add((Test-ResponseCode 'repair-response-reject-configuration-mismatch.json' 'REPAIR_7003'))

$successResult = Get-Content -LiteralPath (Join-Path $exampleRoot 'repair-result-success.json') -Raw |
  ConvertFrom-Json -Depth 100
$results.Add((Test-LocalArtifact 'fix-main-o-config-h.patch' $successResult.output.patch.sha256 $successResult.output.patch.size_bytes))
$results.Add((Test-LocalArtifact 'repair-report.json' $successResult.output.repair_report.sha256 $successResult.output.repair_report.size_bytes))

$repairReport = Get-Content -LiteralPath (Join-Path $artifactRoot 'repair-report.json') -Raw |
  ConvertFrom-Json -Depth 100
$results.Add((Test-LocalArtifact 'repair-verification.txt' $repairReport.verification.log.sha256 $repairReport.verification.log.size_bytes))

$resultAndReportMatch = (
  $successResult.output.provenance -eq $repairReport.provenance -and
  $successResult.output.verification.recheck.status -eq $repairReport.verification.recheck.status -and
  $successResult.output.repair_report.repository_commit -eq $repairReport.repository_commit -and
  $successResult.output.repair_report.configuration_id -eq $repairReport.configuration_id
)
if (-not $resultAndReportMatch) {
  $failures.Add('success result and repair report disagree on provenance, recheck, commit, or configuration')
}
$results.Add([pscustomobject]@{
  Check = 'result-report-consistency'
  File = 'repair-result-success.json / repair-report.json'
  Expected = 'matching provenance, recheck, commit, and configuration'
  Actual = [string]$resultAndReportMatch
  Passed = $resultAndReportMatch
})

if (-not $SkipRemote) {
  $requestObject = Get-Content -LiteralPath (Join-Path $exampleRoot 'repair-request.json') -Raw |
    ConvertFrom-Json -Depth 100
  $temporaryFile = New-TemporaryFile
  try {
    $response = Invoke-WebRequest -Uri $requestObject.input.error_report.read_method.url -OutFile $temporaryFile.FullName -PassThru
    $actualHash = (Get-FileHash -LiteralPath $temporaryFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $actualSize = (Get-Item -LiteralPath $temporaryFile.FullName).Length
    $expectedHash = $requestObject.input.error_report.artifact.sha256
    $expectedSize = $requestObject.input.error_report.artifact.size_bytes
    $actualMediaType = [string]$response.Headers.'Content-Type'
    $remotePassed = (
      $response.StatusCode -eq 200 -and
      $actualMediaType -like 'text/plain*' -and
      $actualHash -eq $expectedHash -and
      $actualSize -eq $expectedSize
    )
    if (-not $remotePassed) {
      $failures.Add('remote ERROR_REPORT metadata or HTTP contract failed')
    }
    $results.Add([pscustomobject]@{
      Check = 'remote-report'
      File = $requestObject.input.error_report.read_method.url
      Expected = "HTTP 200 / text/plain / $expectedHash / $expectedSize bytes"
      Actual = "HTTP $($response.StatusCode) / $actualMediaType / $actualHash / $actualSize bytes"
      Passed = $remotePassed
    })
  } finally {
    Remove-Item -LiteralPath $temporaryFile.FullName -Force
  }
}

$results | Format-Table -Wrap -AutoSize

if ($failures.Count -gt 0) {
  Write-Error ($failures -join [Environment]::NewLine)
  exit 1
}

Write-Host "All $($results.Count) contract checks passed."
