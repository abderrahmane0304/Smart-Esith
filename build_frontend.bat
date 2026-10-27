@echo off
echo Building React Dashboard...
cd frontend-dashboard
call npm run build
cd ..
echo Done! Build React genere dans backend/static/dashboard

