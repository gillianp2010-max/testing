import os
import sqlite3
import re
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template, request, jsonify
from data_generator import PRACTICES, SCHEMA_INFO, generate_all_databases

# ---------------------------------------------------------------------------
# VM-LOCAL DEPLOYMENT
# ---------------------------------------------------------------------------
# This app is designed to run ON each vet practice VM, not in a shared cloud.
# Data never leaves the VM. No external API calls, no AI services, no cloud upload.
#
# For DEMO mode (this Databricks deployment): SQLite databases are auto-generated.
# For PRODUCTION mode (on each VM): Replace run_query_on_db() below to connect
#   to the real database on that VM (SQL Server, PostgreSQL, MySQL, etc.)
#   using the appropriate Python driver (pyodbc, psycopg2, pymysql, etc.).
#   Keep the read-only connection flag to enforce SELECT-only at the DB level.
#
# BASELINE STORAGE: Saved to BASELINE_DIR on the VM's local disk.
#   Default: /opt/vet-sql-tester/baselines (production) or /tmp/vet_baselines (demo)
#   Change this path in the BASELINE_DIR variable below to control where
#   baseline snapshots are persisted. The install location determines the drive.
# ---------------------------------------------------------------------------

app = Flask(__name__)

DB_DIR = "/tmp/vet_dbs"

# Where baseline snapshots are stored on disk. On a VM this defaults to
# /opt/vet-sql-tester/baselines but can be overridden via environment variable.
BASELINE_DIR = os.environ.get("VET_BASELINE_DIR", "/tmp/vet_baselines")
os.makedirs(BASELINE_DIR, exist_ok=True)

# Keywords that are never allowed – defense in depth alongside read-only mode
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA", "VACUUM",
    "REINDEX", "GRANT", "REVOKE", "MERGE", "COMMIT", "ROLLBACK",
    "BEGIN", "SAVEPOINT", "RELEASE", "EXPLAIN",
]


def init_databases():
    """Generate all 10 databases on first startup (cached afterwards)."""
    existing = (
        [f for f in os.listdir(DB_DIR) if f.endswith(".db")]
        if os.path.exists(DB_DIR)
        else []
    )
    if len(existing) >= len(PRACTICES):
        print("Databases already present – skipping generation.")
        return
    print("Generating vet practice databases…")
    count = generate_all_databases(DB_DIR)
    print(f"Generated {count} databases in {DB_DIR}.")


def validate_query(user_input: str):
    """Prepend SELECT and reject anything that looks dangerous."""
    full_query = "SELECT " + user_input.strip()
    upper = full_query.upper()
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", upper):
            return (
                False,
                f"Blocked — '{kw}' is not permitted in this tool.\n\n"
                "Three layers of read-only protection:\n"
                "1. SELECT is hardcoded — the app prepends it for you.\n"
                f"2. Keyword filter — '{kw}' is in the blocked list (20+ keywords including INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, and more).\n"
                "3. Databases open in read-only mode — designed to prevent writes at the database level too.\n\n"
                "This tool is designed to keep data safe — modifications, deletions, and insertions are not supported.",
            )
    return True, full_query


def run_query_on_db(practice: dict, query: str) -> dict:
    """Execute *query* against a single practice database (read-only)."""
    db_path = os.path.join(DB_DIR, f"{practice['id']}.db")
    try:
        # Open in read-only mode – writes are physically impossible
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        start = time.time()
        cursor.execute(query)
        rows = cursor.fetchall()
        elapsed_ms = (time.time() - start) * 1000
        columns = (
            [desc[0] for desc in cursor.description]
            if cursor.description
            else []
        )
        data = [dict(r) for r in rows]
        conn.close()
        return {
            "practice_id": practice["id"],
            "practice_name": practice["name"],
            "city": practice["city"],
            "state": practice["state"],
            "columns": columns,
            "rows": data,
            "row_count": len(data),
            "execution_time_ms": round(elapsed_ms, 2),
            "error": None,
        }
    except Exception as exc:
        return {
            "practice_id": practice["id"],
            "practice_name": practice["name"],
            "city": practice["city"],
            "state": practice["state"],
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": 0,
            "error": str(exc),
        }


