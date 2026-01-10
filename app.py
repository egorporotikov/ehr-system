from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import os
import re
from flask_migrate import Migrate


# --- App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'replace_this_with_a_random_secret')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Email Configuration - Google
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT'))
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS') == 'True'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL') == 'True'
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

db = SQLAlchemy(app)
mail = Mail(app)
migrate = Migrate(app, db)  # Flask-Migrate
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# --- Models ---
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    confirmed = db.Column(db.Boolean, default=False)
    confirmed_on = db.Column(db.DateTime, nullable=True)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    medical_history = db.Column(db.Text)
    weight = db.Column(db.Float)
    last_visit = db.Column(db.String(50))
    allergies = db.Column(db.String(200))
    image_filename = db.Column(db.String(200))

class SUSResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    q1 = db.Column(db.Integer, nullable=False)
    q2 = db.Column(db.Integer, nullable=False)
    q3 = db.Column(db.Integer, nullable=False)
    q4 = db.Column(db.Integer, nullable=False)
    q5 = db.Column(db.Integer, nullable=False)
    q6 = db.Column(db.Integer, nullable=False)
    q7 = db.Column(db.Integer, nullable=False)
    q8 = db.Column(db.Integer, nullable=False)
    q9 = db.Column(db.Integer, nullable=False)
    q10 = db.Column(db.Integer, nullable=False)
    submitted_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    

SUS_QUESTIONS = [
    "1. I think that I would like to use this system frequently.",
    "2. I found the system unnecessarily complex.",
    "3. I thought the system was easy to use.",
    "4. I think that I would need the support of a technical person to be able to use this system.",
    "5. I found the various functions in this system were well integrated.",
    "6. I thought there was too much inconsistency in this system.",
    "7. I would imagine that most people would learn to use this system very quickly.",
    "8. I found the system very cumbersome to use.",
    "9. I felt very confident using the system.",
    "10. I needed to learn a lot of things before I could get going with this system."
]

# --- Helper Functions ---
def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is strong"

def send_confirmation_email(email, name):
    """Send email confirmation link"""
    try:
        token = serializer.dumps(email, salt='email-confirm')
        confirm_url = url_for('confirm_email', token=token, _external=True)
        
        # DEBUG: Output to console
        print("\n" + "="*70)
        print(f"📧 SENDING EMAIL")
        print(f"   To: {email}")
        print(f"   Name: {name}")
        print(f"🔗 CONFIRMATION LINK:")
        print(f"   {confirm_url}")
        print("="*70 + "\n")
        
        msg = Message('Confirm Your Email - EHR System',
                      recipients=[email])
        msg.html = f"""
        <h2>Welcome to EHR System, {name}!</h2>
        <p>Thank you for registering. Please confirm your email address by clicking the link below:</p>
        <p><a href="{confirm_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Confirm Email</a></p>
        <p>Or copy and paste this link into your browser:</p>
        <p>{confirm_url}</p>
        <p>This link will expire in 24 hours.</p>
        <p>If you didn't register for an account, please ignore this email.</p>
        """
        mail.send(msg)
        print("✅ Email sent successfully!\n")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}\n")
        return False

def send_password_reset_email(email, name):
    """Send password reset link"""
    try:
        token = serializer.dumps(email, salt='password-reset')
        reset_url = url_for('reset_password', token=token, _external=True)
        
        # DEBUG: Output to console
        print("\n" + "="*70)
        print(f"🔑 SENDING PASSWORD RESET")
        print(f"   To: {email}")
        print(f"   Name: {name}")
        print(f"🔗 RESET LINK:")
        print(f"   {reset_url}")
        print("="*70 + "\n")
        
        msg = Message('Password Reset Request - EHR System',
                      recipients=[email])
        msg.html = f"""
        <h2>Password Reset Request</h2>
        <p>Hello {name},</p>
        <p>We received a request to reset your password. Click the link below to reset it:</p>
        <p><a href="{reset_url}" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a></p>
        <p>Or copy and paste this link into your browser:</p>
        <p>{reset_url}</p>
        <p>This link will expire in 1 hour.</p>
        <p>If you didn't request a password reset, please ignore this email.</p>
        """
        mail.send(msg)
        print("✅ Password reset email sent successfully!\n")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}\n")
        return False

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

