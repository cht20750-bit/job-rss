# Job RSS - משרות הייטק חיפה/צפון

אוסף אוטומטי של משרות הייטק באזור חיפה והצפון מ-20+ מקורות שונים.

## איך זה עובד

1. **GitHub Actions** רץ כל בוקר ב-9:30
2. **Selenium** (Chrome headless) פותח כל אתר, מריץ JavaScript, ושולף את המשרות
3. **Python** מסנן משרות טכנולוגיות באזור חיפה/צפון
4. **RSS XML** נשמר ומתפרסם ב-GitHub Pages

## הוספת מקור חדש

1. הוסף פונקציית parser ב-`scraper.py`
2. הוסף לרשימת `SOURCES`
3. פתח PR

## הרצה מקומית

```bash
pip install -r requirements.txt
python scraper.py
# או למקור ספציפי:
python scraper.py JobKarov
```
