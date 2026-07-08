import os, time, logging, sqlite3, signal
import requests
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "waste.db")
URL = os.getenv("AWS_API_URL", "").rstrip("/")
INTERVAL = int(os.getenv("SYNC_INTERVAL", "300"))
BATCH = 100

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    handlers=[logging.FileHandler(os.path.join(ROOT, "sync.log")),
                              logging.StreamHandler()])
log = logging.getLogger()
running = True


def stop(*_):
    global running
    running = False


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)


def online():
    if not URL:
        return False
    try:
        return requests.get(URL + "/health", timeout=5).status_code < 500
    except requests.RequestException:
        return False


def pending(conn):
    rows = conn.execute(
        "select id, timestamp, class_detected, confidence, image_filename "
        "from transactions where is_synced = 0 order by id limit ?", (BATCH,)).fetchall()
    return [{"local_id": r[0], "timestamp": r[1], "class_detected": r[2],
             "confidence": r[3], "image_filename": r[4]} for r in rows]


def push(batch):
    try:
        r = requests.post(URL + "/sync", json={"records": batch}, timeout=30)
        return 200 <= r.status_code < 300
    except requests.RequestException as e:
        log.info("post failed: %s", e)
        return False


def cycle():
    """Perform one synchronization cycle when configuration is available."""

    if not os.path.exists(DB):
        log.warning("Local database file is missing: %s", DB)
        return False

    if not URL:
        log.info(
            "Cloud synchronization disabled: AWS_API_URL is not configured. "
            "Local records remain stored in the database."
        )
        return True

    if not online():
        log.warning("Cloud synchronization postponed: API is offline or unreachable.")
        return False

    conn = sqlite3.connect(DB)

    try:
        total = 0

        while running:
            batch = pending(conn)

            if not batch:
                break

            if not push(batch):
                return False

            conn.executemany(
                "UPDATE transactions SET is_synced = 1 WHERE id = ?",
                [(item["local_id"],) for item in batch],
            )
            conn.commit()

            total += len(batch)
            log.info("Synchronized %d record(s).", len(batch))

        if total == 0:
            log.info("No pending local records to synchronize.")

        return True

    finally:
        conn.close()

def main():
    if not os.path.exists(DB):
        log.warning("Local database file is missing: %s", DB)
        log.warning("Start the local application first so it can create waste.db.")

    if not URL:
        log.info("Cloud synchronization is disabled because AWS_API_URL is empty.")
        log.info("Local classification and local database storage will still work.")
        return

    log.info(
        "Sync worker started (url=%s interval=%ds)",
        URL,
        INTERVAL,
    )

    backoff = INTERVAL

    while running:
        success = cycle()
        backoff = INTERVAL if success else min(backoff * 2, 3600)

        for _ in range(backoff):
            if not running:
                break
            time.sleep(1)

    log.info("Stopped")    
if __name__ == "__main__":
    main()
