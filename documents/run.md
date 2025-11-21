PS C:\Users\atulk\My Other Data\work\github\agents-capstone> poetry run python -m src.main

PS C:\Users\atulk\My Other Data\work\github\agents-capstone> poetry run pytest


#add -s parameteter to output print statements on console
PS C:\Users\atulk\My Other Data\work\github\agents-capstone> poetry run pytest -s tests/test_eval_golden.py

#run adk web (sessions persisted in sqllite db)
PS C:\Users\atulk\My Other Data\work\github\agents-capstone> poetry run adk web --port 8000 src/adk_agents --session_service_uri=sqlite+aiosqlite:///adk_sessions.db

#run only the specified test case
PS C:\Users\atulk\My Other Data\work\github\agents-capstone> poetry run pytest -s tests/test_flow_golden_incidents.py -k test_run_scenario_first_golden

#query adk session db
PS C:\Users\atulk\My Other Data\work\github\agents-capstone> sqlite3 .\adk_sessions.db