import json
def md(s): return {"cell_type":"markdown","metadata":{},"source":s.strip("\n").splitlines(True)}
def code(s): return {"cell_type":"code","execution_count":None,"metadata":{},"outputs":[],"source":s.strip("\n").splitlines(True)}
cells = [
md("""# EventHive: Event Ticketing and Attendance Analytics
Python **DB-API** notebook. Connects to MySQL, loads the data, runs the queries from `queries.sql`, analyses with pandas and charts the results.

**Before running:** execute `schema.sql` then `data.sql` in MySQL, and `pip install mysql-connector-python pandas matplotlib`."""),
code("""
import os, re
import pandas as pd
import matplotlib.pyplot as plt
import mysql.connector                      # DB-API 2.0 driver (psycopg2 works the same way)
plt.rcParams.update({"font.size": 16, "axes.titlesize": 18, "legend.fontsize": 13})

def get_connection():
    return mysql.connector.connect(host="localhost", user="root",
                                   password=os.environ.get("MYSQL_PWD", ""), database="eventhive")

conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT VERSION()"); print("Connected to MySQL", cur.fetchone()[0])
"""),
code("""
def run_query(sql, params=None):
    \"\"\"Pure DB-API: cursor.execute -> fetchall -> DataFrame (columns from cursor.description).\"\"\"
    c = conn.cursor()
    c.execute(sql, params or ())
    cols = [d[0] for d in c.description]
    df = pd.DataFrame(c.fetchall(), columns=cols)
    c.close()
    for col in df.columns:                 # MySQL returns Decimal for SUM/ROUND -> make numeric
        try: df[col] = pd.to_numeric(df[col])
        except (ValueError, TypeError): pass
    return df

def load_queries(path="queries.sql"):
    \"\"\"Split the analytics part of queries.sql into {'Q1': sql, ...}.\"\"\"
    text = open(path).read().split("PART B : ANALYTICS")[1]
    parts = re.split(r"\\n-- (Q\\d+)\\.", "\\n" + text)
    return {parts[i]: parts[i+1].split("\\n", 1)[1].strip().rstrip(";") for i in range(1, len(parts), 2)}

Q = load_queries()
print(list(Q))

# 1) Check the load: row counts per table (>= 500 rows required)
tables = ["organisers","venues","event_types","events","ticket_types","attendees","bookings","checkins"]
counts = {t: run_query(f"SELECT COUNT(*) AS n FROM {t}")["n"][0] for t in tables}
print(counts, "TOTAL =", sum(counts.values()))
"""),
md("## 1. Booking curves: cumulative share of tickets sold by days before the event (Q1)"),
code("""
curve = run_query(Q["Q1"])
pivot = curve.pivot_table(index="days_before_event", columns="event_type", values="tickets_sold", aggfunc="sum").fillna(0)
pivot = pivot.sort_index(ascending=False)                       # 59 days out -> event day
cum_pct = pivot.cumsum() / pivot.sum() * 100

fig, ax = plt.subplots(figsize=(7.2, 5.2))
for col in cum_pct.columns:
    ax.plot(cum_pct.index, cum_pct[col], label=col, linewidth=3)
ax.invert_xaxis(); ax.set_xlabel("Days before event"); ax.set_ylabel("Cumulative % of tickets sold")
ax.set_title("Booking curves by event type"); ax.legend(); ax.grid(alpha=.3)
os.makedirs("charts", exist_ok=True); fig.savefig("charts/booking_curves.png", dpi=200, bbox_inches="tight"); plt.show()
"""),
md("## 2. No-show rate by event type (Q2) and by ticket tier (Q6)"),
code("""
noshow = run_query(Q["Q2"]); tiers = run_query(Q["Q6"])
display(noshow); display(tiers)
fig, ax = plt.subplots(figsize=(7.2, 5.2))
d = noshow.sort_values("no_show_pct")
ax.barh(d["event_type"], d["no_show_pct"], color="#0062A9")
for y, v in enumerate(d["no_show_pct"]): ax.text(v + .3, y, f"{v:.1f}%", va="center")
ax.set_xlabel("No-show rate (%)"); ax.set_title("No-show rate by event type")
fig.savefig("charts/no_show_by_type.png", dpi=200, bbox_inches="tight"); plt.show()
"""),
md("## 3. Revenue, sell-through and sales velocity (Q3, Q4, Q5, Q8)"),
code("""
display(run_query(Q["Q3"])); display(run_query(Q["Q4"])); display(run_query(Q["Q5"])); display(run_query(Q["Q8"]))
"""),
md("## 4. Pandas analysis on top of SQL: revenue per event, attendance vs. sales"),
code("""
ev = run_query("SELECT * FROM v_event_summary WHERE event_date < CURDATE()")
ev["attendance_pct"] = (ev["attended"] / ev["tickets_sold"] * 100).round(1)
ev["sell_through_pct"] = (ev["tickets_sold"] / ev["capacity"] * 100).round(1)
print(ev[["tickets_sold","revenue","attendance_pct","sell_through_pct"]].describe().round(1))
print("Correlation sell-through vs attendance:", round(ev["sell_through_pct"].corr(ev["attendance_pct"]), 2))
print("Total revenue (completed events): Rs", f"{ev['revenue'].sum():,.0f}")
"""),
md("## 5. Parameterised DML from Python (booking + cancellation), then clean up"),
code("""
cur = conn.cursor()
cur.execute("INSERT INTO bookings (attendee_id, ticket_type_id, booked_at, status) VALUES (%s, %s, NOW(), 'CONFIRMED')", (10, 2))
new_id = cur.lastrowid
cur.execute("UPDATE bookings SET status='CANCELLED', cancelled_at=NOW() WHERE booking_id=%s", (new_id,))
conn.commit(); print("booked and cancelled booking", new_id)
cur.execute("DELETE FROM bookings WHERE booking_id=%s", (new_id,)); conn.commit()
conn.close()
"""),
]
nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
      "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
json.dump(nb, open("eventhive_analysis.ipynb", "w"), indent=1)
print("notebook written,", len(cells), "cells")
