import os
import subprocess
import glob
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPIDERS_DIR = os.path.join(BASE_DIR, 'scrapy_project', 'spiders')
MODE = 'upcoming'

def clear_old_data():
    print(f"Clearing old JSON files in raw_data/{MODE} ...")
    for root, dirs, files in os.walk(SPIDERS_DIR):
        raw_data_dir = os.path.join(root, 'raw_data', MODE)
        if os.path.exists(raw_data_dir):
            for file in glob.glob(os.path.join(raw_data_dir, '*.json')):
                try:
                    os.remove(file)
                    print(f"Deleted: {file}")
                except Exception as e:
                    print(f"Failed to delete {file}: {e}")

def run_spiders(suffix='_upcoming.py'):
    for root, dirs, files in os.walk(SPIDERS_DIR):
        for file in files:
            if file.endswith(suffix):
                spider_name = file.replace('.py', '')
                print(f"Running spider: {spider_name}")
                subprocess.run(
                    [sys.executable, '-m', 'scrapy', 'crawl', spider_name],
                    cwd=BASE_DIR  # Required to find scrapy.cfg
                )

if __name__ == '__main__':
    clear_old_data()
    run_spiders('_upcoming.py')
