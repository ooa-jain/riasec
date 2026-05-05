from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests, json, csv, io, smtplib, threading, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'jain_riasec_secret_2024')

SHEET_ID      = os.getenv('SHEET_ID', '')
SCRIPT_URL    = os.getenv('SCRIPT_URL', '')
SMTP_EMAIL    = os.getenv('SMTP_EMAIL', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
SMTP_SERVER   = 'smtp.gmail.com'
SMTP_PORT     = 587

# ── Trait meta ─────────────────────────────────────────────────────────────────
TRAIT_INFO = {
    'R': {'name': 'Realistic',     'icon': '🔧', 'color': '#e17055', 'desc': 'Practical & hands-on',    'careers': ['Engineer', 'Architect', 'Mechanic', 'Pilot', 'Chef']},
    'I': {'name': 'Investigative', 'icon': '🔬', 'color': '#0984e3', 'desc': 'Analytical & scientific', 'careers': ['Scientist', 'Doctor', 'Data Analyst', 'Researcher', 'Economist']},
    'A': {'name': 'Artistic',      'icon': '🎨', 'color': '#956afa', 'desc': 'Creative & expressive',   'careers': ['Designer', 'Writer', 'Musician', 'Filmmaker', 'Art Director']},
    'S': {'name': 'Social',        'icon': '🤝', 'color': '#00b894', 'desc': 'Helpful & cooperative',   'careers': ['Teacher', 'Counselor', 'Nurse', 'HR Manager', 'Social Worker']},
    'E': {'name': 'Enterprising',  'icon': '🚀', 'color': '#f39c12', 'desc': 'Leadership & ambitious',  'careers': ['Entrepreneur', 'Manager', 'Lawyer', 'Sales Director', 'CEO']},
    'C': {'name': 'Conventional',  'icon': '📊', 'color': '#636e72', 'desc': 'Organized & systematic',  'careers': ['Accountant', 'Banker', 'Admin', 'Financial Analyst', 'Auditor']},
}

BG_COLORS = {
    'R': '#fff5f3', 'I': '#f0f7ff', 'A': '#f5f0ff',
    'S': '#f0fff8', 'E': '#fffcf0', 'C': '#f8f9fa',
}

COURSES = {
    'creative-tech': {
        'title': 'BS (Hons) in Creative Technology and Design',
        'university': 'JAIN (Deemed-to-be University)',
        'matchTraits': ['A', 'I', 'S'],
        'pathway': "Master's in Creative Technology and Design — UCAM University, Spain",
    },
    'data-ai': {
        'title': 'BS (Hons) in Data Analytics and Applied Artificial Intelligence',
        'university': 'JAIN (Deemed-to-be University)',
        'matchTraits': ['I', 'C', 'R'],
        'pathway': "Master's in Data Analytics and Applied Artificial Intelligence — UCAM University, Spain",
    },
    'corporate-mgmt': {
        'title': 'MS in Corporate Management and Lean Six Sigma',
        'university': 'JAIN (Deemed-to-be University)',
        'matchTraits': ['E', 'C', 'I'],
        'pathway': 'PG Certificate in Business Excellence — UCAM University, Spain & Lean Six Sigma Institute',
    },
    'sports-science': {
        'title': 'MS in High Performance Sports: Strength and Conditioning',
        'university': 'JAIN (Deemed-to-be University)',
        'matchTraits': ['R', 'I', 'S'],
        'pathway': 'PG Certificate in High Performance Sports: Strength and Conditioning — UCAM University, Spain',
    },
}


# ── Apps Script POST ───────────────────────────────────────────────────────────
def post_to_script(row, sheet_name='Sheet1'):
    if not SCRIPT_URL:
        print('⚠️  SCRIPT_URL not set')
        return False
    try:
        resp = requests.post(
            SCRIPT_URL,
            json={'row': row, 'sheet': sheet_name},
            timeout=15,
            allow_redirects=True,
            headers={'Content-Type': 'application/json'}
        )
        print(f'📋 Script [{resp.status_code}]: {resp.text[:200]}')
        return resp.status_code in (200, 201, 302)
    except Exception as e:
        print(f'❌ post_to_script error: {e}')
        return False


# ── Sheet readers ──────────────────────────────────────────────────────────────
def fetch_sheet_data():
    if not SHEET_ID:
        print('⚠️  SHEET_ID not set')
        return []
    try:
        url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet=Sheet1'
        r = requests.get(url, timeout=20, allow_redirects=True)
        r.raise_for_status()
        reader = csv.reader(io.StringIO(r.text))
        rows = list(reader)
        if len(rows) < 2:
            return []
        result = []
        for row in rows[1:]:
            if len(row) < 2 or not row[1].strip():
                continue
            def safe(i): return row[i].strip() if i < len(row) else ''
            result.append({
                'timestamp': safe(0), 'name': safe(1), 'email': safe(2), 'phone': safe(3),
                'R': safe(4) or '0', 'I': safe(5) or '0', 'A': safe(6) or '0',
                'S': safe(7) or '0', 'E': safe(8) or '0', 'C': safe(9) or '0',
                'top3_codes': safe(10), 'top3_names': safe(11)
            })
        print(f'📊 Fetched {len(result)} rows')
        return result
    except Exception as e:
        print(f'❌ CSV fetch error: {e}')
        return fetch_sheet_gviz()


def fetch_sheet_gviz():
    if not SHEET_ID:
        return []
    try:
        url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:json&sheet=Sheet1'
        r = requests.get(url, timeout=15)
        text = r.text
        start = text.index('(') + 1
        end   = text.rindex(')')
        data  = json.loads(text[start:end])
        rows  = data['table']['rows']
        result = []
        for row in rows[1:]:
            c = row.get('c', [])
            def val(i):
                if i < len(c) and c[i] and c[i].get('v') is not None:
                    return str(c[i]['v'])
                return ''
            if not val(1):
                continue
            result.append({
                'timestamp': val(0), 'name': val(1), 'email': val(2), 'phone': val(3),
                'R': val(4) or '0', 'I': val(5) or '0', 'A': val(6) or '0',
                'S': val(7) or '0', 'E': val(8) or '0', 'C': val(9) or '0',
                'top3_codes': val(10), 'top3_names': val(11)
            })
        print(f'📊 gviz fallback: {len(result)} rows')
        return result
    except Exception as e:
        print(f'❌ gviz error: {e}')
        return []


# ── Email builders ─────────────────────────────────────────────────────────────
def build_email_html(name, top3, scores):
    first = (name.split()[0] if name else 'Student')

    def trait_card(code, rank):
        t   = TRAIT_INFO[code]
        bg  = BG_COLORS[code]
        col = t['color']
        sc  = int(scores.get(code, 0))
        max_score = 7
        pct = int((sc / max_score) * 100)
        rank_badge = ['🥇 #1 Match', '🥈 #2 Match', '🥉 #3 Match'][rank]
        careers = ' · '.join(t['careers'][:3])
        return f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
          <tr><td style="background:{bg};border:2px solid {col}22;border-radius:16px;padding:20px 24px;">
            <span style="display:inline-block;background:{col};color:#fff;font-size:11px;font-weight:700;
              padding:3px 10px;border-radius:20px;letter-spacing:0.5px;text-transform:uppercase;
              margin-bottom:8px;">{rank_badge}</span>
            <table cellpadding="0" cellspacing="0"><tr>
              <td style="font-size:32px;padding-right:14px;vertical-align:middle;">{t['icon']}</td>
              <td style="vertical-align:middle;">
                <div style="font-size:22px;font-weight:800;color:{col};line-height:1;">{code}</div>
                <div style="font-size:15px;font-weight:700;color:#1e293b;margin-top:2px;">{t['name']}</div>
                <div style="font-size:12px;color:#64748b;margin-top:2px;">{t['desc']}</div>
              </td>
            </tr></table>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:14px;"><tr>
              <td style="background:#e8ecf0;border-radius:10px;height:8px;overflow:hidden;">
                <div style="width:{pct}%;height:8px;background:{col};border-radius:10px;"></div>
              </td>
              <td width="50" style="padding-left:10px;font-size:12px;font-weight:700;color:{col};">{sc}/{max_score}</td>
            </tr></table>
            <div style="margin-top:10px;font-size:12px;color:#64748b;">
              <strong style="color:#475569;">Career paths:</strong> {careers}
            </div>
          </td></tr>
        </table>"""

    cards_html = ''.join(trait_card(code, i) for i, code in enumerate(top3))
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f2f8;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f8;padding:40px 16px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
  <tr><td style="background:linear-gradient(145deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
    border-radius:20px 20px 0 0;padding:40px 44px 36px;text-align:center;">
    <div style="font-size:28px;font-weight:800;color:#fff;margin-bottom:8px;">Your RIASEC Results</div>
    <div style="font-size:14px;color:rgba(255,255,255,0.55);">Career Assessment · Personality Profile Report</div>
  </td></tr>
  <tr><td style="background:#fff;padding:40px 44px;">
    <h1 style="margin:0 0 16px;font-size:24px;font-weight:800;color:#1a1a2e;">Hey {first}! 👋</h1>
    <p style="margin:0 0 28px;font-size:15px;color:#475569;line-height:1.7;">
      Thank you for completing the <strong>JAIN RIASEC Career Assessment</strong>.
      Here are your <strong style="color:#667eea;">top 3 personality traits</strong>.
    </p>
    {cards_html}
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="background:linear-gradient(135deg,rgba(102,126,234,0.07),rgba(149,106,250,0.07));
        border:1.5px solid rgba(102,126,234,0.18);border-radius:16px;padding:24px;text-align:center;">
        <div style="font-size:15px;font-weight:800;color:#1e293b;margin-bottom:8px;">Want Personalized Guidance?</div>
        <a href="https://jainsogs.com/gfs" style="display:inline-block;background:linear-gradient(135deg,#667eea,#764ba2);
          color:#fff;text-decoration:none;padding:12px 28px;border-radius:10px;font-size:14px;font-weight:700;">
          Visit JAIN School of Global Studies →
        </a>
      </td>
    </tr></table>
  </td></tr>
  <tr><td style="background:#f8fafc;border-radius:0 0 20px 20px;border-top:1px solid #e8ecf0;
    padding:24px 44px;text-align:center;">
    <div style="font-size:11px;color:#b8c4d0;">
      Questions? <a href="mailto:{SMTP_EMAIL}" style="color:#667eea;">{SMTP_EMAIL}</a>
    </div>
  </td></tr>
</table></td></tr></table>
</body></html>"""


def build_enrollment_email_html(name, email, phone, course_title, top3, message=''):
    first = (name.split()[0] if name else 'Student')
    msg_row = (f'<tr><td style="padding:12px 16px;font-size:12px;font-weight:700;color:#64748b;'
               f'text-transform:uppercase;border-top:1px solid #f1f5f9;">Message</td>'
               f'<td style="padding:12px 16px;font-size:14px;color:#1e293b;border-top:1px solid #f1f5f9;">'
               f'{message}</td></tr>' if message else '')
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f2f8;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f8;padding:40px 16px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;
  border-radius:20px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,0.1);">
  <tr><td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:32px 44px;text-align:center;">
    <div style="font-size:24px;font-weight:800;color:#fff;">🎓 New Enrollment Request</div>
    <div style="font-size:13px;color:rgba(255,255,255,0.7);margin-top:6px;">JAIN · RIASEC Portal</div>
  </td></tr>
  <tr><td style="padding:36px 44px;">
    <table width="100%" cellpadding="0" cellspacing="0"
      style="border-radius:12px;overflow:hidden;border:1px solid #e8ecf0;margin-bottom:24px;">
      <tr style="background:#f8fafc;"><td style="padding:12px 16px;font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;width:140px;">Student Name</td><td style="padding:12px 16px;font-size:14px;font-weight:600;color:#1e293b;">{name}</td></tr>
      <tr><td style="padding:12px 16px;font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;border-top:1px solid #f1f5f9;">Email</td><td style="padding:12px 16px;font-size:14px;font-weight:600;color:#1e293b;border-top:1px solid #f1f5f9;">{email}</td></tr>
      <tr style="background:#f8fafc;"><td style="padding:12px 16px;font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;border-top:1px solid #f1f5f9;">Phone</td><td style="padding:12px 16px;font-size:14px;font-weight:600;color:#1e293b;border-top:1px solid #f1f5f9;">{phone}</td></tr>
      <tr><td style="padding:12px 16px;font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;border-top:1px solid #f1f5f9;">Course</td><td style="padding:12px 16px;font-size:14px;font-weight:700;color:#667eea;border-top:1px solid #f1f5f9;">{course_title}</td></tr>
      <tr style="background:#f8fafc;"><td style="padding:12px 16px;font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;border-top:1px solid #f1f5f9;">Top 3 Traits</td><td style="padding:12px 16px;font-size:14px;font-weight:600;color:#1e293b;border-top:1px solid #f1f5f9;">{', '.join(top3)}</td></tr>
      {msg_row}
    </table>
    <div style="background:rgba(102,126,234,0.07);border-radius:12px;padding:18px;font-size:13px;color:#64748b;line-height:1.7;">
      Please contact the student within <strong style="color:#1e293b;">24 hours</strong>.
    </div>
  </td></tr>
