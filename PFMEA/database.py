import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "data" / "pfmea_database.db"

def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)

def initialize_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pfmea_records (
                id                          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at                  TEXT    NOT NULL,
                status                      TEXT    NOT NULL DEFAULT '洗い出し中',
                industry                    TEXT    NOT NULL,
                product                     TEXT    NOT NULL,
                process                     TEXT    NOT NULL,
                gate_type                   TEXT,
                has_insert                  INTEGER,
                failure_mode                TEXT    NOT NULL,
                effect                      TEXT    NOT NULL,
                cause                       TEXT    NOT NULL,
                current_control_prevention  TEXT    NOT NULL,
                current_control_detection   TEXT    NOT NULL,
                recommended_action          TEXT    NOT NULL,
                severity                    INTEGER NOT NULL,
                occurrence                  INTEGER NOT NULL,
                detection                   INTEGER NOT NULL,
                rpn                         INTEGER NOT NULL,
                remarks                     TEXT
            )
        """)
        conn.commit()

def insert_records(records: list[dict]) -> int:
    """
    records: parse済み・評点入力済みのレコードリスト
    戻り値: 登録件数
    """
    now = datetime.now().isoformat()
    rows = []
    for r in records:
        rows.append((
            now,
            "洗い出し中",
            r["industry"],
            r["product"],
            r["process"],
            r.get("gate_type"),
            r.get("has_insert"),
            r["failure_mode"],
            r["effect"],
            r["cause"],
            r["current_control_prevention"],
            r["current_control_detection"],
            r["recommended_action"],
            r["severity"],
            r["occurrence"],
            r["detection"],
            r["severity"] * r["occurrence"] * r["detection"],
            r.get("remarks", "")
        ))
    with get_connection() as conn:
        conn.executemany("""
            INSERT INTO pfmea_records (
                created_at, status, industry, product, process,
                gate_type, has_insert,
                failure_mode, effect, cause,
                current_control_prevention, current_control_detection,
                recommended_action, severity, occurrence, detection, rpn, remarks
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
    return len(rows)

def fetch_records(
    industry: str = None,
    product: str = None,
    process: str = None,
    status: str = None,
    keyword: str = None
) -> list[dict]:
    """
    フィルタ条件に合致するレコードを返す
    """
    query = "SELECT * FROM pfmea_records WHERE 1=1"
    params = []
    if industry:
        query += " AND industry = ?"
        params.append(industry)
    if product:
        query += " AND product LIKE ?"
        params.append(f"%{product}%")
    if process:
        query += " AND process = ?"
        params.append(process)
    if status and status != "全て":
        query += " AND status = ?"
        params.append(status)
    if keyword:
        query += " AND failure_mode LIKE ?"
        params.append(f"%{keyword}%")
    query += " ORDER BY id ASC"

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]

def update_record(record_id: int, updated: dict):
    """
    アプリBからの編集・承認を反映する
    updated: 更新するカラムと値のdict
    """
    if not updated:
        return
    set_clause = ", ".join([f"{k} = ?" for k in updated.keys()])
    values = list(updated.values()) + [record_id]
    with get_connection() as conn:
        conn.execute(
            f"UPDATE pfmea_records SET {set_clause} WHERE id = ?",
            values
        )
        conn.commit()

def approve_records(record_ids: list[int]):
    """
    指定IDのステータスを承認済みに変更する
    """
    with get_connection() as conn:
        conn.executemany(
            "UPDATE pfmea_records SET status = '承認済み' WHERE id = ?",
            [(rid,) for rid in record_ids]
        )
        conn.commit()
