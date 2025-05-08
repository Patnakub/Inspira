$env:PYTHONIOENCODING = "utf-8"
$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logPath = "C:\Users\Lenovo\Desktop\scrapy_project_test\log_upcoming.txt"
Add-Content -Path $logPath -Value "✅ [$date] Task started"

$python = "C:\Users\Lenovo\AppData\Local\Programs\Python\Python311\python.exe"
$base = "C:\Users\Lenovo\Desktop\scrapy_project_test"

# ✅ Step 1: run_all_upcoming.py
Add-Content -Path $logPath -Value "▶ Running run_all_upcoming..."
& $python "$base\run_all_upcoming.py" >> $logPath 2>&1
Add-Content -Path $logPath -Value "✔ run_all_upcoming done"

# ✅ Step 2: rename_json_to_hash.py
Add-Content -Path $logPath -Value "▶ Running rename_json_to_hash..."
& $python "$base\rename_json_to_hash.py" >> $logPath 2>&1
Add-Content -Path $logPath -Value "✔ rename_json_to_hash done"

# ✅ Step 3: merge.py --mode=upcoming
Add-Content -Path $logPath -Value "▶ Running merge --mode=upcoming..."
& $python "$base\merge.py" --mode=upcoming >> $logPath 2>&1
Add-Content -Path $logPath -Value "✔ merge done"

Add-Content -Path $logPath -Value "✅ [$date] Task finished"
