# ops-continuity-watch

דשבורד סיכון לרציפות תפקוד, בעברית (RTL), באירוח GitHub Pages. מתעדכן ממקורות פתוחים.

## כללים
- מידע מאומת בלבד, כל פריט עם קישור למקור.
- ציונים מחושבים בקוד בלבד.
- מפתחות API רק ב-GitHub Secrets.

## מבנה
- `scripts/collect_*.py`: איסוף לכל תחום, פלט ל-`data/*.json`.
- `data/`: נתונים שנאספו.
- `index.html`, `docs/`: הדף.

## רעידות אדמה (שלב 1)
מקור: EMSC FDSN Event, https://www.seismicportal.eu/fdsnws/event/1/query (CC BY 4.0).

```
python scripts/collect_earthquakes.py --days 7
```

אזורים וספים (הצעה, טרם אושרו):

| אזור | גבולות | סף |
|---|---|---|
| ישראל | 29.3-33.5N, 34.2-35.9E | M>=2.5 |
| שכנות והשבר הסורי-אפריקאי | 27-37.5N, 31-42E | M>=3.5 |
| עולם | כל העולם | M>=6.0 |

האזורים חופפים: אירוע בישראל יכול להופיע גם ב"שכנות".

Credit: EMSC-CSEM SeismicPortal, https://www.seismicportal.eu
