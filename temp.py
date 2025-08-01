import pandas as pd

# Read the CSV file
df = pd.read_csv('personal_financial_all_nohit.csv')

# Keep only the first 100 rows
df_cropped = df.head(100)

# Save to a new file (or overwrite the original)
df_cropped.to_csv('personal_financial_all_nohit_100.csv', index=False)