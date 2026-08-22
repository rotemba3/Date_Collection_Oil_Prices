# run_scrape_and_push.ps1
#
# Automates the local half of the pipeline:
#   1. Launches Chrome with remote debugging on a dedicated profile
#   2. Runs main.py (the Selenium Twitter scraper) against it
#   3. Commits and pushes whatever new tweet data was written
#
# ONE-TIME SETUP before this can run unattended:
#   Run this script once by hand, and when Chrome opens, log into your
#   X account in that window. Because it reuses the same --user-data-dir
#   every time, that login persists -- future runs (including scheduled
#   ones) will already be logged in, no manual step needed.
#
# EDIT THESE THREE PATHS to match your machine if they're different:

$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$ProfileDir = "C:\Users\97254\chrome-selenium-profile"
$RepoRoot   = "C:\Users\97254\Desktop\twitter-scraper-author-data-main\Date_Collection_Oil_Prices"

# --- shouldn't need to touch anything below this line ---

$DebugPort  = 9222
$MainScript = Join-Path $RepoRoot "Data_Collection_Oil\app-back\OilDatafiles\Scraper\main.py"
$LogFile    = Join-Path $RepoRoot "scrape_run.log"

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

Log "===== Starting scrape run ====="

Log "Launching Chrome with remote debugging on port $DebugPort..."
$chromeArgs = @(
    "--remote-debugging-port=$DebugPort",
    "--user-data-dir=$ProfileDir"
)
$chromeProc = Start-Process -FilePath $ChromePath -ArgumentList $chromeArgs -PassThru

# Give Chrome a few seconds to fully start before Selenium tries to attach.
Start-Sleep -Seconds 8

Log "Running main.py..."
Push-Location $RepoRoot
$scraperFailed = $false
try {
    python $MainScript
    if ($LASTEXITCODE -ne 0) {
        $scraperFailed = $true
        Log "main.py exited with code $LASTEXITCODE"
    }
} catch {
    $scraperFailed = $true
    Log "main.py threw an error: $_"
} finally {
    Pop-Location
}

Log "Closing Chrome..."
Stop-Process -Id $chromeProc.Id -Force -ErrorAction SilentlyContinue

if ($scraperFailed) {
    Log "Scraper reported a failure -- skipping commit/push so nothing broken gets pushed."
    Log "===== Run finished (with errors) ====="
    exit 1
}

Log "Committing and pushing results..."
Set-Location $RepoRoot
git add -A
$commitMsg = "automated scrape run $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
git commit -m $commitMsg | Out-Null

if ($LASTEXITCODE -eq 0) {
    git push
    Log "Pushed fresh tweet data."
} else {
    Log "Nothing new to commit (no tweet changes since last run)."
}

Log "===== Run finished ====="