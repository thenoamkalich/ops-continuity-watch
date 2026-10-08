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

## סכמה, ולידציה וציון (שלב 1 של DASHBOARD_SPEC)
מסמכי מקור: `docs/HANDOFF.md`, `docs/DASHBOARD_SPEC.md`.

- `schema/event.schema.json`: סכמת אירוע (סעיף 7). `scripts/validate.py` פוסל פריט פגום ומחזיר אותו כ"פער מידע".
- `scripts/score.py`: אחוזון מול היסטוריה ל-1-10, מדד כולל משוקלל, תוויות, מגמה (סעיף 4). ללא היסטוריה: "אין בסיס להשוואה".
- `config/scoring.json`: משקלות, תוויות וספים. הצעה, טרם אושרה.

בדיקות (נתוני דמה בלבד, `tests/fixtures/DUMMY_*`):
```
python -m unittest discover -s tests
```
