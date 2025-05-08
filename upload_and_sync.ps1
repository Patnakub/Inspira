$env:PYTHONIOENCODING = "utf-8"
$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logPath = "C:\Users\Lenovo\Desktop\scrapy_project_test\log_upload_and_sync.txt"

Add-Content -Path $logPath -Value "[INFO][$date] Upload & Sync Task started"

$python = "C:\Users\Lenovo\AppData\Local\Programs\Python\Python311\python.exe"
$base = "C:\Users\Lenovo\Desktop\scrapy_project_test"

# Step 1: upload_to_mongo.py
Add-Content -Path $logPath -Value "[INFO] Running upload_to_mongo..."
& $python "$base\upload_to_mongo.py" >> $logPath 2>&1
Add-Content -Path $logPath -Value "[INFO] upload_to_mongo done"

$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $logPath -Value "[INFO][$date] Upload & Sync Task finished"
