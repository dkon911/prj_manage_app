import pandas as pd

# Create a DataFrame with a 'Date' column
df = pd.DataFrame({
    'Date': pd.to_datetime(['2024-01-05', '2024-03-10', '2023-12-31']),
    'Value': [10, 20, 30]
})

# Extract the week number and assign it to a new column 'Week_Number'
df['Week_Number'] = df['Date'].dt.isocalendar().week

print(df)