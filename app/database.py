import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS portfolio_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            card_name TEXT NOT NULL,
            qty INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            snap_date TEXT NOT NULL,
            value REAL NOT NULL,
            UNIQUE(user_id, snap_date)
        );
        CREATE TABLE IF NOT EXISTS box_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            card_name TEXT NOT NULL,
            box TEXT NOT NULL,
            slot TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS feed_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            profile TEXT NOT NULL,
            card_name TEXT NOT NULL,
            price REAL NOT NULL,
            UNIQUE(user_id, profile, card_name)
        );
        CREATE TABLE IF NOT EXISTS shared_decklists (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            decklist_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS power_certificates (
            id TEXT PRIMARY KEY,
            stats_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS trade_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_code TEXT NOT NULL,
            side TEXT NOT NULL,
            card_name TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()
