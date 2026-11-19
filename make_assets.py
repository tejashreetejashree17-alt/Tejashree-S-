import json, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from verify_sqlite import build, analytics
BLUE, GREEN, LBLUE, GREY = "#0062A9", "#07963A", "#E8F1F9", "#1F2937"

# ---------------- ER diagram ----------------
W, H, LH, TH = 112, 72, 3.1, 4.4
T = {  # name: (x, top, [(col, tag)])
 "organisers":  (1, 72, [("organiser_id","PK"),("name",""),("email","UQ"),("phone","")]),
 "venues":      (1, 40, [("venue_id","PK"),("venue_name",""),("city",""),("capacity","CK")]),
 "events":      (31, 62, [("event_id","PK"),("organiser_id","FK"),("venue_id","FK"),("event_type_id","FK"),("event_date",""),("capacity","CK"),("status","")]),
 "event_types": (61, 30, [("event_type_id","PK"),("type_name","UQ")]),
 "ticket_types":(61, 72, [("ticket_type_id","PK"),("event_id","FK"),("tier_name",""),("price","CK"),("quantity_total","CK")]),
 "attendees":   (90, 72, [("attendee_id","PK"),("full_name",""),("email","UQ"),("city","")]),
 "bookings":    (90, 44, [("booking_id","PK"),("attendee_id","FK"),("ticket_type_id","FK"),("booked_at",""),("status",""),("cancelled_at","")]),
 "checkins":    (90, 15.5, [("checkin_id","PK"),("booking_id","FK UQ"),("checkin_time","")]),
}
BW = 21.5
box = {}
fig, ax = plt.subplots(figsize=(11.2, 7.2)); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
for n, (x, top, cols) in T.items():
    h = TH + len(cols) * LH + 0.8; box[n] = (x, top, h)
    ax.add_patch(Rectangle((x, top - h), BW, h, fc=LBLUE, ec=BLUE, lw=1.6, zorder=2))
    ax.add_patch(Rectangle((x, top - TH), BW, TH, fc=BLUE, ec=BLUE, zorder=3))
    ax.text(x + BW/2, top - TH/2, n, color="white", ha="center", va="center", fontsize=14, fontweight="bold", zorder=4)
    for i, (c, tag) in enumerate(cols):
        y = top - TH - (i + .55) * LH
        col = GREEN if "FK" in tag else GREY
        ax.text(x + 1, y, c, fontsize=12, va="center", color=col, fontweight="bold" if tag.startswith("PK") else "normal", zorder=4)
        if tag: ax.text(x + BW - 1, y, tag, fontsize=10, va="center", ha="right", color=GREEN if "FK" in tag else "#6B7280", zorder=4)
def row_y(n, col):
    x, top, cols = T[n]; i = [c for c, _ in cols].index(col); return top - TH - (i + .55) * LH
def link(p, c, p1, c1, p2="", c2=""):
    ax.plot([p[0], c[0]], [p[1], c[1]], color=GREEN, lw=2, zorder=1)
    ax.text(p[0] + p1[0], p[1] + p1[1], "1", fontsize=13, fontweight="bold", color=GREEN, ha="center", va="center", bbox=dict(fc="white", ec="none", pad=1))
    ax.text(c[0] + c1[0], c[1] + c1[1], "N", fontsize=13, fontweight="bold", color=GREEN, ha="center", va="center", bbox=dict(fc="white", ec="none", pad=1))
E, O, V, ET, TT, A, B, C = (T[k][0] for k in ["events","organisers","venues","event_types","ticket_types","attendees","bookings","checkins"])
link((O+BW, row_y("organisers","organiser_id")), (E, row_y("events","organiser_id")), (2, 1.6), (-2, 1.6))
link((V+BW, row_y("venues","venue_id")), (E, row_y("events","venue_id")), (2, 1.6), (-2, 1.6))
link((ET, row_y("event_types","event_type_id")), (E+BW, row_y("events","event_type_id")), (-2, 1.6), (2, 1.6))
link((E+BW, row_y("events","event_id")), (TT, row_y("ticket_types","event_id")), (2, 1.6), (-2, 1.6))
link((TT+BW, row_y("ticket_types","ticket_type_id")), (B, row_y("bookings","ticket_type_id")), (2, 1.6), (-2, 1.6))
link((A+BW/2, 72-TH-4*LH-.8), (A+BW/2, 44), (1.8, -1.9), (1.8, 1.9))
link((B+BW/2, 44-TH-6*LH-.8), (B+BW/2, 15.5), (1.8, -1.9), (1.8, 1.9))
fig.savefig("charts/er_diagram.png", dpi=200, bbox_inches="tight", pad_inches=.05); plt.close(fig)

# ---------------- result-grid image (Q6) ----------------
con = build(); Q = analytics()
q6 = pd.read_sql(Q["Q6"].strip().rstrip(";"), con)
fig, ax = plt.subplots(figsize=(12.6, 3.3)); ax.axis("off")
ax.set_xlim(0, 12.6); ax.set_ylim(0, 3.3)
ax.text(.1, 3.05, "mysql> Q6. Ticket tier performance (completed events)", fontsize=17, family="monospace", color=BLUE, fontweight="bold", va="center")
xs = [0.1, 3.4, 6.6, 9.6]
heads = ["tier_name", "tickets_sold", "revenue (Rs)", "no_show_pct"]
for x, h in zip(xs, heads): ax.text(x, 2.35, h, fontsize=19, family="monospace", fontweight="bold", color=GREY, va="center")
ax.plot([0.05, 12.5], [2.05, 2.05], color=BLUE, lw=2)
for i, r in q6.iterrows():
    y = 1.6 - i * 0.6
    vals = [r.tier_name, f"{int(r.tickets_sold):,}", f"{int(r.revenue):,}", f"{r.no_show_pct:.1f}%"]
    for x, v in zip(xs, vals):
        ax.text(x, y, v, fontsize=19, family="monospace", va="center", color=GREEN if (v.endswith("%") and r.no_show_pct > 15) else GREY, fontweight="bold" if v.endswith("%") else "normal")
fig.savefig("charts/query_result.png", dpi=200, bbox_inches="tight", facecolor="#E8F1F9"); plt.close(fig)

# ---------------- MongoDB pipeline output (Aggregation 1, by event type) ----------------
fb = pd.DataFrame(json.load(open("mongodb/feedback.json")))
g = fb.groupby("event_type").agg(n=("overall_rating","size"), avg=("overall_rating","mean")).sort_values("avg")
fig, ax = plt.subplots(figsize=(7.2, 3.2))
bars = ax.barh(g.index, g["avg"], color=[GREEN if v == g["avg"].max() else BLUE for v in g["avg"]])
for y, (v, n) in enumerate(zip(g["avg"], g["n"])): ax.text(v + .04, y, f"{v:.2f}  (n={n})", va="center", fontsize=15, color=GREY)
ax.set_xlim(0, 5.6); ax.tick_params(labelsize=15); ax.set_xticks([])
for s in ("top","right","bottom"): ax.spines[s].set_visible(False)
ax.set_title("avg_rating by event_type (1 to 5)", fontsize=16, color=BLUE, loc="left")
fig.savefig("charts/mongo_pipeline_output.png", dpi=200, bbox_inches="tight", facecolor="white"); plt.close(fig)
print("assets ok")
