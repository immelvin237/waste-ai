import os, json

try:
    import pg8000.native as pg
except ImportError:
    pg = None


def connect():
    return pg.Connection(
        user=os.environ["DB_USER"], password=os.environ["DB_PASS"],
        host=os.environ["DB_HOST"], database=os.environ["DB_NAME"], port=5432)


def ensure_table(conn):
    conn.run("""create table if not exists transactions (
        id serial primary key, local_id integer, timestamp text,
        class_detected text, confidence real, image_filename text)""")


def lambda_handler(event, context):
    route = event.get("routeKey", "")
    if route == "GET /health":
        return {"statusCode": 200, "body": json.dumps({"status": "ok"})}
    if pg is None:
        return {"statusCode": 500, "body": json.dumps({"error": "pg8000 layer missing"})}
    try:
        body = json.loads(event.get("body") or "{}")
        records = body.get("records", [])
        conn = connect()
        ensure_table(conn)
        for r in records:
            conn.run("insert into transactions (local_id, timestamp, class_detected, confidence, image_filename) "
                     "values (:l, :t, :c, :cf, :f)",
                     l=r.get("local_id"), t=r.get("timestamp"), c=r.get("class_detected"),
                     cf=r.get("confidence"), f=r.get("image_filename"))
        conn.close()
        return {"statusCode": 200, "body": json.dumps({"inserted": len(records)})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
