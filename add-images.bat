@echo off
echo ========================================
echo    העלאת תמונות לאתר עולם הילד
echo ========================================
echo.

:: Check if git is installed
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo שגיאה: לא התקנת את Git
    echo אנא התקן את Git קודם מהאתר: https://git-scm.com
    pause
    exit /b 1
)

echo שלב 1: מוסיף תמונות ל-Git...
git add .
if %errorlevel% neq 0 (
    echo שגיאה בהוספת קבצים
    pause
    exit /b 1
)

echo.
echo שלב 2: שומר שינויים...
set /p commitmsg="הכנס תיאור לשינויים (למשל: הוספת תמונות חדשות): "
if "%commitmsg%"=="" set commitmsg=הוספת תמונות חדשות

git commit -m "%commitmsg%"
if %errorlevel% neq 0 (
    echo שגיאה בשמירה
    pause
    exit /b 1
)

echo.
echo שלב 3: מעלה לאינטרנט...
git push
if %errorlevel% neq 0 (
    echo שגיאה בהעלאה
    pause
    exit /b 1
)

echo.
echo ========================================
echo הצלחה! התמונות עלו לאינטרנט
echo ========================================
echo כתובת האתר: https://olamhayeled.netlify.app
echo.
echo הערה: יכול לקחת כמה דקות עד שהאתר יתעדכן
pause