@app.route("/")
def index():
    return render_template(
        "index.html", practices=PRACTICES, schema=SCHEMA_INFO
    )


@app.route("/query", methods=["POST"])
def run_query():
    body = request.get_json(silent=True) or {}
    user_input = body.get("query", "").strip()
    if not user_input:
        return jsonify({"error": "Please enter a query after SELECT."}), 400

    ok, result = validate_query(user_input)
    if not ok:
        return jsonify({"error": result}), 400

    full_query = result

    # Support selective database querying
    selected = body.get("databases", [])
    if selected:
        targets = [p for p in PRACTICES if p["id"] in selected]
    else:
        targets = list(PRACTICES)
    if not targets:
        return jsonify({"error": "No databases selected."}), 400

    results = []
    with ThreadPoolExecutor(max_workers=len(targets)) as pool:
        futures = {
            pool.submit(run_query_on_db, p, full_query): p for p in targets
        }
        for fut in as_completed(futures):
            results.append(fut.result())

    results.sort(key=lambda r: r["practice_id"])
    total_ms = max((r["execution_time_ms"] for r in results), default=0)
    total_rows = sum(r["row_count"] for r in results)

    return jsonify({
        "query": full_query,
        "results": results,
        "total_databases": len(targets),
        "total_rows": total_rows,
        "total_time_ms": round(total_ms, 2),
    })


# ---- Baseline storage (server-side, on VM disk) ----

@app.route("/baseline/save", methods=["POST"])
def save_baseline():
    body = request.get_json(silent=True) or {}
    name = body.get("name", "").strip()
    data = body.get("data")
    if not name or not data:
        return jsonify({"error": "Provide name and data."}), 400
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    path = os.path.join(BASELINE_DIR, f"{safe_name}.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return jsonify({
        "status": "saved", "name": safe_name,
        "path": path, "size_bytes": os.path.getsize(path)})


@app.route("/baseline/load", methods=["GET"])
def load_baseline():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "Provide name."}), 400
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    path = os.path.join(BASELINE_DIR, f"{safe_name}.json")
    if not os.path.exists(path):
        return jsonify({"error": f"Baseline {safe_name} not found."}), 404
    with open(path, "r") as f:
        data = json.load(f)
    return jsonify({"name": safe_name, "data": data, "size_bytes": os.path.getsize(path)})


@app.route("/baseline/list", methods=["GET"])
def list_baselines():
    files = []
    if os.path.exists(BASELINE_DIR):
        for fn in sorted(os.listdir(BASELINE_DIR)):
            if fn.endswith(".json"):
                fp = os.path.join(BASELINE_DIR, fn)
                files.append({
                    "name": fn[:-5],
                    "size_bytes": os.path.getsize(fp),
                    "modified": os.path.getmtime(fp),
                })
    return jsonify({"baselines": files, "storage_dir": BASELINE_DIR})


@app.route("/baseline/delete", methods=["POST"])
def delete_baseline():
    body = request.get_json(silent=True) or {}
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"error": "Provide name."}), 400
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    path = os.path.join(BASELINE_DIR, f"{safe_name}.json")
    if not os.path.exists(path):
        return jsonify({"error": f"Baseline {safe_name} not found."}), 404
    os.remove(path)
    return jsonify({"status": "deleted", "name": safe_name})


@app.route("/baseline/delete-all", methods=["POST"])
def delete_all_baselines():
    count = 0
    freed_bytes = 0
    if os.path.exists(BASELINE_DIR):
        for fn in os.listdir(BASELINE_DIR):
            if fn.endswith(".json"):
                fp = os.path.join(BASELINE_DIR, fn)
                freed_bytes += os.path.getsize(fp)
                os.remove(fp)
                count += 1
    return jsonify({"status": "deleted", "count": count, "freed_bytes": freed_bytes})
# Generate databases before the first request
init_databases()

if __name__ == "__main__":
    port = int(os.environ.get("DATABRICKS_APP_PORT", 8000))
    app.run(host="0.0.0.0", port=port)
