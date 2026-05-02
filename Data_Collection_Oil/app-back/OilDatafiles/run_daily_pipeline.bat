@echo off

echo ==============================
echo Starting daily data pipeline
echo ==============================

cd /d "C:\Users\97254\Desktop\twitter-scraper-author-data-main\Date_Collection_Oil_Prices\Data_Collection_Oil\app-back\OilDatafiles"

echo.
echo ===== STEP 1: Start Chrome (for Twitter login) =====
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\chrome-selenium-profile"

echo Waiting 20 seconds for Chrome...
timeout /t 20 /nobreak

echo.
echo ===== STEP 2: Scraping Twitter =====
python "Scraper\main.py"

if errorlevel 1 (
    echo ERROR: Scraper failed
    pause
    exit /b 1
)

echo.
echo ===== STEP 3: Combine data =====
python "combine_data.py"

if errorlevel 1 (
    echo ERROR: combine_data failed
    pause
    exit /b 1
)

echo.
echo ===== STEP 4: Upload to Mongo =====
python "sendtomongo.py"

if errorlevel 1 (
    echo ERROR: sendtomongo failed
    pause
    exit /b 1
)

echo.
echo ===== STEP 5: Train + Predict tomorrow =====
python "OilDatafiles\Scraper\predict_tomorrow.py"

if errorlevel 1 (
    echo ERROR: prediction failed
    pause
    exit /b 1
)

echo.
echo ==============================
echo PIPELINE FINISHED SUCCESSFULLY
echo ==============================

pause