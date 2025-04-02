import sqlite3

def connect_db():
    return sqlite3.connect('data.db')

def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    # Tabela de usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    # Tabela de permissões
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            user_id INTEGER PRIMARY KEY,
            can_access BOOLEAN,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Tabela de logs de acesso
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            attempt_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            allowed BOOLEAN,
            event_type TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()
