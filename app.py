from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

# --- App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'replace_this_with_a_random_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# --- Models ---
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

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

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        password_raw = request.form.get('password','').strip()
        if not name or not email or not password_raw:
            flash('Fill all fields', 'danger')
            return redirect(url_for('register'))
        password = generate_password_hash(password_raw)
        if Doctor.query.filter_by(email=email).first():
            flash('Email already registered!', 'warning')
            return redirect(url_for('register'))
        new_doctor = Doctor(name=name, email=email, password=password)
        db.session.add(new_doctor)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        password = request.form.get('password','').strip()
        doctor = Doctor.query.filter_by(email=email).first()
        if doctor and check_password_hash(doctor.password, password):
            session['doctor_id'] = doctor.id
            session['doctor_name'] = doctor.name
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'doctor_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    doctor_id = session['doctor_id']
    patients = Patient.query.filter_by(doctor_id=doctor_id).all()
    return render_template('dashboard.html', patients=patients)

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

@app.route('/survey', methods=['GET','POST'])
def survey():
    # simple SUS capture: store responses in DB later (for now just show page)
    if request.method == 'POST':
        # handle and save answers (we'll add DB table later)
        flash('Thank you for completing the survey!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('survey.html')

@app.route('/logout')
def logout():
    session.pop('doctor_id', None)
    session.pop('doctor_name', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Serve uploaded files (for dev)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- Run app ---
if __name__ == '__main__':
    if not os.path.exists('instance'):
        os.makedirs('instance')
    with app.app_context():
        db.create_all()
    app.run(debug=True)