# --- Registration ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        password_raw = request.form.get('password','').strip()

        if not name or not email or not password_raw:
            flash('Please fill all fields', 'danger')
            return redirect(url_for('register'))

        # Validate password strength
        is_valid, message = validate_password(password_raw)
        if not is_valid:
            flash(message, 'danger')
            return redirect(url_for('register'))

        if Doctor.query.filter_by(email=email).first():
            flash('Email already registered!', 'warning')
            return redirect(url_for('register'))

        password = generate_password_hash(password_raw)
        new_doctor = Doctor(name=name, email=email, password=password, confirmed=False)
        db.session.add(new_doctor)
        db.session.commit()

        # Send confirmation email
        if send_confirmation_email(email, name):
            flash('Registration successful! Please check your email to confirm your account.', 'success')
        else:
            flash('Registration successful! However, we could not send the confirmation email. Please contact support.', 'warning')
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

# --- Email Confirmation ---
@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=86400)  # 24 hours
    except SignatureExpired:
        flash('The confirmation link has expired. Please request a new one.', 'danger')
        return redirect(url_for('resend_confirmation'))
    except BadSignature:
        flash('Invalid confirmation link.', 'danger')
        return redirect(url_for('login'))

    doctor = Doctor.query.filter_by(email=email).first()
    
    if not doctor:
        flash('Account not found.', 'danger')
        return redirect(url_for('login'))
    
    if doctor.confirmed:
        flash('Account already confirmed. Please log in.', 'info')
    else:
        doctor.confirmed = True
        doctor.confirmed_on = db.func.current_timestamp()
        db.session.commit()
        flash('Your email has been confirmed! You can now log in.', 'success')
    
    return redirect(url_for('login'))

# --- Resend Confirmation ---
@app.route('/resend_confirmation', methods=['GET', 'POST'])
def resend_confirmation():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        doctor = Doctor.query.filter_by(email=email).first()
        
        if doctor:
            if doctor.confirmed:
                flash('Your account is already confirmed. Please log in.', 'info')
                return redirect(url_for('login'))
            
            if send_confirmation_email(email, doctor.name):
                flash('A new confirmation email has been sent. Please check your inbox.', 'success')
            else:
                flash('Could not send confirmation email. Please try again later.', 'danger')
        else:
            # Don't reveal if email exists or not (security)
            flash('If the email exists, a confirmation link has been sent.', 'info')
        
        return redirect(url_for('login'))
    
    return render_template('resend_confirmation.html')

# --- Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        password = request.form.get('password','').strip()
        doctor = Doctor.query.filter_by(email=email).first()

        if doctor and check_password_hash(doctor.password, password):
            if not doctor.confirmed:
                flash('Please confirm your email before logging in. Check your inbox.', 'warning')
                return render_template('login.html', show_resend=True, email=email)
            
            session['doctor_id'] = doctor.id
            session['doctor_name'] = doctor.name
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

# --- Forgot Password ---
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        doctor = Doctor.query.filter_by(email=email).first()
        
        if doctor:
            if send_password_reset_email(email, doctor.name):
                flash('Password reset instructions have been sent to your email.', 'success')
            else:
                flash('Could not send reset email. Please try again later.', 'danger')
        else:
            # Don't reveal if email exists or not (security)
            flash('If the email exists in our system, a password reset link has been sent.', 'info')
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

# --- Reset Password ---
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset', max_age=3600)  # 1 hour
    except SignatureExpired:
        flash('The password reset link has expired. Please request a new one.', 'danger')
        return redirect(url_for('forgot_password'))
    except BadSignature:
        flash('Invalid password reset link.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        password_raw = request.form.get('password', '').strip()
        password_confirm = request.form.get('password_confirm', '').strip()
        
        if password_raw != password_confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html', token=token)
        
        # Validate password strength
        is_valid, message = validate_password(password_raw)
        if not is_valid:
            flash(message, 'danger')
            return render_template('reset_password.html', token=token)
        
        doctor = Doctor.query.filter_by(email=email).first()
        if doctor:
            doctor.password = generate_password_hash(password_raw)
            db.session.commit()
            flash('Your password has been reset successfully. Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Account not found.', 'danger')
            return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)

