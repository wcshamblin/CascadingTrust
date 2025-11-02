#tmux new-session -d -n "Atlas-API" python3 -m uvicorn --reload --workers 33 --port 8000 app:app
python3 -m uvicorn --reload --workers 4 --port 8000 app:app
