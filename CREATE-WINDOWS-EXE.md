# יצירת קובץ EXE ל-Windows

## הוראות ליצירת קובץ הפעלה ל-Windows:

### שלב 1: התקנת Python ב-Windows
1. הורד Python מ: https://www.python.org/downloads/
2. במהלך ההתקנה, סמן V ב-**"Add Python to PATH"**
3. לחץ Install Now

### שלב 2: התקנת OpenCV ו-PyInstaller
פתח Command Prompt (cmd) והרץ:

```bash
pip install opencv-python numpy pyinstaller
```

### שלב 3: יצירת הקובץ
1. פתח את התיקייה של הפרויקט ב-Command Prompt
2. הרץ:

```bash
pyinstaller --onefile --name blur_images blur_new_images.py
```

3. הקובץ יווצר בתיקייה `dist\blur_images.exe`

### שלב 4: העתקת הקבצים הנדרשים
העתק את `dist\blur_images.exe` לתיקיית הפרויקט (שם יש את התיקייה `img` ו-`models`)

### הערה חשובה:
הקובץ exe צריך להיות בתיקייה שמכילה:
- תיקיית `img` עם התמונות
- תיקיית `models` עם קבצי הזיהוי
- קובץ `blurred_images.txt`

---

# English Instructions:

## Creating Windows EXE:

### Step 1: Install Python on Windows
1. Download from: https://www.python.org/downloads/
2. During install, check **"Add Python to PATH"**
3. Click Install Now

### Step 2: Install OpenCV and PyInstaller
Open Command Prompt and run:

```bash
pip install opencv-python numpy pyinstaller
```

### Step 3: Create the EXE
1. Navigate to project folder in Command Prompt
2. Run:

```bash
pyinstaller --onefile --name blur_images blur_new_images.py
```

3. The file will be created in `dist\blur_images.exe`

### Step 4: Copy required files
Copy `dist\blur_images.exe` to your project folder (where `img` and `models` folders are)

### Important Note:
The exe needs to be in a folder containing:
- `img` folder with images
- `models` folder with detection files
- `blurred_images.txt` file
