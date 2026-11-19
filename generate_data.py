"""EventHive synthetic data generator (seeded, reproducible).
Writes: data.sql (MySQL INSERTs) and mongodb/feedback.json (MongoDB documents).
Run:  python generate_data.py
"""
import random, json, datetime as dt
random.seed(42)
TODAY = dt.date(2026, 11, 19)

def q(v):
    if v is None: return "NULL"
    if isinstance(v, (int, float)): return str(v)
    return "'" + str(v).replace("'", "''") + "'"

def insert(table, cols, rows, batch=250):
    out = []
    for i in range(0, len(rows), batch):
        chunk = rows[i:i+batch]
        vals = ",\n  ".join("(" + ", ".join(q(x) for x in r) + ")" for r in chunk)
        out.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES\n  {vals};")
    return "\n".join(out) + "\n"

# ---------- reference data ----------
organisers = [(1,"Spotlight Productions","hello@spotlight.in","9800000001"),
 (2,"Summit Events Pvt Ltd","team@summitevents.in","9800000002"),
 (3,"Pulse Entertainment","contact@pulse.in","9800000003"),
 (4,"Arena Sports Group","info@arenasports.in","9800000004"),
 (5,"Curtain Call Theatre Co","bookings@curtaincall.in","9800000005"),
 (6,"LearnLab Workshops","learn@learnlab.in","9800000006")]
etypes = ["Concert","Conference","Workshop","Sports","Festival","Theatre"]
event_types = [(i+1, n) for i, n in enumerate(etypes)]
venues_raw = [("Palace Grounds","Bengaluru",400),("Chinnaswamy Indoor Arena","Bengaluru",320),
 ("Phoenix Convention Hall","Mumbai",380),("NSCI Dome","Mumbai",300),
 ("Jawaharlal Nehru Stadium Annex","Delhi",400),("Siri Fort Auditorium","Delhi",220),
 ("Hitex Exhibition Centre","Hyderabad",350),("Shilpakala Vedika","Hyderabad",200),
 ("Music Academy Hall","Chennai",180),("Nehru Indoor Stadium","Chennai",300),
 ("Biswa Bangla Sabhaghar","Kolkata",250),("Balewadi Arena","Pune",280)]
venues = [(i+1, n, c, cap) for i, (n, c, cap) in enumerate(venues_raw)]
base_price = {"Concert":1500,"Conference":3000,"Workshop":800,"Sports":1000,"Festival":2000,"Theatre":700}
scale_days = {"Concert":16,"Conference":24,"Workshop":12,"Sports":10,"Festival":20,"Theatre":9}
show_up = {"Concert":.91,"Conference":.79,"Workshop":.86,"Sports":.87,"Festival":.81,"Theatre":.93}
org_for = {"Concert":[1,3],"Conference":[2],"Workshop":[6],"Sports":[4],"Festival":[3,1],"Theatre":[5]}
names = {"Concert":["Indie Nights","Rock Revival","Classical Evenings","Electro Pulse","Sufi Sunset","Jazz Under Stars"],
 "Conference":["DataCon","AI Summit","Startup Connect","CloudWorld Meet","Cyber Safe Forum","Product Leaders Day"],
 "Workshop":["Python for Analytics","Pottery Basics","Photography Masterclass","UX Design Sprint","Public Speaking Lab","SQL Bootcamp"],
 "Sports":["City Premier Cup","Kabaddi League Finals","Basketball Showdown","Badminton Open","Futsal Fest","Marathon Expo"],
 "Festival":["Food & Music Fest","Winter Carnival","Craft & Culture Mela","Film Fest","Beer & BBQ Fest","Lantern Festival"],
 "Theatre":["Midnight Play","Comedy Central Live","Shakespeare Reimagined","Musical Magic","Stand-up Special","Mystery at the Manor"]}
tt_def = [("Early Bird",0.7,0.30,0.80),("Standard",1.0,0.50,0.88),("VIP",2.2,0.20,0.96)]  # name, price x, qty share, show-up mod

# ---------- events (36 completed + 2 scheduled + ... ) ----------
events, ticket_types = [], []
eid = tid = 0
plan = []
for t in etypes:
    for k in range(6): plan.append((t, names[t][k]))
