# google-calendar-booker
Find and book free slots in your Google calendar

```
# Clone
git clone https://github.com/rascal999/google-calendar-booker.git
cd google-calendar-booker

# Set up
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Find free slots for given email address(es) and optionally book
./gc_booker.py --config config.ini --emails test@test.com --title "Some meeting title"
./gc_booker.py --config config.ini --emails test@test.com bob.smith@test.com --title "JIRA-1" # Title will be ticket title

# Book meeting for epic with "Security Review" ticket
./scripts/schedule_srs.sh WFX-309
```
