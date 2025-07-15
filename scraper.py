import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

# Read your Excel file
df = pd.read_excel("Master PE List.xlsx")

# Filter out rows where url is not None/empty and take only first 5
valid_urls = df[df['url'].notna()].head(2)

print(f"Found {len(valid_urls)} companies with valid URLs (limited to first 5)")

# Setup Chrome driver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

# Open first URL
if len(valid_urls) > 0:
    first_row = valid_urls.iloc[0]
    print(f"Opening first tab: {first_row['Title']}")
    driver.get(first_row['url'])
    
    # Open remaining URLs in new tabs
    for _, row in valid_urls.iloc[1:].iterrows():
        print(f"Opening tab: {row['Title']}")
        driver.execute_script(f"window.open('{row['url']}', '_blank');")
        time.sleep(200)

print(f"Opened {len(valid_urls)} tabs")