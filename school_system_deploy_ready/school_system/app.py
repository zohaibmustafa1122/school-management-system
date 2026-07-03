from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, flash, Response)
import sqlite3, hashlib, csv, io, os
from datetime import datetime, date, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'jphs_secret_2024_xyz')
DB_PATH = os.environ.get('DB_PATH', 'school.db')
SCHOOL_NAME = 'Jamil Public High School'
SCHOOL_SHORT = 'JPHS'

# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE
# ══════════════════════════════════════════════════════════════════════════════
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def rows_to_dicts(rows):
    return [dict(r) for r in rows]

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    conn = get_db(); c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        plain_password TEXT,
        role TEXT NOT NULL CHECK(role IN ('admin','teacher','student')),
        full_name TEXT,
        student_id INTEGER,
        class_assigned TEXT
    )''')
    # Migrate: add plain_password column if it doesn't exist yet
    try:
        c.execute("ALTER TABLE users ADD COLUMN plain_password TEXT")
    except: pass
    c.execute('''CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        section TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        roll_number TEXT NOT NULL,
        class TEXT NOT NULL,
        parent_phone TEXT
    )''')
    try: c.execute("ALTER TABLE students ADD COLUMN parent_phone TEXT")
    except: pass
    c.execute('''CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT NOT NULL,
        class TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        exam_type TEXT NOT NULL,
        marks_obtained REAL NOT NULL,
        total_marks REAL NOT NULL DEFAULT 100,
        date TEXT NOT NULL,
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
        UNIQUE(student_id, subject_id, exam_type)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Present','Absent')),
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
        UNIQUE(student_id, date)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS fees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        month TEXT NOT NULL,
        total_amount REAL NOT NULL,
        paid_amount REAL NOT NULL DEFAULT 0,
        due_date TEXT,
        status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Paid','Partial','Pending')),
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS diary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('Assignment','Announcement','Assessment','Homework')),
        due_date TEXT,
        created_by INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(created_by) REFERENCES users(id)
    )''')

    c.execute("INSERT OR IGNORE INTO users (username,password,plain_password,role,full_name) VALUES (?,?,?,?,?)",
              ('admin', hash_pw('admin123'), 'admin123', 'admin', 'Administrator'))
    teachers = [('teacher1','teacher123','Mrs. Ayesha Khan','10-A'),
                ('teacher2','teacher123','Mr. Bilal Raza','10-B'),
                ('teacher3','teacher123','Ms. Sara Malik','9-A')]
    for u,p,name,cls in teachers:
        c.execute("INSERT OR IGNORE INTO users (username,password,plain_password,role,full_name,class_assigned) VALUES (?,?,?,?,?,?)",
                  (u, hash_pw(p), p, 'teacher', name, cls))

    # ── Seed classes ──
    for cls_name in ['10-A','10-B','9-A']:
        c.execute("INSERT OR IGNORE INTO classes (name) VALUES (?)", (cls_name,))

    sample_students = [
        ('Ahmed Khan','001','10-A'), ('Fatima Malik','002','10-A'),
        ('Zaid Hassan','003','10-A'), ('Sara Iqbal','004','10-A'),
        ('Omar Butt','005','10-A'), ('Nadia Javed','006','10-A'),
        ('Ayesha Noor','007','10-B'), ('Ali Raza','008','10-B'),
        ('Hina Shah','009','10-B'), ('Bilal Ahmed','010','10-B'),
        ('Hassan Mirza','011','9-A'), ('Sana Tariq','012','9-A'),
        ('Kamran Ali','013','9-A'), ('Rabia Qureshi','014','9-A'),
    ]
    for name,roll,cls in sample_students:
        c.execute("INSERT OR IGNORE INTO students (name,roll_number,class) VALUES (?,?,?)", (name,roll,cls))
    conn.commit()

    stds = conn.execute("SELECT * FROM students").fetchall()
    for s in stds:
        uname = 'student_' + s['roll_number']
        c.execute("INSERT OR IGNORE INTO users (username,password,plain_password,role,full_name,student_id) VALUES (?,?,?,?,?,?)",
                  (uname, hash_pw('student123'), 'student123', 'student', s['name'], s['id']))

    subjects = [
        ('Mathematics','10-A'),('English','10-A'),('Physics','10-A'),('Chemistry','10-A'),('Biology','10-A'),
        ('Mathematics','10-B'),('English','10-B'),('Physics','10-B'),('Urdu','10-B'),
        ('Mathematics','9-A'),('English','9-A'),('Science','9-A'),('Urdu','9-A'),
    ]
    for sub,cls in subjects:
        c.execute("INSERT OR IGNORE INTO subjects (subject_name,class) VALUES (?,?)", (sub,cls))

    import random; random.seed(42)
    stds = conn.execute("SELECT * FROM students").fetchall()
    for s in stds:
        subs = conn.execute("SELECT * FROM subjects WHERE class=?", (s['class'],)).fetchall()
        for sub in subs:
            for et in ['Midterm','Final']:
                total = 100
                obtained = round(random.uniform(0.45*total, total), 1)
                try:
                    c.execute("INSERT OR IGNORE INTO marks (student_id,subject_id,exam_type,marks_obtained,total_marks,date) VALUES (?,?,?,?,?,?)",
                              (s['id'], sub['id'], et, obtained, total, '2024-11-15'))
                except: pass

    base = date(2024,11,1)
    for s in stds:
        for i in range(20):
            d = (base + timedelta(days=i)).isoformat()
            status = 'Present' if random.random() > 0.2 else 'Absent'
            try:
                c.execute("INSERT OR IGNORE INTO attendance (student_id,date,status) VALUES (?,?,?)",
                          (s['id'], d, status))
            except: pass

    admin_id = conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()['id']
    diary_entries = [
        ('10-A','Math Assignment','Solve exercises 5.1 to 5.3 from textbook.','Assignment','2024-11-20'),
        ('10-A','PTM Announcement','Parent-Teacher Meeting on Saturday 10am.','Announcement',None),
        ('10-B','English Essay','Write a 300-word essay on Climate Change.','Assignment','2024-11-22'),
        ('9-A','Science Quiz','Quiz on Chapter 4 - Cells and Tissues.','Assessment','2024-11-18'),
    ]
    for cls,title,content,typ,due in diary_entries:
        c.execute("INSERT OR IGNORE INTO diary (class,title,content,type,due_date,created_by,created_at) VALUES (?,?,?,?,?,?,?)",
                  (cls,title,content,typ,due,admin_id,'2024-11-14 09:00:00'))

    # ── Seed fees ──
    import random as _rand; _rand.seed(99)
    all_stds = conn.execute("SELECT id FROM students").fetchall()
    months = ['2024-09','2024-10','2024-11','2024-12']
    for s in all_stds:
        for mo in months:
            total = 2500
            paid = _rand.choice([0, 1250, 2500])
            status = 'Paid' if paid>=total else ('Partial' if paid>0 else 'Pending')
            try:
                c.execute("INSERT OR IGNORE INTO fees (student_id,month,total_amount,paid_amount,status,due_date) VALUES (?,?,?,?,?,?)",
                          (s['id'], mo, total, paid, status, mo+'-10'))
            except: pass

    conn.commit(); conn.close()

# ══════════════════════════════════════════════════════════════════════════════
#  AUTH HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*a, **kw)
    return dec

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def dec(*a, **kw):
            if session.get('role') not in roles:
                flash('Access denied.', 'error'); return redirect(url_for('dashboard'))
            return f(*a, **kw)
        return dec
    return decorator

@app.context_processor
def inject_globals():
    return {'now': datetime.now(), 'school_name': SCHOOL_NAME, 'school_short': SCHOOL_SHORT}

def get_grade(pct):
    if pct >= 80: return 'A'
    if pct >= 60: return 'B'
    if pct >= 40: return 'C'
    return 'F'

# ══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/', methods=['GET','POST'])
def login():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        u = request.form.get('username','').strip()
        p = request.form.get('password','').strip()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?",
                            (u, hash_pw(p))).fetchone()
        conn.close()
        if user:
            session.update({'user_id':user['id'],'username':user['username'],
                           'role':user['role'],'full_name':user['full_name'],
                           'student_id':user['student_id'],'class_assigned':user['class_assigned']})
            return redirect(url_for('dashboard'))
        error = 'Invalid username or password.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    role = session['role']

    if role == 'student':
        sid = session['student_id']
        student = dict(conn.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone())
        total_days = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id=?", (sid,)).fetchone()[0]
        present = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='Present'", (sid,)).fetchone()[0]
        att_pct = round(present/total_days*100,1) if total_days else 0
        marks_data = rows_to_dicts(conn.execute("""
            SELECT s.subject_name, m.exam_type, m.marks_obtained, m.total_marks
            FROM marks m JOIN subjects s ON m.subject_id=s.id
            WHERE m.student_id=? ORDER BY s.subject_name
        """, (sid,)).fetchall())
        avg_pct = round(sum(m['marks_obtained']/m['total_marks']*100 for m in marks_data)/len(marks_data),1) if marks_data else 0
        diary = rows_to_dicts(conn.execute("SELECT * FROM diary WHERE class=? ORDER BY created_at DESC LIMIT 5", (student['class'],)).fetchall())
        subj_perf = rows_to_dicts(conn.execute("""
            SELECT s.subject_name, AVG(m.marks_obtained/m.total_marks*100) as avg_pct
            FROM marks m JOIN subjects s ON m.subject_id=s.id
            WHERE m.student_id=? GROUP BY s.subject_name
        """, (sid,)).fetchall())
        conn.close()
        return render_template('dashboard_student.html',
            student=student, att_pct=att_pct, present=present,
            total_days=total_days, avg_pct=avg_pct, diary=diary,
            subj_perf=subj_perf, marks_count=len(marks_data))

    elif role == 'teacher':
        cls = session.get('class_assigned','')
        total_students = conn.execute("SELECT COUNT(*) FROM students WHERE class=?", (cls,)).fetchone()[0]
        total_days = conn.execute("SELECT COUNT(DISTINCT date) FROM attendance").fetchone()[0]
        if total_days and total_students:
            present = conn.execute("""SELECT COUNT(*) FROM attendance a JOIN students s ON a.student_id=s.id
                WHERE s.class=? AND a.status='Present'""", (cls,)).fetchone()[0]
            avg_att = round(present/(total_days*total_students)*100,1)
        else: avg_att = 0
        students = conn.execute("SELECT * FROM students WHERE class=?", (cls,)).fetchall()
        low_att = []
        for s in students:
            td = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id=?", (s['id'],)).fetchone()[0]
            pr = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='Present'", (s['id'],)).fetchone()[0]
            pct = round(pr/td*100,1) if td else 0
            if pct < 75: low_att.append({'name':s['name'],'roll':s['roll_number'],'pct':pct})
        diary = rows_to_dicts(conn.execute("SELECT * FROM diary WHERE class=? ORDER BY created_at DESC LIMIT 3", (cls,)).fetchall())
        subj_avgs = rows_to_dicts(conn.execute("""
            SELECT sub.subject_name, AVG(m.marks_obtained/m.total_marks*100) as avg_pct
            FROM marks m JOIN subjects sub ON m.subject_id=sub.id
            JOIN students s ON m.student_id=s.id WHERE s.class=?
            GROUP BY sub.subject_name
        """, (cls,)).fetchall())
        conn.close()
        return render_template('dashboard_teacher.html',
            cls=cls, total_students=total_students, avg_att=avg_att,
            low_att=low_att, diary=diary, subj_avgs=subj_avgs)

    else:  # admin
        total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        total_teachers = conn.execute("SELECT COUNT(*) FROM users WHERE role='teacher'").fetchone()[0]
        classes = conn.execute("SELECT DISTINCT class FROM students ORDER BY class").fetchall()
        class_stats = []
        for c in classes:
            cls = c['class']
            cnt = conn.execute("SELECT COUNT(*) FROM students WHERE class=?", (cls,)).fetchone()[0]
            avg_m = conn.execute("""SELECT AVG(m.marks_obtained/m.total_marks*100)
                FROM marks m JOIN students s ON m.student_id=s.id WHERE s.class=?""", (cls,)).fetchone()[0]
            avg_m = round(avg_m,1) if avg_m else 0
            td = conn.execute("SELECT COUNT(DISTINCT date) FROM attendance").fetchone()[0]
            if td and cnt:
                pr = conn.execute("""SELECT COUNT(*) FROM attendance a JOIN students s ON a.student_id=s.id
                    WHERE s.class=? AND a.status='Present'""", (cls,)).fetchone()[0]
                avg_a = round(pr/(td*cnt)*100,1)
            else: avg_a = 0
            class_stats.append({'class':cls,'students':cnt,'avg_marks':avg_m,'avg_att':avg_a})
        conn.close()
        return render_template('dashboard_admin.html',
            total_students=total_students, total_teachers=total_teachers, class_stats=class_stats)

# ══════════════════════════════════════════════════════════════════════════════
#  USER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/users')
@login_required
@role_required('admin')
def users():
    conn = get_db()
    all_users = rows_to_dicts(conn.execute(
        "SELECT u.*, s.name as sname, s.class as sclass FROM users u LEFT JOIN students s ON u.student_id=s.id ORDER BY u.role, u.username"
    ).fetchall())
    # Ensure plain_password key exists
    for u in all_users:
        if 'plain_password' not in u: u['plain_password'] = None
    classes = rows_to_dicts(conn.execute("SELECT DISTINCT class FROM students ORDER BY class").fetchall())
    students_unlinked = rows_to_dicts(conn.execute("SELECT * FROM students ORDER BY class, name").fetchall())
    conn.close()
    return render_template('users.html', users=all_users, classes=classes, students_unlinked=students_unlinked)

@app.route('/users/add', methods=['POST'])
@login_required
@role_required('admin')
def add_user():
    u = request.form.get('username','').strip()
    p = request.form.get('password','').strip()
    role = request.form.get('role','').strip()
    name = request.form.get('full_name','').strip()
    cls = request.form.get('class_assigned','').strip()
    sid = request.form.get('student_id','').strip() or None
    if not all([u,p,role,name]):
        flash('All fields required.','error'); return redirect(url_for('users'))
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username,password,plain_password,role,full_name,class_assigned,student_id) VALUES (?,?,?,?,?,?,?)",
                     (u, hash_pw(p), p, role, name, cls or None, sid))
        conn.commit()
        flash(f'User "{u}" created successfully.','success')
    except sqlite3.IntegrityError:
        flash('Username already exists.','error')
    conn.close()
    return redirect(url_for('users'))

@app.route('/users/edit/<int:uid>', methods=['POST'])
@login_required
@role_required('admin')
def edit_user(uid):
    name = request.form.get('full_name','').strip()
    cls = request.form.get('class_assigned','').strip()
    new_pw = request.form.get('new_password','').strip()
    conn = get_db()
    if new_pw:
        conn.execute("UPDATE users SET full_name=?,class_assigned=?,password=?,plain_password=? WHERE id=?",
                     (name, cls or None, hash_pw(new_pw), new_pw, uid))
    else:
        conn.execute("UPDATE users SET full_name=?,class_assigned=? WHERE id=?",
                     (name, cls or None, uid))
    conn.commit(); conn.close()
    flash('User updated.','success')
    return redirect(url_for('users'))

@app.route('/users/delete/<int:uid>', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(uid):
    if uid == session['user_id']:
        flash("Cannot delete your own account.",'error'); return redirect(url_for('users'))
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit(); conn.close()
    flash('User deleted.','success')
    return redirect(url_for('users'))

# ══════════════════════════════════════════════════════════════════════════════
#  STUDENTS
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/students')
@login_required
@role_required('admin','teacher')
def students():
    search = request.args.get('q','')
    conn = get_db()
    role = session['role']
    cls_filter = session.get('class_assigned','') if role == 'teacher' else request.args.get('class','')
    q = f"%{search}%"
    if cls_filter:
        rows = rows_to_dicts(conn.execute(
            "SELECT * FROM students WHERE class=? AND (name LIKE ? OR roll_number LIKE ?) ORDER BY roll_number",
            (cls_filter, q, q)).fetchall())
    else:
        rows = rows_to_dicts(conn.execute(
            "SELECT * FROM students WHERE name LIKE ? OR roll_number LIKE ? OR class LIKE ? ORDER BY class,roll_number",
            (q, q, q)).fetchall())
    classes = rows_to_dicts(conn.execute("SELECT DISTINCT class FROM students ORDER BY class").fetchall())
    conn.close()
    return render_template('students.html', students=rows, search=search, classes=classes, cls_filter=cls_filter)

@app.route('/students/add', methods=['POST'])
@login_required
@role_required('admin','teacher')
def add_student():
    name  = request.form.get('name','').strip()
    roll  = request.form.get('roll_number','').strip()
    cls   = request.form.get('class','').strip()
    phone = request.form.get('parent_phone','').strip()
    if not all([name,roll,cls]):
        flash('All fields required.','error'); return redirect(url_for('students'))
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO students (name,roll_number,class,parent_phone) VALUES (?,?,?,?)", (name,roll,cls,phone or None))
    sid = c.lastrowid
    uname = 'student_' + roll
    try:
        c.execute("INSERT OR IGNORE INTO users (username,password,plain_password,role,full_name,student_id) VALUES (?,?,?,?,?,?)",
                  (uname, hash_pw('student123'), 'student123', 'student', name, sid))
    except: pass
    conn.commit(); conn.close()
    flash(f'Student "{name}" added. Login: {uname} / student123','success')
    return redirect(url_for('students'))

@app.route('/students/edit/<int:sid>', methods=['POST'])
@login_required
@role_required('admin','teacher')
def edit_student(sid):
    name  = request.form.get('name','').strip()
    roll  = request.form.get('roll_number','').strip()
    cls   = request.form.get('class','').strip()
    phone = request.form.get('parent_phone','').strip()
    conn = get_db()
    conn.execute("UPDATE students SET name=?,roll_number=?,class=?,parent_phone=? WHERE id=?", (name,roll,cls,phone or None,sid))
    conn.execute("UPDATE users SET full_name=? WHERE student_id=?", (name,sid))
    conn.commit(); conn.close()
    flash('Student updated.','success')
    return redirect(url_for('students'))

@app.route('/students/delete/<int:sid>', methods=['POST'])
@login_required
@role_required('admin','teacher')
def delete_student(sid):
    conn = get_db()
    conn.execute("DELETE FROM students WHERE id=?", (sid,))
    conn.commit(); conn.close()
    flash('Student deleted.','success')
    return redirect(url_for('students'))

# ══════════════════════════════════════════════════════════════════════════════
#  SUBJECTS
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/subjects')
@login_required
@role_required('admin','teacher')
def subjects():
    conn = get_db()
    cls_filter = session.get('class_assigned','') if session['role']=='teacher' else request.args.get('class','')
    if cls_filter:
        subs = rows_to_dicts(conn.execute("SELECT * FROM subjects WHERE class=? ORDER BY class,subject_name", (cls_filter,)).fetchall())
    else:
        subs = rows_to_dicts(conn.execute("SELECT * FROM subjects ORDER BY class,subject_name").fetchall())
    classes = rows_to_dicts(conn.execute("SELECT DISTINCT class FROM students ORDER BY class").fetchall())
    conn.close()
    return render_template('subjects.html', subjects=subs, classes=classes, cls_filter=cls_filter)

@app.route('/subjects/add', methods=['POST'])
@login_required
@role_required('admin','teacher')
def add_subject():
    name = request.form.get('subject_name','').strip()
    cls  = request.form.get('class','').strip()
    if not all([name,cls]):
        flash('All fields required.','error'); return redirect(url_for('subjects'))
    conn = get_db()
    try:
        conn.execute("INSERT INTO subjects (subject_name,class) VALUES (?,?)", (name,cls))
        conn.commit()
        flash(f'Subject "{name}" added to class {cls}.','success')
    except: flash('Subject may already exist.','error')
    conn.close()
    return redirect(url_for('subjects'))

@app.route('/subjects/edit/<int:sub_id>', methods=['POST'])
@login_required
@role_required('admin','teacher')
def edit_subject(sub_id):
    name = request.form.get('subject_name','').strip()
    cls  = request.form.get('class','').strip()
    conn = get_db()
    conn.execute("UPDATE subjects SET subject_name=?,class=? WHERE id=?", (name,cls,sub_id))
    conn.commit(); conn.close()
    flash('Subject updated.','success')
    return redirect(url_for('subjects'))

@app.route('/subjects/delete', methods=['POST'])
@login_required
@role_required('admin','teacher')
def delete_subjects():
    ids = request.form.getlist('selected_ids')
    if not ids:
        flash('No subjects selected.','error'); return redirect(url_for('subjects'))
    conn = get_db()
    placeholders = ','.join('?'*len(ids))
    conn.execute(f"DELETE FROM subjects WHERE id IN ({placeholders})", ids)
    conn.commit(); conn.close()
    flash(f'{len(ids)} subject(s) deleted.','success')
    return redirect(url_for('subjects'))

@app.route('/subjects/delete/<int:sub_id>', methods=['POST'])
@login_required
@role_required('admin','teacher')
def delete_subject(sub_id):
    conn = get_db()
    sub = conn.execute("SELECT * FROM subjects WHERE id=?", (sub_id,)).fetchone()
    cls = sub['class'] if sub else ''
    conn.execute("DELETE FROM subjects WHERE id=?", (sub_id,))
    conn.commit(); conn.close()
    flash('Subject deleted.','success')
    # If came from marks page, go back there
    ref = request.referrer or ''
    if 'marks' in ref:
        return redirect(url_for('marks', **{'class': cls}))
    return redirect(url_for('subjects'))

# ══════════════════════════════════════════════════════════════════════════════
#  ATTENDANCE
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/attendance')
@login_required
def attendance():
    if session['role'] == 'student':
        return redirect(url_for('student_attendance'))
    conn = get_db()
    classes = rows_to_dicts(conn.execute("SELECT DISTINCT class FROM students ORDER BY class").fetchall())
    conn.close()
    sel_class = request.args.get('class', session.get('class_assigned','') if session['role']=='teacher' else '')
    sel_date  = request.args.get('date', date.today().isoformat())
    students = []
    if sel_class:
        conn = get_db()
        students = rows_to_dicts(conn.execute("""SELECT s.*, a.status FROM students s
            LEFT JOIN attendance a ON s.id=a.student_id AND a.date=?
            WHERE s.class=? ORDER BY s.roll_number""", (sel_date, sel_class)).fetchall())
        conn.close()
    return render_template('attendance.html', classes=classes, students=students,
                           sel_class=sel_class, sel_date=sel_date)

@app.route('/attendance/submit', methods=['POST'])
@login_required
@role_required('admin','teacher')
def submit_attendance():
    cls  = request.form.get('class')
    d    = request.form.get('date')
    present_ids = request.form.getlist('present')
    conn = get_db()
    stds = conn.execute("SELECT id FROM students WHERE class=?", (cls,)).fetchall()
    for s in stds:
        status = 'Present' if str(s['id']) in present_ids else 'Absent'
        conn.execute("""INSERT INTO attendance (student_id,date,status) VALUES (?,?,?)
            ON CONFLICT(student_id,date) DO UPDATE SET status=excluded.status""",
            (s['id'], d, status))
    conn.commit(); conn.close()
    flash(f'Attendance saved for class {cls} on {d}.','success')
    return redirect(url_for('attendance', **{'class':cls,'date':d}))

@app.route('/attendance/reset', methods=['POST'])
@login_required
@role_required('admin','teacher')
def reset_attendance():
    cls = request.form.get('class','')
    d   = request.form.get('date','')
    conn = get_db()
    if cls and d:
        conn.execute("""DELETE FROM attendance WHERE date=? AND student_id IN
            (SELECT id FROM students WHERE class=?)""", (d,cls))
        conn.commit()
        flash(f'Attendance reset for {cls} on {d}.','success')
    conn.close()
    return redirect(url_for('attendance', **{'class':cls,'date':d}))

@app.route('/student/attendance')
@login_required
@role_required('student')
def student_attendance():
    sid = session['student_id']
    conn = get_db()
    records = rows_to_dicts(conn.execute("SELECT * FROM attendance WHERE student_id=? ORDER BY date DESC", (sid,)).fetchall())
    total = len(records)
    present = sum(1 for r in records if r['status']=='Present')
    pct = round(present/total*100,1) if total else 0
    monthly = rows_to_dicts(conn.execute("""SELECT strftime('%Y-%m',date) as month,
        SUM(status='Present') as present, COUNT(*) as total
        FROM attendance WHERE student_id=? GROUP BY month ORDER BY month""", (sid,)).fetchall())
    conn.close()
    return render_template('student_attendance.html', records=records,
                           total=total, present=present, pct=pct, monthly=monthly)

# ══════════════════════════════════════════════════════════════════════════════
#  MARKS
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/marks')
@login_required
def marks():
    if session['role'] == 'student':
        return redirect(url_for('student_marks'))
    conn = get_db()
    classes = rows_to_dicts(conn.execute("SELECT DISTINCT class FROM students ORDER BY class").fetchall())
    sel_class = request.args.get('class', session.get('class_assigned','') if session['role']=='teacher' else '')
    sel_subject = request.args.get('subject','')
    sel_exam = request.args.get('exam_type','')
    subjects = []
    marks_data = []
    subj_exam_counts = {}
    if sel_class:
        subjects = rows_to_dicts(conn.execute("SELECT * FROM subjects WHERE class=? ORDER BY subject_name", (sel_class,)).fetchall())
    if sel_class and sel_subject and sel_exam:
        marks_data = rows_to_dicts(conn.execute("""
            SELECT s.id, s.name, s.roll_number, m.id as mid, m.marks_obtained, m.total_marks, m.date
            FROM students s LEFT JOIN marks m ON s.id=m.student_id AND m.subject_id=? AND m.exam_type=?
            WHERE s.class=? ORDER BY s.roll_number
        """, (sel_subject, sel_exam, sel_class)).fetchall())
    # For subject card labels, include exam-type counts
    subj_exam_counts = {}
    if sel_class:
        for sub in subjects:
            counts = {}
            for et in ['Midterm','Final','Quiz','Assignment']:
                cnt = conn.execute("""SELECT COUNT(*) FROM marks m JOIN students s ON m.student_id=s.id
                    WHERE m.subject_id=? AND m.exam_type=? AND s.class=?""",
                    (sub['id'], et, sel_class)).fetchone()[0]
                counts[et] = cnt
            subj_exam_counts[sub['id']] = counts
    # Build subject summary: for each subject, how many exam entries exist
    subject_summaries = []
    for sub in subjects:
        counts = {}
        exam_types_list = ['Midterm','Final','Quiz','Assignment']
        for et in exam_types_list:
            cnt = conn.execute("SELECT COUNT(*) FROM marks m JOIN students s ON m.student_id=s.id WHERE m.subject_id=? AND m.exam_type=? AND s.class=?", (sub['id'], et, sel_class)).fetchone()[0]
            counts[et] = cnt
        total_entries = sum(counts.values())
        subject_summaries.append({'id': sub['id'], 'subject_name': sub['subject_name'], 'exam_counts': counts, 'total': total_entries})
    conn.close()
    exam_types = ['Midterm','Final','Quiz','Assignment']
    return render_template('marks.html', classes=classes, subjects=subjects, marks_data=marks_data,
                           subject_summaries=subject_summaries,
                           sel_class=sel_class, sel_subject=sel_subject, sel_exam=sel_exam,
                           exam_types=exam_types)

@app.route('/marks/save', methods=['POST'])
@login_required
@role_required('admin','teacher')
def save_marks():
    cls = request.form.get('class')
    sub_id = request.form.get('subject_id')
    exam = request.form.get('exam_type')
    total = float(request.form.get('total_marks',100))
    today = date.today().isoformat()
    conn = get_db()
    stds = conn.execute("SELECT id FROM students WHERE class=?", (cls,)).fetchall()
    saved = 0
    for s in stds:
        val = request.form.get(f'marks_{s["id"]}','').strip()
        if val:
            try:
                obtained = min(float(val), total)
                conn.execute("""INSERT INTO marks (student_id,subject_id,exam_type,marks_obtained,total_marks,date)
                    VALUES (?,?,?,?,?,?)
                    ON CONFLICT(student_id,subject_id,exam_type) DO UPDATE SET
                    marks_obtained=excluded.marks_obtained, total_marks=excluded.total_marks, date=excluded.date""",
                    (s['id'], sub_id, exam, obtained, total, today))
                saved += 1
            except ValueError: pass
    conn.commit(); conn.close()
    flash(f'Marks saved for {saved} students.','success')
    return redirect(url_for('marks', **{'class':cls,'subject':sub_id,'exam_type':exam}))

@app.route('/marks/delete/<int:mid>', methods=['POST'])
@login_required
@role_required('admin','teacher')
def delete_mark(mid):
    conn = get_db()
    conn.execute("DELETE FROM marks WHERE id=?", (mid,))
    conn.commit(); conn.close()
    flash('Mark entry deleted.','success')
    return redirect(request.referrer or url_for('marks'))

@app.route('/student/marks')
@login_required
@role_required('student')
def student_marks():
    sid = session['student_id']
    conn = get_db()
    student = dict(conn.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone())
    marks = rows_to_dicts(conn.execute("""
        SELECT sub.subject_name, m.exam_type, m.marks_obtained, m.total_marks, m.date,
               ROUND(m.marks_obtained/m.total_marks*100,1) as pct
        FROM marks m JOIN subjects sub ON m.subject_id=sub.id
        WHERE m.student_id=? ORDER BY sub.subject_name, m.exam_type
    """, (sid,)).fetchall())
    subj_summary = rows_to_dicts(conn.execute("""
        SELECT sub.subject_name, AVG(m.marks_obtained/m.total_marks*100) as avg_pct, COUNT(*) as count
        FROM marks m JOIN subjects sub ON m.subject_id=sub.id
        WHERE m.student_id=? GROUP BY sub.subject_name
    """, (sid,)).fetchall())
    conn.close()
    return render_template('student_marks.html', student=student, marks=marks, subj_summary=subj_summary)

# ══════════════════════════════════════════════════════════════════════════════
#  PROGRESS
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/progress')
@login_required
def progress():
    if session['role'] == 'student':
        return redirect(url_for('student_progress'))
    conn = get_db()
    classes = rows_to_dicts(conn.execute("SELECT DISTINCT class FROM students ORDER BY class").fetchall())
    sel_class = request.args.get('class', session.get('class_assigned','') if session['role']=='teacher' else '')
    sel_student = request.args.get('student_id','')
    students_list = rows_to_dicts(conn.execute("SELECT * FROM students WHERE class=? ORDER BY roll_number", (sel_class,)).fetchall()) if sel_class else []
    progress_data = None
    if sel_student:
        s = dict(conn.execute("SELECT * FROM students WHERE id=?", (sel_student,)).fetchone())
        marks = rows_to_dicts(conn.execute("""
            SELECT sub.subject_name, m.exam_type, m.marks_obtained, m.total_marks,
                   ROUND(m.marks_obtained/m.total_marks*100,1) as pct
            FROM marks m JOIN subjects sub ON m.subject_id=sub.id
            WHERE m.student_id=? ORDER BY sub.subject_name, m.exam_type
        """, (sel_student,)).fetchall())
        total_att = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id=?", (sel_student,)).fetchone()[0]
        present_att = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='Present'", (sel_student,)).fetchone()[0]
        att_pct = round(present_att/total_att*100,1) if total_att else 0
        subj_summary = rows_to_dicts(conn.execute("""
            SELECT sub.subject_name, AVG(m.marks_obtained/m.total_marks*100) as avg_pct
            FROM marks m JOIN subjects sub ON m.subject_id=sub.id
            WHERE m.student_id=? GROUP BY sub.subject_name
        """, (sel_student,)).fetchall())
        overall_avg = round(sum(x['avg_pct'] for x in subj_summary)/len(subj_summary),1) if subj_summary else 0
        grade = get_grade(overall_avg)
        progress_data = {'student':s,'marks':marks,'total_att':total_att,'present_att':present_att,
                         'att_pct':att_pct,'subj_summary':subj_summary,'overall_avg':overall_avg,'grade':grade}
    conn.close()
    return render_template('progress.html', classes=classes, students_list=students_list,
                           progress_data=progress_data, sel_class=sel_class, sel_student=sel_student)

@app.route('/student/progress')
@login_required
@role_required('student')
def student_progress():
    sid = session['student_id']
    conn = get_db()
    student = dict(conn.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone())
    subj_summary = rows_to_dicts(conn.execute("""
        SELECT sub.subject_name, AVG(m.marks_obtained/m.total_marks*100) as avg_pct
        FROM marks m JOIN subjects sub ON m.subject_id=sub.id
        WHERE m.student_id=? GROUP BY sub.subject_name
    """, (sid,)).fetchall())
    total_att = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id=?", (sid,)).fetchone()[0]
    present_att = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='Present'", (sid,)).fetchone()[0]
    att_pct = round(present_att/total_att*100,1) if total_att else 0
    overall_avg = round(sum(s['avg_pct'] for s in subj_summary)/len(subj_summary),1) if subj_summary else 0
    grade = get_grade(overall_avg)
    monthly_att = rows_to_dicts(conn.execute("""SELECT strftime('%Y-%m',date) as month,
        SUM(status='Present') as present, COUNT(*) as total
        FROM attendance WHERE student_id=? GROUP BY month ORDER BY month""", (sid,)).fetchall())
    conn.close()
    return render_template('student_progress.html', student=student, subj_summary=subj_summary,
                           total_att=total_att, present_att=present_att, att_pct=att_pct,
                           overall_avg=overall_avg, grade=grade, monthly_att=monthly_att)

# ══════════════════════════════════════════════════════════════════════════════
#  CLASSBOARD
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/classboard')
@login_required
def classboard():
    conn = get_db()
    role = session['role']
    if role == 'student':
        student = dict(conn.execute("SELECT * FROM students WHERE id=?", (session['student_id'],)).fetchone())
        cls = student['class']
    elif role == 'teacher':
        cls = session.get('class_assigned','')
    else:
        cls = request.args.get('class','')
    classes = rows_to_dicts(conn.execute("SELECT DISTINCT class FROM students ORDER BY class").fetchall())
    type_filter = request.args.get('type','')
    q = "SELECT d.*, u.full_name as author FROM diary d JOIN users u ON d.created_by=u.id WHERE 1=1"
    params = []
    if cls: q += " AND d.class=?"; params.append(cls)
    if type_filter: q += " AND d.type=?"; params.append(type_filter)
    q += " ORDER BY d.created_at DESC"
    entries = rows_to_dicts(conn.execute(q, params).fetchall())
    conn.close()
    return render_template('classboard.html', entries=entries, cls=cls,
                           classes=classes, type_filter=type_filter, role=role)

@app.route('/classboard/add', methods=['POST'])
@login_required
@role_required('admin','teacher')
def add_diary():
    cls=request.form.get('class','').strip(); title=request.form.get('title','').strip()
    content=request.form.get('content','').strip(); typ=request.form.get('type','').strip()
    due=request.form.get('due_date','').strip() or None
    if not all([cls,title,content,typ]):
        flash('All fields required.','error'); return redirect(url_for('classboard'))
    conn = get_db()
    conn.execute("INSERT INTO diary (class,title,content,type,due_date,created_by,created_at) VALUES (?,?,?,?,?,?,?)",
                 (cls,title,content,typ,due,session['user_id'],datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit(); conn.close()
    flash('Entry added to ClassBoard.','success')
    return redirect(url_for('classboard', **{'class':cls}))

@app.route('/classboard/delete/<int:eid>', methods=['POST'])
@login_required
@role_required('admin','teacher')
def delete_diary(eid):
    conn = get_db()
    conn.execute("DELETE FROM diary WHERE id=?", (eid,))
    conn.commit(); conn.close()
    flash('Entry deleted.','success')
    return redirect(request.referrer or url_for('classboard'))

# ══════════════════════════════════════════════════════════════════════════════
#  REPORTS
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/reports')
@login_required
@role_required('admin','teacher')
def reports():
    conn = get_db()
    classes = rows_to_dicts(conn.execute("SELECT DISTINCT class FROM students ORDER BY class").fetchall())
    sel_class = request.args.get('class', session.get('class_assigned','') if session['role']=='teacher' else '')
    date_from = request.args.get('date_from',''); date_to = request.args.get('date_to','')
    results = []
    if sel_class:
        stds = conn.execute("SELECT * FROM students WHERE class=? ORDER BY roll_number", (sel_class,)).fetchall()
        for s in stds:
            att_q = "SELECT COUNT(*) FROM attendance WHERE student_id=?"
            params = [s['id']]
            if date_from: att_q += " AND date>=?"; params.append(date_from)
            if date_to:   att_q += " AND date<=?"; params.append(date_to)
            total_att = conn.execute(att_q, params).fetchone()[0]
            present_att = conn.execute(att_q.replace("COUNT(*)","SUM(status='Present')"), params).fetchone()[0] or 0
            att_pct = round(present_att/total_att*100,1) if total_att else 0
            m_avg = conn.execute("SELECT AVG(marks_obtained/total_marks*100) FROM marks WHERE student_id=?", (s['id'],)).fetchone()[0]
            m_avg = round(m_avg,1) if m_avg else 0
            results.append({'id':s['id'],'name':s['name'],'roll':s['roll_number'],
                            'total_att':total_att,'present':present_att,'att_pct':att_pct,
                            'avg_marks':m_avg,'grade':get_grade(m_avg)})
    conn.close()
    return render_template('reports.html', classes=classes, results=results,
                           sel_class=sel_class, date_from=date_from, date_to=date_to)

@app.route('/reports/export')
@login_required
@role_required('admin','teacher')
def export_report():
    sel_class = request.args.get('class','')
    conn = get_db()
    rows = conn.execute("""
        SELECT s.name, s.roll_number, s.class,
               COUNT(a.id) as total_att, SUM(a.status='Present') as present,
               AVG(m.marks_obtained/m.total_marks*100) as avg_marks
        FROM students s LEFT JOIN attendance a ON s.id=a.student_id LEFT JOIN marks m ON s.id=m.student_id
        WHERE s.class=? GROUP BY s.id ORDER BY s.roll_number
    """, (sel_class,)).fetchall()
    conn.close()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(['Name','Roll','Class','Total Days','Present','Att%','Avg Marks%','Grade'])
    for r in rows:
        att_pct = round((r['present'] or 0)/(r['total_att'] or 1)*100,1)
        avg_m = round(r['avg_marks'] or 0,1)
        w.writerow([r['name'],r['roll_number'],r['class'],r['total_att'],r['present'],att_pct,avg_m,get_grade(avg_m)])
    return Response(out.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition':f'attachment;filename=report_{sel_class}.csv'})

# ══════════════════════════════════════════════════════════════════════════════
#  PDF REPORTS
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/student/report_pdf/<int:sid>')
@login_required
def student_report_pdf(sid):
    if session['role'] == 'student' and session['student_id'] != sid:
        flash('Access denied.','error'); return redirect(url_for('dashboard'))
    conn = get_db()
    student = dict(conn.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone())
    # All marks
    all_marks = rows_to_dicts(conn.execute("""
        SELECT sub.subject_name, m.exam_type, m.marks_obtained, m.total_marks,
               ROUND(m.marks_obtained/m.total_marks*100,1) as pct
        FROM marks m JOIN subjects sub ON m.subject_id=sub.id
        WHERE m.student_id=? ORDER BY sub.subject_name, m.exam_type
    """, (sid,)).fetchall())
    # Group marks by subject
    subjects_marks = {}
    for m in all_marks:
        sn = m['subject_name']
        if sn not in subjects_marks:
            subjects_marks[sn] = []
        subjects_marks[sn].append(m)
    # Subject summary
    subj_summary = rows_to_dicts(conn.execute("""
        SELECT sub.subject_name, AVG(m.marks_obtained/m.total_marks*100) as avg_pct,
               SUM(m.marks_obtained) as total_obtained, SUM(m.total_marks) as total_possible
        FROM marks m JOIN subjects sub ON m.subject_id=sub.id
        WHERE m.student_id=? GROUP BY sub.subject_name
    """, (sid,)).fetchall())
    total_att = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id=?", (sid,)).fetchone()[0]
    present_att = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='Present'", (sid,)).fetchone()[0]
    att_pct = round(present_att/total_att*100,1) if total_att else 0
    monthly_att = rows_to_dicts(conn.execute("""SELECT strftime('%Y-%m',date) as month,
        SUM(status='Present') as present, COUNT(*) as total
        FROM attendance WHERE student_id=? GROUP BY month ORDER BY month""", (sid,)).fetchall())
    overall_avg = round(sum(s['avg_pct'] for s in subj_summary)/len(subj_summary),1) if subj_summary else 0
    grade = get_grade(overall_avg)
    conn.close()
    return render_template('report_pdf.html', student=student, all_marks=all_marks,
                           subjects_marks=subjects_marks, subj_summary=subj_summary,
                           total_att=total_att, present_att=present_att, att_pct=att_pct,
                           monthly_att=monthly_att, overall_avg=overall_avg,
                           grade=grade, generated=datetime.now().strftime('%d %b %Y %H:%M'))

@app.route('/attendance/report_pdf')
@login_required
@role_required('admin','teacher')
def attendance_report_pdf():
    sel_class = request.args.get('class','')
    date_from = request.args.get('date_from','')
    date_to   = request.args.get('date_to','')
    conn = get_db()
    stds = conn.execute("SELECT * FROM students WHERE class=? ORDER BY roll_number", (sel_class,)).fetchall()
    att_q_base = "SELECT COUNT(*) FROM attendance WHERE student_id=?"
    att_params_extra = []
    if date_from: att_params_extra.append(('date_from', date_from))
    if date_to:   att_params_extra.append(('date_to', date_to))
    results = []
    for s in stds:
        params = [s['id']]
        q = att_q_base
        if date_from: q += " AND date>=?"; params.append(date_from)
        if date_to:   q += " AND date<=?"; params.append(date_to)
        total = conn.execute(q, params).fetchone()[0]
        present = conn.execute(q.replace("COUNT(*)","SUM(status='Present')"), params).fetchone()[0] or 0
        pct = round(present/total*100,1) if total else 0
        monthly = rows_to_dicts(conn.execute("""SELECT strftime('%Y-%m',date) as month,
            SUM(status='Present') as present, COUNT(*) as total
            FROM attendance WHERE student_id=? GROUP BY month ORDER BY month""", (s['id'],)).fetchall())
        results.append({'name':s['name'],'roll':s['roll_number'],'total':total,'present':present,'pct':pct,'monthly':monthly})
    # Get all distinct dates for calendar view
    date_records = rows_to_dicts(conn.execute("""
        SELECT a.date, s.name, a.status FROM attendance a
        JOIN students s ON a.student_id=s.id WHERE s.class=? ORDER BY a.date, s.roll_number
    """, (sel_class,)).fetchall())
    conn.close()
    return render_template('attendance_pdf.html', sel_class=sel_class, results=results,
                           date_from=date_from, date_to=date_to,
                           generated=datetime.now().strftime('%d %b %Y %H:%M'))

@app.route('/users/reset_password/<int:uid>', methods=['POST'])
@login_required
@role_required('admin')
def reset_password(uid):
    new_pw = request.form.get('new_password','').strip()
    if not new_pw:
        flash('Password cannot be empty.','error'); return redirect(url_for('users'))
    conn = get_db()
    conn.execute("UPDATE users SET password=?, plain_password=? WHERE id=?", (hash_pw(new_pw), new_pw, uid))
    conn.commit(); conn.close()
    flash('Password reset successfully.','success')
    return redirect(url_for('users'))

# ══════════════════════════════════════════════════════════════════════════════
#  FEES MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/fees')
@login_required
def fees():
    if session['role'] == 'teacher':
        flash('Access denied. Teachers cannot view fees.','error')
        return redirect(url_for('dashboard'))
    conn = get_db()
    if session['role'] == 'student':
        sid = session['student_id']
        student = dict(conn.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone())
        fee_records = rows_to_dicts(conn.execute(
            "SELECT * FROM fees WHERE student_id=? ORDER BY month DESC", (sid,)).fetchall())
        total_fees  = sum(r['total_amount'] for r in fee_records)
        total_paid  = sum(r['paid_amount']  for r in fee_records)
        total_due   = total_fees - total_paid
        conn.close()
        return render_template('fees_student.html', student=student,
                               fee_records=fee_records, total_fees=total_fees,
                               total_paid=total_paid, total_due=total_due)
    # Admin view
    cls_filter = request.args.get('class','')
    search     = request.args.get('q','')
    month_filter = request.args.get('month','')
    q = """SELECT s.id as sid, s.name, s.roll_number, s.class, s.parent_phone,
              f.id, f.month, f.total_amount, f.paid_amount,
              (f.total_amount - f.paid_amount) as due_amount,
              f.status, f.due_date, f.notes, f.updated_at
           FROM students s LEFT JOIN fees f ON s.id=f.student_id WHERE 1=1"""
    params = []
    if cls_filter: q += " AND s.class=?"; params.append(cls_filter)
    if search:     q += " AND (s.name LIKE ? OR s.roll_number LIKE ?)"; params += [f'%{search}%']*2
    if month_filter: q += " AND f.month=?"; params.append(month_filter)
    q += " ORDER BY s.class, s.roll_number, f.month"
    records = rows_to_dicts(conn.execute(q, params).fetchall())
    classes  = rows_to_dicts(conn.execute("SELECT DISTINCT class FROM students ORDER BY class").fetchall())
    students = rows_to_dicts(conn.execute("SELECT * FROM students ORDER BY class, name").fetchall())
    months   = rows_to_dicts(conn.execute("SELECT DISTINCT month FROM fees ORDER BY month DESC").fetchall())
    # Summary stats
    total_billed = sum(r['total_amount'] or 0 for r in records if r['total_amount'])
    total_paid   = sum(r['paid_amount']  or 0 for r in records if r['paid_amount'])
    total_due    = total_billed - total_paid
    conn.close()
    return render_template('fees.html', records=records, classes=classes,
                           students=students, months=months,
                           cls_filter=cls_filter, search=search, month_filter=month_filter,
                           total_billed=total_billed, total_paid=total_paid, total_due=total_due)

@app.route('/fees/add', methods=['POST'])
@login_required
@role_required('admin')
def add_fee():
    sid    = request.form.get('student_id','').strip()
    month  = request.form.get('month','').strip()
    total  = request.form.get('total_amount','').strip()
    paid   = request.form.get('paid_amount','0').strip()
    due_dt = request.form.get('due_date','').strip() or None
    notes  = request.form.get('notes','').strip() or None
    if not all([sid,month,total]):
        flash('Student, month and total amount are required.','error')
        return redirect(url_for('fees'))
    try:
        total_f = float(total); paid_f = float(paid)
        status = 'Paid' if paid_f>=total_f else ('Partial' if paid_f>0 else 'Pending')
        conn = get_db()
        conn.execute("INSERT INTO fees (student_id,month,total_amount,paid_amount,status,due_date,notes,updated_at) VALUES (?,?,?,?,?,?,?,datetime('now'))",
                     (sid,month,total_f,paid_f,status,due_dt,notes))
        conn.commit(); conn.close()
        flash('Fee record added.','success')
    except (ValueError, sqlite3.IntegrityError) as e:
        flash(f'Error: {e}','error')
    return redirect(url_for('fees'))

@app.route('/fees/edit/<int:fid>', methods=['POST'])
@login_required
@role_required('admin')
def edit_fee(fid):
    total  = float(request.form.get('total_amount',0))
    paid   = float(request.form.get('paid_amount',0))
    due_dt = request.form.get('due_date','').strip() or None
    notes  = request.form.get('notes','').strip() or None
    status = 'Paid' if paid>=total else ('Partial' if paid>0 else 'Pending')
    conn = get_db()
    conn.execute("UPDATE fees SET total_amount=?,paid_amount=?,status=?,due_date=?,notes=?,updated_at=datetime('now') WHERE id=?",
                 (total,paid,status,due_dt,notes,fid))
    conn.commit(); conn.close()
    flash('Fee record updated.','success')
    return redirect(request.referrer or url_for('fees'))

@app.route('/fees/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_fees():
    ids = request.form.getlist('selected_ids')
    if not ids:
        flash('No records selected.','error'); return redirect(url_for('fees'))
    conn = get_db()
    ph = ','.join('?'*len(ids))
    conn.execute(f"DELETE FROM fees WHERE id IN ({ph})", ids)
    conn.commit(); conn.close()
    flash(f'{len(ids)} fee record(s) deleted.','success')
    return redirect(url_for('fees'))

@app.route('/fees/pdf')
@login_required
@role_required('admin')
def fees_pdf():
    cls_filter   = request.args.get('class','')
    month_filter = request.args.get('month','')
    conn = get_db()
    q = """SELECT s.name, s.roll_number, s.class, s.parent_phone,
              f.month, f.total_amount, f.paid_amount,
              (f.total_amount-f.paid_amount) as due_amount, f.status, f.due_date, f.notes
           FROM students s JOIN fees f ON s.id=f.student_id WHERE 1=1"""
    params=[]
    if cls_filter:   q+=" AND s.class=?";  params.append(cls_filter)
    if month_filter: q+=" AND f.month=?";  params.append(month_filter)
    q += " ORDER BY s.class, s.roll_number, f.month"
    records = rows_to_dicts(conn.execute(q,params).fetchall())
    total_billed = sum(r['total_amount'] for r in records)
    total_paid   = sum(r['paid_amount']  for r in records)
    conn.close()
    return render_template('fees_pdf.html', records=records,
                           cls_filter=cls_filter, month_filter=month_filter,
                           total_billed=total_billed, total_paid=total_paid,
                           total_due=total_billed-total_paid,
                           generated=datetime.now().strftime('%d %b %Y %H:%M'))

# ══════════════════════════════════════════════════════════════════════════════
#  CLASS MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/classes')
@login_required
@role_required('admin')
def classes():
    conn = get_db()
    all_classes = rows_to_dicts(conn.execute("SELECT c.*, COUNT(s.id) as student_count FROM classes c LEFT JOIN students s ON s.class=c.name GROUP BY c.id ORDER BY c.name").fetchall())
    conn.close()
    return render_template('classes.html', classes=all_classes)

@app.route('/classes/add', methods=['POST'])
@login_required
@role_required('admin')
def add_class():
    name = request.form.get('name','').strip().upper()
    section = request.form.get('section','').strip()
    if not name:
        flash('Class name is required.','error'); return redirect(url_for('classes'))
    conn = get_db()
    try:
        conn.execute("INSERT INTO classes (name, section) VALUES (?,?)", (name, section or None))
        conn.commit()
        flash(f'Class "{name}" added successfully.','success')
    except sqlite3.IntegrityError:
        flash(f'Class "{name}" already exists.','error')
    conn.close()
    return redirect(url_for('classes'))

@app.route('/classes/edit/<int:cid>', methods=['POST'])
@login_required
@role_required('admin')
def edit_class(cid):
    new_name = request.form.get('name','').strip().upper()
    section = request.form.get('section','').strip()
    if not new_name:
        flash('Class name required.','error'); return redirect(url_for('classes'))
    conn = get_db()
    old = conn.execute("SELECT name FROM classes WHERE id=?", (cid,)).fetchone()
    if old:
        old_name = old['name']
        try:
            conn.execute("UPDATE classes SET name=?, section=? WHERE id=?", (new_name, section or None, cid))
            # Cascade rename to students, subjects, diary, users
            conn.execute("UPDATE students SET class=? WHERE class=?", (new_name, old_name))
            conn.execute("UPDATE subjects SET class=? WHERE class=?", (new_name, old_name))
            conn.execute("UPDATE diary SET class=? WHERE class=?", (new_name, old_name))
            conn.execute("UPDATE users SET class_assigned=? WHERE class_assigned=?", (new_name, old_name))
            conn.commit()
            flash(f'Class renamed from "{old_name}" to "{new_name}". All records updated.','success')
        except sqlite3.IntegrityError:
            flash(f'Class "{new_name}" already exists.','error')
    conn.close()
    return redirect(url_for('classes'))

@app.route('/classes/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_classes():
    ids = request.form.getlist('selected_ids')
    if not ids:
        flash('No classes selected.','error'); return redirect(url_for('classes'))
    conn = get_db()
    names = [conn.execute("SELECT name FROM classes WHERE id=?", (i,)).fetchone()['name'] for i in ids]
    placeholders = ','.join('?'*len(ids))
    conn.execute(f"DELETE FROM classes WHERE id IN ({placeholders})", ids)
    conn.commit(); conn.close()
    flash(f'Deleted {len(ids)} class(es): {", ".join(names)}','success')
    return redirect(url_for('classes'))

@app.route('/api/classes')
@login_required
def api_classes():
    conn = get_db()
    cls_list = rows_to_dicts(conn.execute("SELECT name FROM classes ORDER BY name").fetchall())
    # Also include any classes used in students but not yet in classes table
    used = rows_to_dicts(conn.execute("SELECT DISTINCT class as name FROM students ORDER BY class").fetchall())
    all_names = list({c['name'] for c in cls_list + used})
    all_names.sort()
    conn.close()
    return jsonify(all_names)

# ══════════════════════════════════════════════════════════════════════════════
#  API
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/api/marks_data')
@login_required
def api_marks_data():
    cls     = request.args.get('class','')
    sub_id  = request.args.get('subject','')
    exam    = request.args.get('exam_type','')
    if not all([cls, sub_id, exam]):
        return jsonify([])
    conn = get_db()
    rows = rows_to_dicts(conn.execute("""
        SELECT s.id, s.name, s.roll_number, m.id as mid,
               m.marks_obtained, m.total_marks, m.date
        FROM students s LEFT JOIN marks m
          ON s.id=m.student_id AND m.subject_id=? AND m.exam_type=?
        WHERE s.class=? ORDER BY s.roll_number
    """, (sub_id, exam, cls)).fetchall())
    conn.close()
    return jsonify(rows)

@app.route('/api/subjects_by_class')
@login_required
def api_subjects():
    cls = request.args.get('class','')
    conn = get_db()
    subs = rows_to_dicts(conn.execute("SELECT * FROM subjects WHERE class=? ORDER BY subject_name", (cls,)).fetchall())
    conn.close()
    return jsonify(subs)

@app.route('/api/students_by_class')
@login_required
def api_students_by_class():
    cls = request.args.get('class','')
    conn = get_db()
    stds = rows_to_dicts(conn.execute("SELECT * FROM students WHERE class=? ORDER BY roll_number", (cls,)).fetchall())
    conn.close()
    return jsonify(stds)

# Initialize the database on import too, so it works when run under a
# production server like gunicorn (which never hits the __main__ block).
init_db()

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
