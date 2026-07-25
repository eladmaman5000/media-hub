# HUB · ניטור תקשורת

אתר חי שמרכז אייטמים סביב חוק התקשורת / ערוץ 12 מול ערוץ 14 / רגולציית מדיה,
מאתרי חדשות ומחיפושי גוגל. מתעדכן **לבד כל שעה** דרך GitHub Actions — בלי מחשב
דלוק ובלי שום כלי מותקן אצל מי שצופה. פותחים קישור, זהו.

## איך זה עובד
- `index.html` — הדשבורד. טוען את `data.json` ומציג (חיפוש, סינון לפי מקור/מילת-מפתח, מיון).
- `collector.py` — הסקרייפר. מושך את עמודי הכתבים + חיפושי DuckDuckGo, מסנן לפי
  מילות המפתח, מוריד כפילויות מול `data.json`, וכותב `data.json` מחדש.
- `.github/workflows/refresh.yml` — מריץ את הסקרייפר **כל שעה** ומבצע commit ל-`data.json`.
- `data.json` — מאגר האייטמים (מגיע כבר מלא בגרסת פתיחה).

**סינון:** אייטם מאתר נכנס רק אם הכותרת מכילה מילת מפתח; אייטם מחיפוש גוגל נכנס בלי תנאי.

## פריסה (deploy) — פעם אחת, ~5 דקות
צריך חשבון GitHub. מתוך תיקיית `media-hub/`:

```bash
gh repo create media-hub --public --source=. --push
```

או ידני:
```bash
git init && git add -A && git commit -m "media-hub"
git branch -M main
git remote add origin https://github.com/<USER>/media-hub.git
git push -u origin main
```

אחר כך ב-GitHub:
1. **Settings → Pages** → Source: `Deploy from a branch` → Branch: `main` / `/ (root)` → Save.
   הקישור שיתקבל (`https://<USER>.github.io/media-hub/`) — זה מה ששולחים לחברה.
2. **Settings → Actions → General** → Workflow permissions → `Read and write permissions` → Save.
3. **Actions → refresh-hub → Run workflow** — הרצה ראשונה ידנית כדי לוודא שהכול עובד;
   מכאן זה רץ לבד כל שעה.

## מה שולחים לחברה
רק את הקישור: `https://<USER>.github.io/media-hub/`. אין מה להתקין.

## מגבלות (חשוב, בכנות)
- **X/טוויטר לא נאסף בגרסה הזו.** ראנר בענן לא מחובר ל-X → צריך X API בתשלום. עד אז הפיד בלי ציוצים ישירים.
- **חלק מהאתרים עלולים לחסום שרתים** (ישראל היום חוסם fetch ישיר; לכן הוא נמשך דרך DuckDuckGo). ייתכן ש-DuckDuckGo יגביל בקשות מ-IP של GitHub — אם מקור מסוים לא מחזיר תוצאות, בדקו את לוג ה-Action ותכווננו.
- **אתרים מאחורי מנוי** (הארץ/דה-מרקר פרימיום) — כותרות ותקצירים בלבד.
- **GitHub Actions בחינם** עלול להתעכב כמה דקות, ומושבת אוטומטית אחרי 60 יום ללא פעילות ברrepo (כניסה אחת ל-Actions ולחיצה על Run מאפסת את זה).

## הוספת מקורות / מילות מפתח
הכול ב-`collector.py`: הרשימות `KEYWORDS`, `SITES`, `SEARCHES`. משנים, עושים commit, ה-Action ירים את זה בריצה הבאה.

## הרצה מקומית לבדיקה
```bash
pip install -r requirements.txt
python collector.py
python -m http.server 8000   # ואז פותחים http://localhost:8000
```