random.shuffle(plan)
dates = sorted(dt.date(2026,1,10) + dt.timedelta(days=int(i*(285/36))+random.randint(0,4)) for i in range(36))
for (t, nm), d in zip(plan, dates):
    eid += 1
    v = random.choice(venues)
    cap = int(v[3] * random.uniform(0.6, 1.0)) // 10 * 10
    price = int(base_price[t] * random.uniform(0.85, 1.25) // 50 * 50)
    events.append([eid, random.choice(org_for[t]), v[0], etypes.index(t)+1, f"{nm} {d.strftime('%b %Y')}",
                   d, "19:00:00" if t in ("Concert","Festival","Theatre") else "10:00:00", cap, "COMPLETED", t, price])
for nm_t, d in [("Concert","2026-12-12"),("Conference","2026-12-20")]:
    eid += 1
    v = random.choice(venues); cap = int(v[3]*0.9)//10*10
    events.append([eid, random.choice(org_for[nm_t]), v[0], etypes.index(nm_t)+1,
                   f"{random.choice(names[nm_t])} Dec 2026", dt.date.fromisoformat(d), "18:30:00", cap, "SCHEDULED", nm_t,
                   int(base_price[nm_t]*1.1//50*50)])
for e in events:
    for nm, mult, share, _ in tt_def:
        tid += 1
        ticket_types.append([tid, e[0], nm, int(e[10]*mult//10*10), max(1, int(e[7]*share)),
                             e[5]-dt.timedelta(days=60)])

# ---------- attendees ----------
first = "Aarav Vivaan Aditya Arjun Reyansh Ishaan Kabir Rohan Dev Karan Ananya Diya Saanvi Aadhya Myra Kiara Meera Riya Isha Navya Priya Sneha Pooja Neha Rahul Amit Vikram Sanjay Deepak".split()
last = "Sharma Verma Iyer Nair Reddy Patel Gupta Singh Mehta Rao Kapoor Joshi Das Bose Menon Pillai Shetty Kulkarni Chopra Malhotra".split()
cities = ["Bengaluru","Mumbai","Delhi","Hyderabad","Chennai","Kolkata","Pune"]
attendees = []
for i in range(1, 1201):
    n = f"{random.choice(first)} {random.choice(last)}"
    attendees.append((i, n, f"{n.lower().replace(' ','.')}{i}@mail.com", random.choice(cities)))

# ---------- bookings & check-ins ----------
bookings, checkins, bid, cid = [], [], 0, 0
tt_by_event = {}
for t in ticket_types: tt_by_event.setdefault(t[1], []).append(t)
popularity = {}
for e in events:
    pop = random.uniform(0.45, 1.15)
    popularity[e[0]] = pop
    ev_att = set(); sold_event = 0
    for t in tt_by_event[e[0]]:
        mod = {"Early Bird":(0.9,1.8),"Standard":(1.0,1.0),"VIP":(0.7,0.7)}[t[2]]
        target = int(t[4] * min(1.0, pop * mod[0] + random.uniform(-.05, .08)))
        sold = 0
        while sold < target:
            if sold_event >= e[7] or sold >= t[4]: break
            d = 99
            while d > 59: d = int(random.expovariate(1.0 / (scale_days[e[9]] * mod[1])))
            if e[8] == "SCHEDULED": d = max(d, (e[5] - dt.date(2026,11,18)).days)
            while True:
                a = random.randint(1, 1200)
                if a not in ev_att: ev_att.add(a); break
            booked = dt.datetime.combine(e[5] - dt.timedelta(days=d), dt.time(random.randint(8,22), random.randint(0,59), random.randint(0,59)))
            bid += 1
            cancelled = random.random() < 0.07
            if cancelled:
                cancel_at = booked + (dt.timedelta(days=random.randint(0, d-1), hours=random.randint(1, 20)) if d > 0
                                      else dt.timedelta(hours=random.randint(1, 3)))
                bookings.append((bid, a, t[0], booked.strftime("%Y-%m-%d %H:%M:%S"), "CANCELLED",
                                 cancel_at.strftime("%Y-%m-%d %H:%M:%S")))
            else:
                sold += 1; sold_event += 1
                bookings.append((bid, a, t[0], booked.strftime("%Y-%m-%d %H:%M:%S"), "CONFIRMED", None))
                if e[8] == "COMPLETED":
                    smod = dict((n, s) for n, _, _, s in tt_def)[t[2]] - 0.88
                    if random.random() < show_up[e[9]] + smod:
                        cid += 1
                        start = dt.datetime.combine(e[5], dt.time.fromisoformat(e[6]))
                        checkins.append((cid, bid, (start - dt.timedelta(minutes=random.randint(0, 90))).strftime("%Y-%m-%d %H:%M:%S")))

# ---------- feedback (MongoDB) ----------
qset = {"Concert":[("sound_quality","rating"),("artist_performance","rating"),("crowd_experience","rating"),("would_return","boolean")],
 "Conference":[("speaker_quality","rating"),("content_relevance","rating"),("networking_value","rating"),("food_and_beverage","rating")],
 "Workshop":[("instructor_clarity","rating"),("hands_on_value","rating"),("material_quality","rating"),("difficulty","choice")],
 "Sports":[("seating_view","rating"),("atmosphere","rating"),("concessions","rating"),("safety_arrangements","rating")],
 "Festival":[("lineup_quality","rating"),("food_stalls","rating"),("crowd_management","rating"),("value_for_money","rating")],
 "Theatre":[("acting","rating"),("stage_design","rating"),("seating_comfort","rating"),("story_rating","rating")]}
ev = {e[0]: e for e in events}
vn = {v[0]: v for v in venues}
ttev = {t[0]: t[1] for t in ticket_types}
vq = {v[0]: random.uniform(-0.5, 0.5) for v in venues}
eq = {e[0]: random.uniform(-0.6, 0.6) for e in events}
bk = {b[0]: b for b in bookings}
fb = []
for c in checkins:
    if random.random() > 0.32: continue
    b = bk[c[1]]; e = ev[ttev[b[2]]]
    lat = 3.9 + eq[e[0]] + vq[e[2]]
    r = lambda s=0.7: max(1, min(5, round(random.gauss(lat, s))))
    answers = []
    for qn, qt in qset[e[9]]:
        if qt == "rating": answers.append({"question": qn, "type": "rating", "value": r()})
        elif qt == "boolean": answers.append({"question": qn, "type": "boolean", "value": random.random() < lat/5.2})
        else: answers.append({"question": qn, "type": "choice", "value": random.choices(["Too easy","Just right","Too hard"], [.15,.65,.2])[0]})
    overall = r(0.6)
    doc = {"event_id": e[0], "event_name": e[4], "event_type": e[9], "venue_id": e[2], "venue_name": vn[e[2]][1],
           "city": vn[e[2]][2], "attendee_id": b[1], "booking_id": b[0],
           "submitted_at": (dt.datetime.combine(e[5], dt.time(23,0)) + dt.timedelta(hours=random.randint(1, 96))).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "overall_rating": overall, "nps_score": max(0, min(10, round(overall*2 + random.gauss(0, 1)))),
           "answers": answers}
    if random.random() < 0.4:
        doc["comment"] = random.choice(["Loved it!","Great organisation.","Entry queue was long.","Worth the price.","Sound could be better.","Would attend again.","Parking was a problem."])
    fb.append(doc)

# ---------- write ----------
with open("data.sql", "w") as f:
    f.write("-- EventHive sample data (synthetic, generated by generate_data.py, seed=42)\n")
    f.write("-- Load AFTER schema.sql.  Triggers are active, so every booking passes the overselling check.\nUSE eventhive;\nSET FOREIGN_KEY_CHECKS = 1;\n\n")
    f.write(insert("organisers", ["organiser_id","name","email","phone"], organisers))
    f.write(insert("venues", ["venue_id","venue_name","city","capacity"], venues))
    f.write(insert("event_types", ["event_type_id","type_name"], event_types))
    f.write(insert("events", ["event_id","organiser_id","venue_id","event_type_id","event_name","event_date","start_time","capacity","status"],
                   [e[:9] for e in events]))
    f.write(insert("ticket_types", ["ticket_type_id","event_id","tier_name","price","quantity_total","sale_start"], ticket_types))
    f.write(insert("attendees", ["attendee_id","full_name","email","city"], attendees))
    f.write(insert("bookings", ["booking_id","attendee_id","ticket_type_id","booked_at","status","cancelled_at"], bookings))
    f.write(insert("checkins", ["checkin_id","booking_id","checkin_time"], checkins))
json.dump(fb, open("mongodb/feedback.json", "w"), indent=1)
tot = len(organisers)+len(venues)+len(event_types)+len(events)+len(ticket_types)+len(attendees)+len(bookings)+len(checkins)
print(dict(events=len(events), ticket_types=len(ticket_types), attendees=len(attendees), bookings=len(bookings),
           checkins=len(checkins), feedback=len(fb), total_sql_rows=tot))
