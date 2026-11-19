import json, sys, types
from verify_sqlite import build
nb = json.load(open("eventhive_analysis.ipynb"))
con = build()
# stand-in so the same cells run on the verification engine (SQLite is also DB-API 2.0)
fake = types.ModuleType("mysql.connector"); _m = types.ModuleType("mysql"); _m.connector = fake; sys.modules["mysql"] = _m; sys.modules["mysql.connector"] = fake
import matplotlib; matplotlib.use("Agg")
g = {"display": lambda x: print(x.to_string(index=False) if hasattr(x, "to_string") else x)}
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] != "code": continue
    src = "".join(c["source"])
    if "def get_connection" in src:
        fake.connect = lambda **k: con
        src = src.replace("SELECT VERSION()", "SELECT sqlite_version()")
    if "cur = conn.cursor()" in src and "%s" in src:   # MySQL-style placeholders: skip in sqlite check
        print("[skip DML cell: uses %s placeholders (MySQL driver)]"); continue
    src = src.replace("CURDATE()", "CURDATE()")
    exec(compile(src, f"cell{i}", "exec"), g)
    if "plt.show()" in src: pass
print("NOTEBOOK CHECK OK")
