import pandas as pd
import re

def create_company_url(company_name):
    # Remove special characters (keep only letters, numbers, and spaces)
    clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', company_name)
    
    # Convert to lowercase and replace spaces with hyphens
    url_part = clean_name.lower().replace(" ", "-")
    
    # Remove multiple consecutive hyphens and leading/trailing hyphens
    url_part = re.sub(r'-+', '-', url_part).strip('-')
    
    base_url = "https://network.axial.net/company/"
    return base_url + url_part

def get_special_characters(company_name):
    # Find all special characters that were removed
    special_chars = re.findall(r'[^a-zA-Z0-9\s]', company_name)
    if special_chars:
        return ', '.join(set(special_chars))  # Remove duplicates
    return None

df = pd.read_excel("Master PE List.xlsx")

df['url'] = df['Title'].apply(create_company_url)
df['removed_characters'] = df['Title'].apply(get_special_characters)

# Display results
for _, row in df.iterrows():
    if row['removed_characters'] is not None:
        print(f"{row['Title']} → {row['url']} (removed: {row['removed_characters']})")
    else:
        print(f"{row['Title']} → {row['url']}")

print(f"\nSummary:")
print(f"Total companies: {len(df)}")
print(f"URLs created: {len(df)}")
print(f"Companies with special characters removed: {df['removed_characters'].notna().sum()}")

# Save the DataFrame back to Excel
df.to_excel("Master PE List.xlsx", index=False)