</table></td></tr></table>
</body></html>"""


def send_result_email(to_email, name, top3, scores):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print('⚠️  SMTP not configured')
        return
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '🎯 Your RIASEC Results – JAIN School of Global Studies'
        msg['From']    = f'JAIN Career Guidance <{SMTP_EMAIL}>'
        msg['To']      = to_email
        first = (name.split()[0] if name else 'Student')
        top3_text = '\n'.join(
            f'  #{i+1} {TRAIT_INFO[c]["name"]} ({c}) — {TRAIT_INFO[c]["desc"]}'
            for i, c in enumerate(top3) if c in TRAIT_INFO
        )
        plain = f'Hi {first},\n\nThank you for completing the JAIN RIASEC Assessment!\n\nYour Top 3:\n{top3_text}\n\nVisit: https://jainsogs.com/gfs'
        html  = build_email_html(name, top3, scores)
        msg.attach(MIMEText(plain, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo(); server.starttls(); server.ehlo()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        print(f'✅ Result email → {to_email}')
    except Exception as e:
        print(f'❌ Result email failed: {e}')


def send_enrollment_notification(enroll_data):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print('⚠️  SMTP not configured')
        return
    try:
        name         = enroll_data.get('name', '')
        email        = enroll_data.get('email', '')
        phone        = enroll_data.get('phone', '')
        course_title = enroll_data.get('course', 'N/A')
        top3         = enroll_data.get('top3', [])
        message      = enroll_data.get('message', '')
        first = (name.split()[0] if name else 'Student')

        admin_msg = MIMEMultipart('alternative')
        schol_flag = enroll_data.get('scholarship', False)
        action = 'Scholarship Click' if schol_flag else 'Enrollment'
        admin_msg['Subject'] = f'🎓 {action}: {name} → {course_title}'
        admin_msg['From']    = f'JAIN RIASEC Portal <{SMTP_EMAIL}>'
        admin_msg['To']      = SMTP_EMAIL
        admin_msg.attach(MIMEText(
            build_enrollment_email_html(name, email, phone, course_title, top3, message), 'html'))

        student_msg = MIMEMultipart('alternative')
        student_msg['Subject'] = '🎓 Enrollment Received – JAIN School of Global Studies'
        student_msg['From']    = f'JAIN Admissions <{SMTP_EMAIL}>'
        student_msg['To']      = email
        student_plain = (f'Hi {first},\n\nWe received your enrollment interest for {course_title}.\n'
                         f'Our Admission Coordinator will contact you within 24 hours.\n\n'
                         f'Best regards,\nJAIN School of Global Studies')
        student_html  = f"""<!DOCTYPE html><html><body style="font-family:'Segoe UI',Arial,sans-serif;background:#f0f2f8;margin:0;padding:36px 14px;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<table width="560" style="background:#fff;border-radius:20px;overflow:hidden;max-width:560px;width:100%;">
  <tr><td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:30px 36px;text-align:center;">
    <div style="font-size:20px;font-weight:800;color:#fff;">Enrollment Request Received</div>
  </td></tr>
  <tr><td style="padding:32px 36px;">
    <p style="font-size:16px;font-weight:700;color:#1e293b;margin-bottom:16px;">Hi {first}!</p>
    <div style="background:#f0f4ff;border-radius:12px;padding:16px 20px;margin-bottom:20px;">
      <div style="font-size:11px;font-weight:700;color:#667eea;text-transform:uppercase;margin-bottom:6px;">Your Selected Programme</div>
      <div style="font-size:14px;font-weight:800;color:#1e293b;">{course_title}</div>
    </div>
    <p style="font-size:14px;color:#475569;line-height:1.75;">Our Admission Coordinator will contact you within <strong>24 hours</strong>.</p>
    <p style="font-size:12px;color:#64748b;margin-top:16px;">Questions? <a href="mailto:{SMTP_EMAIL}" style="color:#667eea;">{SMTP_EMAIL}</a></p>
  </td></tr>
