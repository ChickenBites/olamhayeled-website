@echo off
echo ========================================
echo        Uploading Images to Website
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

echo Step 1: Adding images to Git...
git add .
if %errorlevel% neq 0 (
    echo Error while adding files
    pause
    exit /b 1
)

echo.
echo Step 2: Saving changes...
set /p commitmsg="Enter a description for the changes (e.g., added new images): "
if "%commitmsg%"=="" set commitmsg=Added new images

git commit -m "%commitmsg%"
if %errorlevel% neq 0 (
    echo Error while committing changes
    pause
    exit /b 1
)

echo.
echo Step 3: Uploading to the internet...
git push
if %errorlevel% neq 0 (
    echo Error while uploading
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