This repo powers a small fantasy NASCAR picks game (Door Bumper Clear).

## Recommended: run the dynamic web app
1. Set environment variables:
   - `DBC_PICKS_ADMIN_PASSWORD` (required): password for the admin pages
   - `DBC_PICKS_SECRET_KEY` (optional): Flask session secret (defaults to a dev value)
   - `DBC_PICKS_DB_PATH` (optional): where `dbcPicks.db` should live (defaults to `dbcPicks.db` in this folder)
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Start the server:
   - `python app.py`
   - or production-style: `gunicorn app:app`
4. Open:
   - Public scoreboard: `http://localhost:5000/`
   - Admin: `http://localhost:5000/admin/login`

Admin flow:
- Choose weekly picks in the admin UI and click `Save Draft Picks`.
- Click `Finalize Week` to fetch the latest ESPN results, score everyone, and lock the week.

## Legacy script (still present)
`DBC-Picks.py` can still be run manually by editing `PlayerStats.json`, then running the script to generate `weeklyResults.txt` and `Website/picks-data.json`.