from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from db_setup import create_tables, connect_db
from pubsub import AsyncConn
import pandas as pd

app = Flask(__name__)
app.secret_key = "SEGREDO"

pubnub = AsyncConn("FlaskApplication", "meu_canal")
create_tables()

def _get_all_users():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users")
        return cursor.fetchall()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()

        if row:
            user_id = row[0]
            hashed_password = row[1]
            if check_password_hash(hashed_password, password):
                session['user_id'] = user_id
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="Senha incorreta")
        else:
            return render_template('login.html', error="Usuário não encontrado")
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/')
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/users', methods=['GET', 'POST'])
def users():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = request.form['id']  # ID do cartão
        username = request.form['username']
        password = request.form['password']
        hashed = generate_password_hash(password)

        with connect_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (id, username, password) VALUES (?, ?, ?)",
                               (user_id, username, hashed))
                conn.commit()
            except Exception as e:
                return render_template('users.html', error=str(e), users=_get_all_users())
        return redirect(url_for('users'))
    else:
        return render_template('users.html', users=_get_all_users())

@app.route('/users/delete/<int:uid>')
def delete_user(uid):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.commit()
    return redirect(url_for('users'))

@app.route('/users/edit/<int:uid>', methods=['GET', 'POST'])
def edit_user(uid):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_username = request.form['username']
        new_password = request.form['password']
        hashed = generate_password_hash(new_password)

        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET username = ?, password = ? WHERE id = ?",
                           (new_username, hashed, uid))
            conn.commit()
        return redirect(url_for('users'))
    else:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username FROM users WHERE id = ?", (uid,))
            row = cursor.fetchone()
        return render_template('users.html', edit_user=row, users=_get_all_users())

@app.route('/permissions', methods=['GET', 'POST'])
def permissions():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = request.form['user_id']
        can_access = request.form.get('can_access') == 'on'
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO permissions (user_id, can_access)
                VALUES (?, ?)
            """, (user_id, 1 if can_access else 0))
            conn.commit()
        return redirect(url_for('permissions'))
    else:
        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.id, u.username, COALESCE(p.can_access, 0)
                FROM users u
                LEFT JOIN permissions p ON u.id = p.user_id
            """)
            rows = cursor.fetchall()
        return render_template('permissions.html', data=rows)

@app.route('/permissions/toggle/<int:uid>')
def toggle_permission(uid):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT can_access FROM permissions WHERE user_id = ?", (uid,))
        row = cursor.fetchone()
        if row:
            new_val = 0 if row[0] == 1 else 1
            cursor.execute("UPDATE permissions SET can_access=? WHERE user_id=?", (new_val, uid))
        else:
            cursor.execute("INSERT INTO permissions (user_id, can_access) VALUES (?, 1)", (uid,))
        conn.commit()
    return redirect(url_for('permissions'))

# =============================
#   ROTA /access (IMPORTANTE)
# =============================
@app.route('/access', methods=['POST'])
def register_access():
    """
    Recebe JSON como {"user_id": <int>, "event_type": "entry" ou "exit"}
    e registra no access_logs. Se 'entry', checa permissão. Se 'exit', libera.
    """
    data = request.json
    user_id = data.get('user_id')
    event_type = data.get('event_type', 'entry')

    if not user_id:
        return jsonify({"error": "User ID não informado"}), 400

    with connect_db() as conn:
        cursor = conn.cursor()

        if event_type == 'entry':
            # Verifica se tem permissão
            cursor.execute("SELECT can_access FROM permissions WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            allowed = bool(row[0]) if row else False
        elif event_type == 'exit':
            # Vamos permitir saída (outra lógica se quiser)
            allowed = True
        else:
            # Caso algum outro event_type
            allowed = False

        cursor.execute("""
            INSERT INTO access_logs (user_id, allowed, event_type)
            VALUES (?, ?, ?)
        """, (user_id, int(allowed), event_type))
        conn.commit()

    # PubNub
    msg = f"Acesso {event_type} - {'permitido' if allowed else 'negado'}"
    pubnub.publish({"user_id": user_id, "message": msg})

    return jsonify({
        "user_id": user_id,
        "event_type": event_type,
        "allowed": allowed
    }), 201

@app.route('/logs')
def show_logs():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT l.id, u.username, l.attempt_time, l.event_type, l.allowed
            FROM access_logs l
            LEFT JOIN users u ON l.user_id = u.id
            ORDER BY l.attempt_time DESC
        """)
        rows = cursor.fetchall()
    return render_template('logs.html', logs=rows)

# =============================
#     MONITOR (PubNub)
# =============================
@app.route('/monitor')
def monitor():
    return app.send_static_file('monitor.html')

# =============================
#   ANÁLISE COM PANDAS
# =============================
@app.route('/analysis')
def analysis():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = connect_db()
    df = pd.read_sql_query("SELECT * FROM access_logs", conn)
    conn.close()

    if df.empty:
        return render_template('analysis.html',
                               daily_list=[],
                               hours_list=[],
                               user_hours=[],
                               no_data=True)

    df['attempt_time'] = pd.to_datetime(df['attempt_time'])
    df['date'] = df['attempt_time'].dt.date

    # Entradas/Saídas por dia
    group_daily = df.groupby(['date', 'event_type'])['id'].count().reset_index()
    group_daily.columns = ['date', 'event_type', 'count']

    # Horas dentro da sala => precisa allowed=1 e event_type=entry/exit
    df_allowed = df[df['allowed'] == 1].copy()
    df_allowed.sort_values(['user_id', 'attempt_time'], inplace=True)

    time_data = []
    for uid, subset in df_allowed.groupby('user_id'):
        subset = subset.reset_index(drop=True)
        entry_time = None
        for i, row in subset.iterrows():
            if row['event_type'] == 'entry':
                entry_time = row['attempt_time']
            elif row['event_type'] == 'exit' and entry_time is not None:
                delta = row['attempt_time'] - entry_time
                time_data.append({
                    'user_id': uid,
                    'entry_time': entry_time,
                    'exit_time': row['attempt_time'],
                    'time_spent_hours': delta.total_seconds() / 3600.0
                })
                entry_time = None

    df_time = pd.DataFrame(time_data, columns=['user_id', 'entry_time', 'exit_time', 'time_spent_hours'])
    if df_time.empty:
        df_sum = pd.DataFrame(columns=['user_id', 'total_hours'])
    else:
        df_sum = df_time.groupby('user_id')['time_spent_hours'].sum().reset_index()
        df_sum.columns = ['user_id', 'total_hours']

    daily_list = group_daily.to_dict('records')
    hours_list = df_sum.to_dict('records')

    # Filtro: /analysis?user_id=XYZ
    user_id_str = request.args.get('user_id')
    user_hours = []
    if user_id_str and user_id_str.isdigit():
        wanted_uid = int(user_id_str)
        df_user = df_time[df_time['user_id'] == wanted_uid].copy()
        if not df_user.empty:
            # Soma diária ou total
            # Por dia:
            # group_user = df_user.groupby(df_user['entry_time'].dt.date)['time_spent_hours'].sum().reset_index()
            # user_hours = group_user.to_dict('records')
            # Ou total
            total_h = df_user['time_spent_hours'].sum()
            user_hours.append({"user_id": wanted_uid, "total_hours": total_h})

    return render_template('analysis.html',
                           daily_list=daily_list,
                           hours_list=hours_list,
                           user_hours=user_hours,
                           no_data=False)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