</table></td></tr></table>
</body></html>"""
        student_msg.attach(MIMEText(student_plain, 'plain'))
        student_msg.attach(MIMEText(student_html, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo(); server.starttls(); server.ehlo()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, SMTP_EMAIL, admin_msg.as_string())
            if email:
                server.sendmail(SMTP_EMAIL, email, student_msg.as_string())
        print(f'✅ Enrollment emails sent for {name}')
    except Exception as e:
        print(f'❌ Enrollment email error: {e}')


def save_enrollment_to_sheet(enroll_data):
    row = [
        enroll_data.get('timestamp', ''),
        enroll_data.get('name', ''),
        enroll_data.get('email', ''),
        enroll_data.get('phone', ''),
        enroll_data.get('course', ''),
        enroll_data.get('courseId', ''),
        ', '.join(enroll_data.get('top3', [])),
        enroll_data.get('message', ''),
    ]
    post_to_script(row, sheet_name='Enrollments')


# ── Routes ─────────────────────────────────────────────────────────────────────
def ctx():
    """Common template context."""
    return {'script_url': SCRIPT_URL}

@app.route('/')
def index():
    return redirect(url_for('entry'))

@app.route('/entry')
def entry():
    return render_template('entry.html', **ctx())

@app.route('/survey')
def survey():
    return render_template('survey.html', **ctx())

@app.route('/home')
def home():
    return render_template('home.html', **ctx())

@app.route('/programs')
def programs():
    return render_template('programs.html', **ctx())

@app.route('/results')
def results():
    return render_template('results.html', **ctx())

@app.route('/admin')
def admin():
    return render_template('admin.html', **ctx())

@app.route('/course/<course_id>')
def course(course_id):
    if course_id not in COURSES:
        return redirect(url_for('home'))
    return render_template('course.html', **ctx())


# ── API ────────────────────────────────────────────────────────────────────────
@app.route('/api/lookup-email', methods=['POST'])
def lookup_email():
    email = (request.json or {}).get('email', '').strip().lower()
    if not email:
        return jsonify({'found': False})
    rows    = fetch_sheet_data()
    matches = [r for r in rows if r.get('email', '').strip().lower() == email]
    if matches:
        user = matches[-1]
        print(f'✅ Login: {user["name"]} ({email})')
        return jsonify({'found': True, 'user': user})
    print(f'ℹ️  No record for {email}')
    return jsonify({'found': False})


@app.route('/api/submit-results', methods=['POST'])
def submit_results():
    body   = request.json or {}
    name   = body.get('name', '').strip()
    email  = body.get('email', '').strip()
    phone  = body.get('phone', '').strip()
    scores = body.get('scores', {})
    top3   = body.get('top3', [])
    ts     = body.get('timestamp', '')

    if not (name and email and top3):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    row = [ts, name, email, phone,
           scores.get('R', 0), scores.get('I', 0), scores.get('A', 0),
           scores.get('S', 0), scores.get('E', 0), scores.get('C', 0),
           ', '.join(top3),
           ', '.join(TRAIT_INFO[t]['name'] for t in top3 if t in TRAIT_INFO)]

    threading.Thread(target=post_to_script, args=(row, 'Sheet1'), daemon=True).start()
    threading.Thread(target=send_result_email, args=(email, name, top3, scores), daemon=True).start()
    return jsonify({'success': True})


@app.route('/api/enroll', methods=['POST'])
def enroll():
    body      = request.json or {}
    name      = body.get('name', '').strip()
    email     = body.get('email', '').strip()
    phone     = body.get('phone', '').strip()
    course    = body.get('course', '').strip()
    course_id = body.get('courseId', '').strip()
    top3      = body.get('top3', [])
    message   = body.get('message', '').strip()
    ts        = body.get('timestamp', '')

    if not (name and email):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    enroll_data = {
        'name': name, 'email': email, 'phone': phone,
        'course': course, 'courseId': course_id,
        'top3': top3, 'message': message, 'timestamp': ts,
    }
    threading.Thread(target=save_enrollment_to_sheet, args=(enroll_data,), daemon=True).start()
    threading.Thread(target=send_enrollment_notification, args=(enroll_data,), daemon=True).start()
    return jsonify({'success': True})


@app.route('/api/admin-data', methods=['POST'])
def admin_data():
    body = request.json or {}
    if body.get('password') != 'admin@2023':
        return jsonify({'error': 'Unauthorized'}), 401
    rows = fetch_sheet_data()
    return jsonify({'rows': rows, 'count': len(rows)})


if __name__ == '__main__':
    print(f'🚀 JAIN RIASEC Server')
    print(f'   SHEET_ID:   {"✅" if SHEET_ID else "❌ NOT SET"}')
    print(f'   SCRIPT_URL: {"✅" if SCRIPT_URL else "❌ NOT SET"}')
    print(f'   SMTP_EMAIL: {"✅" if SMTP_EMAIL else "❌ NOT SET"}')
    app.run(debug=True, port=5000)
