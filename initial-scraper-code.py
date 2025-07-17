import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import os # Import the os module for path manipulation

# Read your Excel file
df = pd.read_excel("Master PE List.xlsx")

# Filter out rows where url is not None/empty - PROCESS ALL VALID URLs
# valid_urls = df[df['url'].notna()].head(2)
valid_urls = df[df['url'].notna()].iloc[[239]]

print(f"Found {len(valid_urls)} companies with valid URLs")

# Setup Chrome driver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)
driver.maximize_window() 
wait = WebDriverWait(driver, 10) # Initialize WebDriverWait for explicit waits

# Create a directory to store the scraped data if it doesn't exist
output_dir = "scraped_company_data"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"Created output directory: {output_dir}")

try:
    for index, row in valid_urls.iterrows():
        print(f"\nProcessing: {row['Title']}")

        # Derive filename from the URL
        url_path = row['url'].rstrip('/') # Remove trailing slash if any
        filename_part = url_path.split('/')[-1]
        output_filename = os.path.join(output_dir, f"{filename_part}.txt")

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
                # Locate the <p> parent of the <span>
                btn = driver.find_element(By.XPATH, "//p[contains(@class, 'p--expand-label') and .//span[@more-label]]")

                if btn.is_displayed() and btn.is_enabled():
                    # Use JavaScript to trigger proper click event
                    driver.execute_script("arguments[0].click();", btn)
                    print("✓ Clicked 'Show full description' <p> element")

                    # Wait for the "Show full description" span to disappear, indicating expanded
                    wait.until(EC.invisibility_of_element_located(
                        (By.XPATH, "//span[@more-label and contains(text(), 'Show full description')]")
                    ))

            except Exception:
                print("No 'Show full description' <p> found or not clickable, continuing without it.")

            try:
                heading = driver.find_element(By.XPATH, "//h2[contains(text(), 'Overview')] | //h3[contains(text(), 'Overview')] | //h4[contains(text(), 'Overview')] | //h5[contains(text(), 'Overview')] | //h6[contains(text(), 'Overview')]")
                desc_container = heading.find_element(By.XPATH, "following-sibling::*[1]")

                # Clean out any leftover span if still present
                try:
                    show_more_span = desc_container.find_element(By.XPATH, ".//span[@more-label]")
                    driver.execute_script("arguments[0].remove();", show_more_span)
                except Exception:
                    pass

                overview_text = desc_container.text
                print("✓ Found Overview by heading")
            except Exception:
                pass

            if not overview_text or overview_text.strip() == "":
                overview_text = extract_section(["Overview", "About Us", "Company Profile"])
                if overview_text:
                    print("✓ Found Overview by text search")

            if not overview_text or overview_text.strip() == "":
                overview_text = "Overview not found"


            # --- Scrape Location ---
            location_text = None

            # First try text-based extraction with keywords
            location_text = extract_section(["Location", "Address", "Contact Information", "Headquarters"])
            if location_text:
                print(f"✓ Found Location by text search")

            if not location_text or location_text.strip() == "":
                # Try specific element-based location finding if text search fails
                try:
                    location_element = driver.find_element(
                        By.XPATH,
                        "//p[contains(@class, 'u-text-body')]/span[1]"
                    )
                    location_text = location_element.text.strip()
                    print(f"✓ Found Location by specific XPath")
                except Exception as e:
                    location_text = "Location not found"
                    print(f"✗ Location not found: {e}")

            print(f"Location: {location_text}")


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

            # Save data to individual TXT file for the current company
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(f"Title: {row['Title']}\n")
                f.write(f"Overview: {overview_text}\n")
                f.write(f"Location: {location_text}\n")
                f.write(f"URL: {page_url}\n")
                f.write(f"--- Transactions ---\n")
                if all_transactions:
                    for i, transaction in enumerate(all_transactions):
                        f.write(f"  Transaction {i+1}:\n")
                        f.write(f"    Acquirer/Investor: {transaction.get('Acquirer/Investor', 'N/A')}\n")
                        f.write(f"    Activity: {transaction.get('Activity', 'N/A')}\n")
                        f.write(f"    Company: {transaction.get('Company', 'N/A')}\n")
                        f.write(f"    Industry: {transaction.get('Industry', 'N/A')}\n")
                        f.write(f"    Date: {transaction.get('Date', 'N/A')}\n")
                else:
                    f.write("  No transactions found.\n")
                f.write("\n")  # blank line at the end of each file

            print(f"✓ Scraped: {row['Title']} and saved to {output_filename}")

        except Exception as e:
            error_message = f"Error processing {row['Title']}: {str(e)}"
            print(f"✗ {error_message}")
            # If an error occurs, save an error message to the specific company's file
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(f"Title: {row['Title']}\n")
                f.write(f"URL: {row['url']}\n")
                f.write(f"Error: {error_message}\n")

        time.sleep(2) # Short pause between companies

finally:
    print(f"\n=== SCRAPING COMPLETE ===")
    print(f"All valid companies processed. Check the '{output_dir}' directory for individual files.")

    input("Press Enter to close browser...")
    driver.quit()