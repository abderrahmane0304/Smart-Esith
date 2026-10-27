@echo off
echo Démarrage Smart ESITH...
cd backend
python -m venv venv 2>nul
call venv\Scripts\activate.bat
pip install -r requirements.txt -q
echo Serveur démarré sur http://localhost:5001
start http://localhost:5001
python app.py
