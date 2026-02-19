@echo off
echo ========================================
echo      Uploading Images to Olam HaYeled
echo ========================================
echo.

:: Check if git is installed
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Git is not installed
    echo Please install Git first from: https://git-scm.com
    pause
    exit /b 1
)

echo Step 1: Blurring faces in new images...
python blur_new_images.py
if %errorlevel% neq 0 (
    echo ERROR: Failed to blur images
    echo Make sure Python and OpenCV are installed
    pause
    exit /b 1
)

echo.
echo Step 2: Adding images to Git...
git add .
if %errorlevel% neq 0 (
    echo ERROR: Failed to add files
    pause
    exit /b 1
)

echo.
echo Step 3: Saving changes...
set /p commitmsg="Enter a description for the changes (e.g., added new images): "
if "%commitmsg%"=="" set commitmsg=Added new images

git commit -m "%commitmsg%"
if %errorlevel% neq 0 (
    echo ERROR: Failed to commit changes
    pause
    exit /b 1
)

echo.
echo Step 4: Uploading to the internet...
git push
if %errorlevel% neq 0 (
    echo ERROR: Failed to upload
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS! Images have been uploaded
echo ========================================
echo Website URL: https://olamhayeled.netlify.app
echo.
echo Note: It may take a few minutes for the site to update
pause