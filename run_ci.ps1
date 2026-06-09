# AI Test Generator Local CI Trigger
Write-Host "--- Starting Local CI Validation ---" -ForegroundColor Cyan

# 1. Linting
Write-Host "[*] Running Syntax Check..." -ForegroundColor Yellow
Get-ChildItem -Filter *.py -Recurse | ForEach-Object { 
    python -m py_compile $_.FullName 
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Syntax check failed on $($_.Name)!" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}
Write-Host "[+] Syntax check passed." -ForegroundColor Green

# 2. Run Evaluation Pipeline
Write-Host "[*] Running AI Evaluation Pipeline (RTM & Static Analysis)..." -ForegroundColor Yellow
python evaluate.py --data data/input/sample_brd.txt --output local_ci_report.md
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Evaluation pipeline failed!" -ForegroundColor Red
    # Log failure for feedback loop if possible
    exit $LASTEXITCODE
}

# 3. Execution Validation (Dry-Run / Syntax only for generated tests)
Write-Host "[*] Validating Generated Script Execution..." -ForegroundColor Yellow
$generated_script = "output/test_script.py"
if (Test-Path $generated_script) {
    # Check if we can run it (requires server/env, so we do a collection run or check)
    pytest --collect-only $generated_script
    if ($LASTEXITCODE -ne 0) {
         Write-Host "[!] Generated script is not valid pytest or has collection errors!" -ForegroundColor Red
         # Future: Call feedback_handler.py here to log the failure
         exit $LASTEXITCODE
    }
    Write-Host "[+] Generated script validated (collection successful)." -ForegroundColor Green
}

Write-Host "--- CI Validation Successful ---" -ForegroundColor Green
Write-Host "View report at: local_ci_report.md"
