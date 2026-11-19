"""Verification harness: runs the project on SQLite (DATEDIFF shimmed) to prove the logic and
produce the numbers/charts used in the presentation.  The real target is MySQL 8 (schema.sql)."""
import sqlite3, re, datetime as dt, sys
def datediff(a, b):
    f = lambda s: dt.date.fromisoformat(str(s)[:10])
    return (f(a) - f(b)).days
def build(path=":memory:"):
    con = sqlite3.connect(path); con.create_function("DATEDIFF", 2, datediff); con.create_function("CURDATE", 0, lambda: "2026-11-19")
    ddl = open("schema.sql").read().split("-- VIEW")[0] if False else open("schema.sql").read()
    tables = ddl[ddl.index("CREATE TABLE organisers"):ddl.index("-- =====", ddl.index("CREATE TABLE checkins"))]
    tables = tables.replace("INT AUTO_INCREMENT PRIMARY KEY", "INTEGER PRIMARY KEY")
    tables = re.sub(r"ENUM\([^)]*\)", "TEXT", tables); tables = re.sub(r"\) ENGINE=InnoDB", ")", tables)
    tables = re.sub(r",\s*INDEX [^\n]*", "", tables)
    con.executescript(tables)
    view = ddl[ddl.index("CREATE VIEW"):ddl.index("-- =====", ddl.index("CREATE VIEW"))]
    con.executescript(view)
    con.executescript("""
    CREATE TRIGGER trg_prevent_overselling BEFORE INSERT ON bookings WHEN NEW.status='CONFIRMED'
    BEGIN
      SELECT RAISE(ABORT,'Sold out: ticket tier is full') WHERE
        (SELECT COUNT(*) FROM bookings WHERE ticket_type_id=NEW.ticket_type_id AND status='CONFIRMED')
        >= (SELECT quantity_total FROM ticket_types WHERE ticket_type_id=NEW.ticket_type_id);
      SELECT RAISE(ABORT,'Sold out: event capacity reached') WHERE
        (SELECT COUNT(*) FROM bookings b JOIN ticket_types t ON t.ticket_type_id=b.ticket_type_id
          WHERE b.status='CONFIRMED' AND t.event_id=(SELECT event_id FROM ticket_types WHERE ticket_type_id=NEW.ticket_type_id))
        >= (SELECT capacity FROM events WHERE event_id=(SELECT event_id FROM ticket_types WHERE ticket_type_id=NEW.ticket_type_id));
    END;
    CREATE TRIGGER trg_checkin_validate BEFORE INSERT ON checkins
    BEGIN
      SELECT RAISE(ABORT,'Cannot check in a cancelled booking') WHERE (SELECT status FROM bookings WHERE booking_id=NEW.booking_id)<>'CONFIRMED';
    END;""")
    data = open("data.sql").read().replace("USE eventhive;", "").replace("SET FOREIGN_KEY_CHECKS = 1;", "")
    con.executescript(data)           # triggers ARE active while loading
    return con
def analytics():
    src = open("queries.sql").read().split("-- PART B")[1] if "-- PART B" in open("queries.sql").read() else open("queries.sql").read().split("PART B : ANALYTICS")[1]
    parts = re.split(r"\n-- (Q\d+)\.", "\n" + src)
    return {parts[i]: parts[i+1].split("\n", 1)[1] for i in range(1, len(parts), 2)}
if __name__ == "__main__":
    import pandas as pd
    con = build()
    for t in ["organisers","venues","event_types","events","ticket_types","attendees","bookings","checkins"]:
        print(t, con.execute(f"select count(*) from {t}").fetchone()[0])
    pd.set_option("display.width", 200); pd.set_option("display.max_columns", 20)
    for k, sql in analytics().items():
        sql = sql.replace("SUM(b.status = 'CANCELLED')", "SUM(b.status = 'CANCELLED')")
        print("\n==", k); print(pd.read_sql(sql.strip().rstrip(";"), con).head(12).to_string(index=False))
