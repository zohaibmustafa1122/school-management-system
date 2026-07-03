# 🏫 SchoolTrack — Complete School Management System

A full-featured school management platform with role-based access (Admin, Teacher, Student), attendance, marks, progress tracking, ClassBoard diary, and PDF report generation.

---

## 🚀 Quick Start (3 commands)

```bash
cd school_system
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000**

---

## 🔑 Login Credentials

| Role    | Username       | Password      | Access |
|---------|----------------|---------------|--------|
| Admin   | `admin`        | `admin123`    | Full system access |
| Teacher | `teacher1`     | `teacher123`  | Class 10-A |
| Teacher | `teacher2`     | `teacher123`  | Class 10-B |
| Teacher | `teacher3`     | `teacher123`  | Class 9-A |
| Student | `student_001`  | `student123`  | Ahmed Khan (10-A) |
| Student | `student_007`  | `student123`  | Ayesha Noor (10-B) |

> All students: username = `student_[roll_number]`, password = `student123`

---

## 📁 Project Structure

```
school_system/
│
├── app.py                        ← Complete Flask backend (all routes)
├── school.db                     ← SQLite DB (auto-created on first run)
├── requirements.txt
│
├── templates/
│   ├── base.html                 ← Shared layout with role-based sidebar
│   ├── login.html                ← Login page
│   ├── dashboard_admin.html      ← Admin dashboard
│   ├── dashboard_teacher.html    ← Teacher dashboard (per class)
│   ├── dashboard_student.html    ← Student dashboard (own data only)
│   ├── users.html                ← User account management (admin)
│   ├── students.html             ← Student CRUD
│   ├── subjects.html             ← Subject management
│   ├── attendance.html           ← Mark attendance
│   ├── student_attendance.html   ← Student's own attendance view
│   ├── marks.html                ← Marks portal
│   ├── student_marks.html        ← Student's own marks view
│   ├── progress.html             ← Progress report (teacher/admin)
│   ├── student_progress.html     ← Student's own progress
│   ├── classboard.html           ← Diary/announcements/assignments
│   ├── reports.html              ← Class reports + CSV export
│   └── report_pdf.html           ← Printable PDF report card
│
└── static/
    ├── css/style.css             ← Full responsive stylesheet
    └── js/app.js                 ← Modal, sidebar, validation helpers
```

---

## ✨ Features by Role

### 👑 Admin
- Full access to all modules
- **User Management**: Create/edit/delete login credentials for teachers & students
- **Dashboard**: Class-wise performance overview with charts
- **Student Management**: Add/edit/delete students (auto-creates login)
- **Subjects**: Add/delete subjects per class
- **Attendance**: Mark for any class, reset capability
- **Marks Portal**: Enter marks by class/subject/exam
- **Student Progress**: View any student's full profile with radar chart
- **ClassBoard**: Post and manage entries for all classes
- **Reports**: Full class reports with CSV export + individual PDF

### 👩‍🏫 Teacher
- Restricted to their assigned class
- **Dashboard**: Class-specific stats and charts
- **Students**: Manage their class students
- **Attendance**: Mark/reset attendance for their class
- **Marks Portal**: Enter marks for their class subjects
- **Student Progress**: View any student in their class
- **ClassBoard**: Post assignments & announcements for their class
- **Reports**: Class report with CSV + individual PDF

### 👨‍🎓 Student
- **View-only access** to their own data
- **Dashboard**: Personal stats + recent ClassBoard notices
- **My Attendance**: Full attendance record with monthly chart
- **My Marks**: All marks with subject performance chart
- **My Progress**: Radar chart, grade calculation, overall summary
- **ClassBoard**: View assignments & announcements for their class
- **Download Report**: Printable PDF report card

---

## 🗄️ Database Tables

| Table     | Key Columns |
|-----------|-------------|
| users     | id, username, password (SHA-256), role, full_name, student_id, class_assigned |
| students  | id, name, roll_number, class |
| subjects  | id, subject_name, class |
| marks     | id, student_id, subject_id, exam_type, marks_obtained, total_marks, date |
| attendance| id, student_id, date, status (Present/Absent) |
| diary     | id, class, title, content, type, due_date, created_by, created_at |

---

## 📊 Grading System

| Grade | Percentage |
|-------|-----------|
| A     | 80%+      |
| B     | 60–79%    |
| C     | 40–59%    |
| F     | Below 40% |

---

## 💡 Notes

- Database auto-creates with 14 sample students, marks, attendance & diary entries
- Adding a student auto-creates their login (`student_[roll]` / `student123`)
- Attendance can be reset per class per date by teachers/admin
- Marks entry supports all exam types: Midterm, Final, Quiz, Assignment
- PDF report includes marks table, subject grades, attendance, and signature lines
- CSV export includes all student data for the selected class

---

## 🛠️ Tech Stack
- **Backend**: Python 3 + Flask (pure stdlib only)
- **Database**: SQLite (zero setup)
- **Frontend**: HTML, CSS, JavaScript
- **Charts**: Chart.js 4 (CDN)
- **Fonts**: Plus Jakarta Sans + JetBrains Mono (Google Fonts)
