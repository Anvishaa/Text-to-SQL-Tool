import pandas as pd
import sqlite3

df = pd.read_csv("Data.csv", encoding="latin1", on_bad_lines="skip")
df.columns = [
    col.split(" [")[0].strip() if "[" in col else col.strip()
    for col in df.columns
]
df = df.replace("..", None)

conn = sqlite3.connect("worldbank.db")
df.to_sql("india_indicators", conn, if_exists="replace", index=False)
conn.close()

print("Database is ready to go!")