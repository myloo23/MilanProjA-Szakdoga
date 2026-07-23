Development

Create venv:
python3.12 -m venv .venv

Activate:
source .venv/bin/activate

Run app:
flask --app app/app.py run

Run tests:
python -m pytest

Run Docker:
docker compose up --build