# --- Dashboard with search ---
@app.route('/dashboard')
def dashboard():
    if 'doctor_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))

    doctor_id = session['doctor_id']
    search_query = request.args.get('search', '').strip()

    if search_query:
        patients = Patient.query.filter(
            Patient.doctor_id == doctor_id,
            Patient.name.ilike(f'%{search_query}%')
        ).all()
    else:
        patients = Patient.query.filter_by(doctor_id=doctor_id).all()

    return render_template('dashboard.html', patients=patients)

# --- New Patient ---
@app.route('/patient/new', methods=['GET','POST'])
def patient_new():
    if 'doctor_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name','').strip()
        age = request.form.get('age') or None
        gender = request.form.get('gender','')
        medical_history = request.form.get('medical_history','')
        weight = request.form.get('weight') or None
        last_visit = request.form.get('last_visit','')
        allergies = ",".join(request.form.getlist('allergies'))

        file = request.files.get('image')
        filename = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        p = Patient(
            doctor_id=session['doctor_id'],
            name=name,
            age=int(age) if age else None,
            gender=gender,
            medical_history=medical_history,
            weight=float(weight) if weight else None,
            last_visit=last_visit,
            allergies=allergies,
            image_filename=filename
        )
        db.session.add(p)
        db.session.commit()
        flash('Patient created', 'success')
        return redirect(url_for('dashboard'))

    return render_template('ehr_form.html', patient=None)

# --- Edit Patient ---
@app.route('/patient/<int:pid>/edit', methods=['GET','POST'])
def patient_edit(pid):
    if 'doctor_id' not in session:
        return redirect(url_for('login'))

    p = Patient.query.get_or_404(pid)
    if p.doctor_id != session['doctor_id']:
        flash('Not authorized', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        p.name = request.form.get('name','').strip()
        p.age = int(request.form.get('age') or 0)
        p.gender = request.form.get('gender','')
        p.medical_history = request.form.get('medical_history','')
        p.weight = float(request.form.get('weight') or 0)
        p.last_visit = request.form.get('last_visit','')
        p.allergies = ",".join(request.form.getlist('allergies'))

        file = request.files.get('image')
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            p.image_filename = filename

        db.session.commit()
        flash('Patient updated', 'success')
        return redirect(url_for('dashboard'))

    return render_template('ehr_form.html', patient=p)

# --- Delete Patient ---
@app.route('/patient/<int:pid>/delete', methods=['POST'])
def patient_delete(pid):
    if 'doctor_id' not in session:
        return redirect(url_for('login'))

    p = Patient.query.get_or_404(pid)
    if p.doctor_id != session['doctor_id']:
        flash('Not authorized', 'danger')
        return redirect(url_for('dashboard'))

    db.session.delete(p)
    db.session.commit()
    flash('Patient deleted', 'success')
    return redirect(url_for('dashboard'))

# --- Survey (SUS) ---
@app.route('/survey', methods=['GET','POST'])
def survey():
    if 'doctor_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        answers = [int(request.form.get(f'q{i}', 0)) for i in range(1, 11)]
        sus = SUSResult(
            doctor_id=session['doctor_id'],
            q1=answers[0], q2=answers[1], q3=answers[2], q4=answers[3], q5=answers[4],
            q6=answers[5], q7=answers[6], q8=answers[7], q9=answers[8], q10=answers[9]
        )
        db.session.add(sus)
        db.session.commit()
        flash('Thank you for completing the survey!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('survey.html')

@app.route('/sus_results')
def sus_results():
    if 'doctor_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))

    results = SUSResult.query.order_by(SUSResult.submitted_at.desc()).all()
    return render_template('sus_results.html', results=results, questions=SUS_QUESTIONS)

# --- Logout ---
@app.route('/logout')
def logout():
    session.pop('doctor_id', None)
    session.pop('doctor_name', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/ehr_info')
def ehr_info():
    return render_template('ehr_info.html')

# --- Serve uploaded files ---
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- Run App ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    
    
    
    #https://mailtrap.io/inboxes/4296136/messages