# google-calendar-booker
Find and book free slots in your Google calendar

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

./gc_booker.py --config config.ini --emails test@test.com --title "Some meeting title"
./gc_booker.py --config config.ini --emails test@test.com --title "JIRA-1" # Title will be ticket title
```
