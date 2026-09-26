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

function Test-SchemaObject {
  param(
    [string]$Name,
    [object]$Document,
    [bool]$ExpectedValid
  )

  $actualValid = $false
  try {
    $actualValid = ($Document | ConvertTo-Json -Depth 100) |
      Test-Json -Schema $schemaText -ErrorAction Stop
  } catch {
    $actualValid = $false
  }

  if ($actualValid -ne $ExpectedValid) {
    $failures.Add("schema expectation failed: $Name expected=$ExpectedValid actual=$actualValid")
  }

  [pscustomobject]@{
    Check = 'schema'
    File = $Name
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

function Test-PackageArtifact {
  param(
    [string]$RelativePath,
    [string]$ExpectedSha256,
    [long]$ExpectedSize
  )

  $artifactPath = Join-Path $packageRoot $RelativePath
  $artifact = Get-Item -LiteralPath $artifactPath
  $actualHash = (Get-FileHash -LiteralPath $artifactPath -Algorithm SHA256).Hash.ToLowerInvariant()
  $passed = ($actualHash -eq $ExpectedSha256 -and $artifact.Length -eq $ExpectedSize)
  if (-not $passed) {
    $failures.Add("artifact metadata failed: $RelativePath")
  }

  [pscustomobject]@{
    Check = 'draft-artifact'
    File = $RelativePath
    Expected = "$ExpectedSha256 / $ExpectedSize bytes"
    Actual = "$actualHash / $($artifact.Length) bytes"
    Passed = $passed
  }
}

function Test-Utf8File {
  param([string]$RelativePath)

  $path = Join-Path $packageRoot $RelativePath
  $passed = $true
  try {
    $strictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
    $null = $strictUtf8.GetString([System.IO.File]::ReadAllBytes($path))
  } catch {
    $passed = $false
    $failures.Add("UTF-8 decoding failed: $RelativePath")
  }

  [pscustomobject]@{
    Check = 'draft-utf8'
    File = $RelativePath
    Expected = 'valid UTF-8'
    Actual = [string]$passed
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
$results.Add((Test-SchemaDocument 'contracts/draft-request.json' $true))
$results.Add((Test-SchemaDocument 'contracts/draft-success.json' $true))
$results.Add((Test-SchemaDocument 'contracts/draft-failure.json' $true))

$draftRequest = Get-Content -LiteralPath (Join-Path $packageRoot 'contracts/draft-request.json') -Raw |
  ConvertFrom-Json -Depth 100
$draftSuccess = Get-Content -LiteralPath (Join-Path $packageRoot 'contracts/draft-success.json') -Raw |
  ConvertFrom-Json -Depth 100
$draftFailure = Get-Content -LiteralPath (Join-Path $packageRoot 'contracts/draft-failure.json') -Raw |
  ConvertFrom-Json -Depth 100

$invalidDraftRequest = $draftRequest | ConvertTo-Json -Depth 100 | ConvertFrom-Json -Depth 100
$invalidDraftRequest.PSObject.Properties.Remove('idempotency_key')
$results.Add((Test-SchemaObject 'draft-request without idempotency_key' $invalidDraftRequest $false))

$invalidDraftSuccess = $draftSuccess | ConvertTo-Json -Depth 100 | ConvertFrom-Json -Depth 100
$invalidDraftSuccess.input.configuration.commands.build = 'make'
$results.Add((Test-SchemaObject 'draft-success with scalar build command' $invalidDraftSuccess $false))

$invalidDraftFailure = $draftFailure | ConvertTo-Json -Depth 100 | ConvertFrom-Json -Depth 100
$invalidDraftFailure.error.code = 'COMMAND_NOT_FOUND'
$results.Add((Test-SchemaObject 'draft-failure with private error code' $invalidDraftFailure $false))

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

$results.Add((Test-PackageArtifact 'draft-baseline/Dockerfile.reference' $draftSuccess.output.dockerfile.sha256 $draftSuccess.output.dockerfile.size_bytes))
$results.Add((Test-PackageArtifact 'draft-baseline/artifacts/build-success.log' $draftSuccess.output.build_log.sha256 $draftSuccess.output.build_log.size_bytes))
$results.Add((Test-PackageArtifact 'draft-baseline/artifacts/run-result.log' $draftSuccess.output.run_log.sha256 $draftSuccess.output.run_log.size_bytes))
$results.Add((Test-PackageArtifact 'draft-baseline/Dockerfile.broken' $draftFailure.output.dockerfile.sha256 $draftFailure.output.dockerfile.size_bytes))
$results.Add((Test-PackageArtifact 'draft-baseline/artifacts/build-failed.log' $draftFailure.output.build_log.sha256 $draftFailure.output.build_log.size_bytes))
$results.Add((Test-Utf8File 'draft-baseline/artifacts/build-success.log'))
$results.Add((Test-Utf8File 'draft-baseline/artifacts/run-result.log'))
$results.Add((Test-Utf8File 'draft-baseline/artifacts/build-failed.log'))

$requestInput = $draftRequest.input | ConvertTo-Json -Depth 100 -Compress
$successInput = $draftSuccess.input | ConvertTo-Json -Depth 100 -Compress
$failureInput = $draftFailure.input | ConvertTo-Json -Depth 100 -Compress
$draftInputMatches = ($requestInput -eq $successInput -and $requestInput -eq $failureInput)
if (-not $draftInputMatches) {
  $failures.Add('DRAFT request, success, and failure input echoes differ')
}
$results.Add([pscustomobject]@{
  Check = 'draft-input-consistency'
  File = 'draft-request.json / draft-success.json / draft-failure.json'
  Expected = 'identical input objects'
  Actual = [string]$draftInputMatches
  Passed = $draftInputMatches
})

foreach ($draftResult in @($draftSuccess, $draftFailure)) {
  $artifactNames = if ($draftResult.status -eq 'SUCCEEDED') {
    @('dockerfile', 'build_log', 'run_log')
  } else {
    @('dockerfile', 'build_log')
  }
  $repositoryCommit = $draftResult.input.repository.commit
  $configurationId = $draftResult.input.configuration.configuration_id
  $metadataMatches = $true
  foreach ($artifactName in $artifactNames) {
    $metadata = $draftResult.output.$artifactName
    if (
      $metadata.producer_job_id -ne $draftResult.job_id -or
      $metadata.repository_commit -ne $repositoryCommit -or
      $metadata.configuration_id -ne $configurationId
    ) {
      $metadataMatches = $false
    }
  }
  if (-not $metadataMatches) {
    $failures.Add("DRAFT $($draftResult.status) artifact provenance is inconsistent")
  }
  $resultFile = if ($draftResult.status -eq 'SUCCEEDED') {
    'contracts/draft-success.json'
  } else {
    'contracts/draft-failure.json'
  }
  $results.Add([pscustomobject]@{
    Check = 'draft-artifact-provenance'
    File = $resultFile
    Expected = 'matching job, commit, and configuration'
    Actual = [string]$metadataMatches
    Passed = $metadataMatches
  })
}

$expectedPullReference = "$($draftSuccess.output.container_image.name)@$($draftSuccess.output.container_image.digest)"
$imageDigestPinned = ($draftSuccess.output.container_image.pull_reference -eq $expectedPullReference)
if (-not $imageDigestPinned) {
  $failures.Add('DRAFT image pull reference is not pinned to its declared digest')
}
$results.Add([pscustomobject]@{
  Check = 'draft-image-digest'
  File = 'contracts/draft-success.json'
  Expected = 'pull_reference equals name@digest'
  Actual = [string]$imageDigestPinned
  Passed = $imageDigestPinned
})

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
