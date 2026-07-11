import sqlite3
import pandas as pd

DB_PATH = "nectar_iot.db"
SQL_FILE = "src/sql_queries.sql"

def run_queries(db_path=DB_PATH, sql_file=SQL_FILE):
    # Read and split SQL queries by comments or double-newlines
    with open(sql_file, "r") as f:
        content = f.read()
        
    # Split queries by semicolon, filtering out empty ones
    raw_queries = content.split(";")
    queries = []
    
    for q in raw_queries:
        q_strip = q.strip()
        if q_strip:
            queries.append(q_strip)
            
    conn = sqlite3.connect(db_path)
    
    question_titles = [
        "1. Top 10 assets with the highest energy consumption",
        "2. Average daily energy consumption for each site",
        "3. Assets that generated more than 10 faults in the last 30 days",
        "4. Assets that have not reported telemetry for the last 24 hours",
        "5. Hourly utilization for each building (sample first 5 rows)",
        "6. Sites with abnormal increases in power consumption (day-over-day >50%)"
    ]
    
    for i, query in enumerate(queries):
        if i >= len(question_titles):
            break
            
        print(f"\n==================================================")
        print(f"{question_titles[i]}")
        print(f"==================================================")
        
        try:
            df = pd.read_sql_query(query, conn)
            if "utilization" in question_titles[i].lower():
                print(df.head(5).to_string(index=False))
            else:
                print(df.to_string(index=False))
        except Exception as e:
            print(f"Error running query: {e}")
            
    conn.close()

if __name__ == "__main__":
    run_queries()
