# import pandas as pd
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.chrome.service import Service
# import time

# # Read your Excel file
# df = pd.read_excel("Master PE List.xlsx")

# # Filter out rows where url is not None/empty and take only first 5
# valid_urls = df[df['url'].notna()].head(2)

# print(f"Found {len(valid_urls)} companies with valid URLs (limited to first 5)")

# # Setup Chrome driver
# service = Service(ChromeDriverManager().install())
# driver = webdriver.Chrome(service=service)

# # Open first URL
# if len(valid_urls) > 0:
#     first_row = valid_urls.iloc[0]
#     print(f"Opening first tab: {first_row['Title']}")
#     driver.get(first_row['url'])
    
#     # Open remaining URLs in new tabs
#     for _, row in valid_urls.iloc[1:].iterrows():
#         print(f"Opening tab: {row['Title']}")
#         driver.execute_script(f"window.open('{row['url']}', '_blank');")
#         time.sleep(200)

# print(f"Opened {len(valid_urls)} tabs")

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

# Read your Excel file
df = pd.read_excel("Master PE List.xlsx")

# Filter out rows where url is not None/empty and take only first 2
valid_urls = df[df['url'].notna()].head(2)

print(f"Found {len(valid_urls)} companies with valid URLs (limited to first 2)")

# Setup Chrome driver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

# List to store scraped data
scraped_data = []

try:
    for index, row in valid_urls.iterrows():
        print(f"\nProcessing: {row['Title']}")
        
        try:
            # Open URL
            driver.get(row['url'])
            time.sleep(3)  # Wait for page to load
            
            page_text = driver.find_element(By.TAG_NAME, "body").text

            # Helper to extract section by keyword
            def extract_section(keyword):
                lines = page_text.split('\n')
                start_idx = -1
                for i, line in enumerate(lines):
                    if keyword.lower() in line.lower():
                        start_idx = i
                        break
                if start_idx != -1:
                    section_lines = []
                    for i in range(start_idx + 1, min(start_idx + 10, len(lines))):
                        if lines[i].strip():
                            section_lines.append(lines[i].strip())
                        if len(section_lines) >= 3:
                            break
                    return ' '.join(section_lines)
                return None

            # --- Scrape Overview ---
            overview_text = None
            try:
                heading = driver.find_element(By.XPATH, "//h2[contains(text(), 'Overview')] | //h3[contains(text(), 'Overview')] | //h4[contains(text(), 'Overview')]")
                overview_text = heading.find_element(By.XPATH, "following-sibling::*").text
                print(f"✓ Found Overview by heading")
            except:
                pass
            if not overview_text:
                overview_text = extract_section("Overview")
                if overview_text:
                    print(f"✓ Found Overview by text search")
            if not overview_text:
                overview_text = "Overview not found"

            # --- Scrape Location ---
            location_text = None
            try:
                location_text = extract_section("Location")
                if location_text:
                    print(f"✓ Found Location by text search")
            except:
                pass
            if not location_text:
                location_text = "Location not found"

            # --- Scrape Transactions ---
            transactions_text = None
            try:
                transactions_text = extract_section("Transactions")
                if transactions_text:
                    print(f"✓ Found Transactions by text search")
            except:
                pass
            if not transactions_text:
                transactions_text = "Transactions not found"

            # Store the data
            scraped_data.append({
                'Title': row['Title'],
                'Overview': overview_text,
                'Location': location_text,
                'Transaction': transactions_text,
                'URL': row['url']
            })
            
            print(f"✓ Scraped: {row['Title']}")

        except Exception as e:
            print(f"✗ Error processing {row['Title']}: {str(e)}")
            scraped_data.append({
                'Title': row['Title'],
                'Overview': f"Error: {str(e)}",
                'Location': "Error",
                'Transaction': "Error",
                'URL': row['url']
            })

        time.sleep(2)

finally:
    print(f"\n=== SCRAPING COMPLETE ===")
    print(f"Total companies processed: {len(scraped_data)}")

    # Save to TXT file
    with open("scraped_data.txt", "w", encoding="utf-8") as f:
        for data in scraped_data:
            f.write(f"Title: {data['Title']}\n")
            f.write(f"Overview: {data['Overview']}\n")
            f.write(f"Location: {data['Location']}\n")
            f.write(f"Transaction: {data['Transaction']}\n")
            f.write(f"URL: {data['URL']}\n")
            f.write("\n")  # blank line between companies

    print(f"Results saved to 'scraped_data.txt'")

    input("Press Enter to close browser...")
    driver.quit()
