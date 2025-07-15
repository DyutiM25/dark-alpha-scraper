import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait # Corrected import
from selenium.webdriver.support import expected_conditions as EC # Corrected import
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

# Read your Excel file
df = pd.read_excel("Master PE List.xlsx")

# Filter out rows where url is not None/empty and take only first 2 for demonstration
valid_urls = df[df['url'].notna()].head(2)

print(f"Found {len(valid_urls)} companies with valid URLs (limited to first 2 for demo)")

# Setup Chrome driver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)
wait = WebDriverWait(driver, 10) # Initialize WebDriverWait for explicit waits

scraped_data = []

try:
    for index, row in valid_urls.iterrows():
        print(f"\nProcessing: {row['Title']}")

        try:
            # Open URL
            driver.get(row['url'])
            time.sleep(3)  # Give the page some time to load initially

            # Get the full page text for keyword-based extraction
            page_text = driver.find_element(By.TAG_NAME, "body").text

            # Helper to extract section by keyword (for Overview and Location)
            def extract_section(keyword_list):
                lines = page_text.split('\n')
                for keyword in keyword_list:
                    start_idx = -1
                    for i, line in enumerate(lines):
                        if keyword.lower() in line.lower():
                            start_idx = i
                            break
                    if start_idx != -1:
                        section_lines = []
                        # Look for content in the next few lines, stopping if a new heading or empty lines appear
                        for i in range(start_idx + 1, min(start_idx + 15, len(lines))): # Increased range
                            line_content = lines[i].strip()
                            if not line_content: # Stop on empty lines
                                break
                            # Heuristic to stop if it looks like a new section heading
                            if any(h_keyword.lower() in line_content.lower() for h_keyword in ["Overview", "Location", "Transactions", "Team", "Contact"]):
                                break
                            section_lines.append(line_content)
                            if len(section_lines) >= 5: # Get a bit more text
                                break
                        return ' '.join(section_lines)
                return None

            # --- Scrape Overview ---
            overview_text = None
            try:
                # Try to find by heading first
                heading = driver.find_element(By.XPATH, "//h2[contains(text(), 'Overview')] | //h3[contains(text(), 'Overview')] | //h4[contains(text(), 'Overview')]")
                # Get text from the following sibling, often a paragraph or div
                overview_text = heading.find_element(By.XPATH, "following-sibling::*[1]").text
                print(f"✓ Found Overview by heading")
            except Exception:
                pass # If heading not found, try text search
            if not overview_text or overview_text.strip() == "":
                overview_text = extract_section(["Overview", "About Us", "Company Profile"])
                if overview_text:
                    print(f"✓ Found Overview by text search")
            if not overview_text or overview_text.strip() == "":
                overview_text = "Overview not found"

            # --- Scrape Location ---
            location_text = None
            location_text = extract_section(["Location", "Address", "Contact"])
            if location_text:
                print(f"✓ Found Location by text search")
            if not location_text or location_text.strip() == "":
                location_text = "Location not found"

            # --- Scrape URL from a.u-link ---
            page_url = None
            try:
                # Corrected CSS selector to target the <a> tag with class u-link directly
                link_elem = driver.find_element(By.CSS_SELECTOR, "a.u-link")
                page_url = link_elem.get_attribute("href")
                print(f"✓ Found page URL from a.u-link: {page_url}")
            except Exception:
                page_url = "URL not found in a.u-link"

            # --- Scrape ALL Transactions ---
            all_transactions = []
            while True:
                # Wait for transaction elements to be present
                try:
                    wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "axl-legacy-tombstone")))
                except Exception:
                    print("No more 'axl-legacy-tombstone' elements found or page did not load correctly.")
                    break # Exit loop if no tombstone elements are found

                tombstones = driver.find_elements(By.TAG_NAME, "axl-legacy-tombstone")
                if not tombstones:
                    print("No transactions found on current page.")
                    break

                for tombstone in tombstones:
                    try:
                        # Extracting party, activity, company name
                        parties = tombstone.find_elements(By.CLASS_NAME, "tombstone-party")
                        acquirer_investor = parties[0].text if len(parties) > 0 else "N/A"
                        company_name = parties[1].text if len(parties) > 1 else "N/A"

                        activity_elem = tombstone.find_element(By.CLASS_NAME, "tombstone-activity")
                        activity = activity_elem.text if activity_elem else "N/A"

                        # Extracting industry and date from the footer div
                        footer_div = tombstone.find_element(By.CLASS_NAME, "footer")
                        footer_spans = footer_div.find_elements(By.CSS_SELECTOR, "span.u-text-xs-01.u-text-color-secondary")

                        industry = footer_spans[0].text if len(footer_spans) > 0 else "N/A"
                        date = footer_spans[1].text if len(footer_spans) > 1 else "N/A"

                        all_transactions.append({
                            'Acquirer/Investor': acquirer_investor,
                            'Activity': activity,
                            'Company': company_name,
                            'Industry': industry,
                            'Date': date
                        })
                    except Exception as e:
                        print(f"Warning: Could not scrape one transaction: {e}")
                        # Append partial data or a placeholder if an error occurs for a single transaction
                        all_transactions.append({
                            'Acquirer/Investor': 'Error',
                            'Activity': 'Error',
                            'Company': 'Error',
                            'Industry': 'Error',
                            'Date': 'Error'
                        })

                # Check for the next pagination button
                next_button = None
                try:
                    # Look for the button with the right arrow icon or text
                    # The screenshots show a `>` button. We need to find its selector.
                    # Assuming it's a button or div with a specific class or aria-label for 'next'
                    # Let's try finding the next button by its common attributes or structure
                    # Based on common patterns, it might be a button with a specific class or an SVG icon
                    # If there's a parent div for pagination, it would be good to target that.
                    # Let's assume the next button has an aria-label or a specific class like 'next-page' or contains an SVG for a right arrow.
                    # From the screenshot, it looks like a button within a pagination control.
                    # Let's try to find a button with an aria-label "Next page" or similar, or by its text content if it's visible.
                    # Since it's a generic looking arrow, let's try to find it by its SVG or a parent element.
                    # A common pattern is a button that is not disabled and contains an arrow icon.
                    next_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Next page') or contains(@class, 'pagination-next')] | //button[./*[name()='svg' and contains(@data-icon, 'arrow-right')]] | //button[contains(., '>') and not(@disabled)]")
                    if "disabled" in next_button.get_attribute("class") or next_button.get_attribute("disabled"):
                        print("Next button is disabled. End of transactions.")
                        break
                    next_button.click()
                    print("Clicked next page button.")
                    time.sleep(3) # Wait for the next page to load
                except Exception as e:
                    print(f"No next pagination button found or it's disabled: {e}. Ending transaction scraping.")
                    break # Exit loop if no next button or error clicking it

            # Store the data
            scraped_data.append({
                'Title': row['Title'],
                'Overview': overview_text,
                'Location': location_text,
                'URL': page_url,
                'Transactions': all_transactions # Store the list of transactions
            })

            print(f"✓ Scraped: {row['Title']}")

        except Exception as e:
            print(f"✗ Error processing {row['Title']}: {str(e)}")
            scraped_data.append({
                'Title': row['Title'],
                'Overview': f"Error: {str(e)}",
                'Location': "Error",
                'Transaction': "Error", # Keep "Transaction" for consistency, but it will be an error string
                'URL': "Error"
            })

        time.sleep(2) # Short pause between companies

