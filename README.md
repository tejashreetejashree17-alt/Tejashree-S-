# EventHive: Event Ticketing and Attendance Analytics
M.Sc. Data Science · DBMS for Analytics (25MSDA1S04) · Problem 16 · Domain: Events

EventHive is a relational database (MySQL 8) for organisers, venues, events, ticket tiers, attendees, bookings and
check-ins. SQL analyses sales velocity, no-shows and revenue by event type and venue. Attendee feedback forms whose
questions differ per event type are stored and aggregated in MongoDB.

## Contents
| File | Purpose |
|---|---|
| `schema.sql` | 8 tables in 3NF, PK/FK/CHECK/UNIQUE constraints, view `v_event_summary`, triggers `trg_prevent_overselling` and `trg_checkin_validate` |
| `data.sql` | ~14,300 rows (see below) |
| `queries.sql` | Part A: DML for booking, cancellation, check-in. Part B: 8 analytical queries (Q1-Q8) |
| `eventhive_analysis.ipynb` | Python DB-API notebook: connect, load, run queries, pandas analysis, charts |
| `mongodb/feedback.json` | 1,755 feedback documents (event-specific question sets) |
| `mongodb/mongo_scripts.js` | CRUD, 5 indexes, 3 aggregation pipelines |
| `generate_data.py` | Seeded (42) generator for `data.sql` and `feedback.json` |
| `charts/` | ER diagram and charts used in the presentation |

## Data source
Synthetic data generated with Python (`generate_data.py`, `random.seed(42)`, fully reproducible). Row counts:
organisers 6 · venues 12 · event_types 6 · events 38 · ticket_types 114 · attendees 1,200 · bookings 7,475 · checkins 5,460
(total 14,311). Booking times follow an exponential lead-time curve; show-up probability varies by event type and ticket tier.

## How to run
1. `mysql -u root -p < schema.sql` then `mysql -u root -p < data.sql` (triggers are active during load).
2. Run `queries.sql` in MySQL Workbench / CLI.
3. `pip install mysql-connector-python pandas matplotlib jupyter`, set `MYSQL_PWD`, open `eventhive_analysis.ipynb`.
4. MongoDB: `mongoimport --db eventhive --collection feedback --jsonArray --file mongodb/feedback.json`, then `mongosh < mongodb/mongo_scripts.js`.

## Design notes
* **3NF:** venue, organiser and event type live in their own tables; ticket price lives on `ticket_types`, not on
  `bookings`; check-ins are separate so "no-show" = confirmed booking with no check-in row.
* **Overselling:** `trg_prevent_overselling` rejects a CONFIRMED booking (SQLSTATE 45000) when the tier or the event is full;
  cancelling frees the seat because only CONFIRMED rows count.
* **SQL vs NoSQL:** feedback forms have different questions per event type, so a document with an `answers` array avoids
  a wide, sparse table or an EAV design.

## Verification note
The SQL was written for MySQL 8. It was also verified end-to-end on an equivalent engine (SQLite, with `DATEDIFF`
shimmed; `verify_sqlite.py`, `check_notebook.py`) including the trigger logic; the MongoDB pipeline results were
cross-checked with pandas. Re-run the scripts on your own MySQL/MongoDB to capture your own screenshots.
