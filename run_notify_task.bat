@echo off
cd /d C:\Users\Lenovo\Desktop\exhibition-backend
set SKIP_ELASTIC_SYNC=true
node cron\notifyEndingExhibitions.js