finally:
    print(f"\n=== SCRAPING COMPLETE ===")
    print(f"Total companies processed: {len(scraped_data)}")

    # Save to TXT file
    with open("scraped_data.txt", "w", encoding="utf-8") as f:
        for data in scraped_data:
            f.write(f"Title: {data['Title']}\n")
            f.write(f"Overview: {data['Overview']}\n")
            f.write(f"Location: {data['Location']}\n")
            f.write(f"URL: {data['URL']}\n")
            f.write(f"--- Transactions ---\n")
            if isinstance(data['Transactions'], list):
                if data['Transactions']:
                    for i, transaction in enumerate(data['Transactions']):
                        f.write(f"  Transaction {i+1}:\n")
                        f.write(f"    Acquirer/Investor: {transaction.get('Acquirer/Investor', 'N/A')}\n")
                        f.write(f"    Activity: {transaction.get('Activity', 'N/A')}\n")
                        f.write(f"    Company: {transaction.get('Company', 'N/A')}\n")
                        f.write(f"    Industry: {transaction.get('Industry', 'N/A')}\n")
                        f.write(f"    Date: {transaction.get('Date', 'N/A')}\n")
                else:
                    f.write("  No transactions found.\n")
            else: # Handle the case where 'Transactions' might be an error string
                f.write(f"  {data['Transactions']}\n")
            f.write("\n")  # blank line between companies

    print(f"Results saved to 'scraped_data.txt'")

    input("Press Enter to close browser...")
    driver.quit()
