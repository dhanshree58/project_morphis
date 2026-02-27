from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
import sqlite3
import datetime
import requests
import os
import pickle
import pandas as pd
from werkzeug.utils import secure_filename
from severity_engine import adjust_severity
from ai_engine import extract_symptoms, generate_ai_recommendations
from sdi_engine import calculate_sdi, get_patient_data, get_previous_scores
# Initialization

app = Flask(__name__)
app.secret_key = "supersecretkey" 
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
DB_NAME = os.path.join(BASE_DIR, "health.db")
with open(os.path.join( "disease_model.pkl"), "rb") as f:
    model = pickle.load(f)

symptoms = pd.read_csv(
    os.path.join(BASE_DIR, "symptom_list.csv")
)["Symptom"].tolist()


UPLOAD_FOLDER = 'Upload'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Gemini API configuration 



#  Utility Functions
def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Makes datetime available in all templates
def utility_processor():
    return dict(datetime=datetime)
app.context_processor(utility_processor)


#  File Upload Routes
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload_record', methods=['POST'])
def upload_record():
    """Handle file upload with metadata"""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Login required'}), 401

    # Check if file is in request
    if 'document_file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
    
    file = request.files['document_file']
    description = request.form.get('document_description', '').strip()
    user_id = session['user_id']

    # Validate file
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': 'Invalid file type. Only PDF, JPG, JPEG, PNG allowed'}), 400

    try:
        
        original_filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"user{user_id}_{timestamp}_{original_filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save file to disk
        file.save(file_path)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        file_size_mb = round(file_size / (1024 * 1024), 2)
        
        # Save metadata to database
        conn = get_connection()
        cursor = conn.cursor()
        upload_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO UserRecords (user_id, file_name, description, upload_date)
            VALUES (?, ?, ?, ?)
        """, (user_id, filename, description if description else original_filename, upload_date))
        
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()

        # Return success response with record details
        return jsonify({
            'status': 'success',
            'message': 'File uploaded successfully',
            'record': {
                'id': record_id,
                'file_name': filename,
                'description': description if description else original_filename,
                'upload_date': upload_date,
                'file_size': f"{file_size_mb} MB",
                'download_url': url_for('uploaded_file', filename=filename, _external=False)
            }
        })
        
    except Exception as e:
        # Clean up file if database insert fails
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'status': 'error', 'message': f'Upload failed: {str(e)}'}), 500

@app.route('/get_records', methods=['GET'])
def get_records():
    """Fetch all records for the logged-in user"""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Login required'}), 401

    user_id = session['user_id']
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT record_id, file_name, description, upload_date
            FROM UserRecords
            WHERE user_id=?
            ORDER BY upload_date DESC
        """, (user_id,))
        
        records = cursor.fetchall()
        conn.close()

        # Convert records to list of dictionaries
        records_list = []
        for r in records:
            record_dict = {
                'id': r['record_id'],
                'file_name': r['file_name'],
                'description': r['description'] if r['description'] else 'Medical Document',
                'upload_date': r['upload_date'],
                'download_url': url_for('uploaded_file', filename=r['file_name'], _external=False)
            }
            
            # Add file size if file exists
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], r['file_name'])
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                record_dict['file_size'] = f"{round(file_size / (1024 * 1024), 2)} MB"
            
            records_list.append(record_dict)

        return jsonify({
            'status': 'success',
            'records': records_list,
            'total': len(records_list)
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to fetch records: {str(e)}'}), 500

@app.route('/delete_record', methods=['POST'])
def delete_record():
    """Delete a record and its associated file"""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Login required'}), 401

    data = request.get_json()
    record_id = data.get('record_id')
    user_id = session['user_id']

    if not record_id:
        return jsonify({'status': 'error', 'message': 'Record ID required'}), 400

    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # First, get the file name and verify ownership
        cursor.execute("""
            SELECT file_name FROM UserRecords 
            WHERE record_id=? AND user_id=?
        """, (record_id, user_id))
        
        record = cursor.fetchone()
        
        if not record:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Record not found or access denied'}), 404
        
        file_name = record['file_name']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        
        # Delete from database
        cursor.execute("DELETE FROM UserRecords WHERE record_id=? AND user_id=?", (record_id, user_id))
        conn.commit()
        conn.close()
        
        # Delete physical file if it exists
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Warning: Could not delete file {file_path}: {e}")
        
        return jsonify({
            'status': 'success', 
            'message': 'Record deleted successfully',
            'deleted_id': record_id
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'status': 'error', 'message': f'Delete failed: {str(e)}'}), 500

@app.route('/download_record/<int:record_id>')
def download_record(record_id):
    """Download a specific record file"""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Login required'}), 401
    
    user_id = session['user_id']
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT file_name FROM UserRecords 
            WHERE record_id=? AND user_id=?
        """, (record_id, user_id))
        
        record = cursor.fetchone()
        conn.close()
        
        if not record:
            return jsonify({
                'status': 'error',
                'message': 'Record not found or access denied'
            }), 404
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], record['file_name'])
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({
                'status': 'error',
                'message': 'File not found on server. It may have been deleted.'
            }), 404
        
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            record['file_name'],
            as_attachment=True  # Force download
        )
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error downloading file: {str(e)}'
        }), 500
@app.route('/view_record/<int:record_id>')
def view_record(record_id):
    """View a specific record file in browser"""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Login required'}), 401
    
    user_id = session['user_id']
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT file_name FROM UserRecords 
            WHERE record_id=? AND user_id=?
        """, (record_id, user_id))
        
        record = cursor.fetchone()
        conn.close()
        
        if not record:
            return jsonify({
                'status': 'error',
                'message': 'Record not found or access denied'
            }), 404
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], record['file_name'])
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({
                'status': 'error',
                'message': 'File not found on server. It may have been deleted.'
            }), 404
        
        # Serve the file for viewing (inline display)
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            record['file_name'],
            as_attachment=False  # Display in browser instead of download
        )
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error viewing file: {str(e)}'
        }), 500

    
#  Symptom / Recommendations
def fetch_symptoms(symptom_list):

    if not symptom_list:
        return [], []

    # Convert underscore format to space format
    normalized_list = [
        s.replace("_", " ").strip().lower()
        for s in symptom_list
    ]

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ','.join(['?'] * len(normalized_list))

    cursor.execute(f"""
        SELECT symptom_id, symptom_name, doctor_advice, priority
        FROM Symptoms
        WHERE LOWER(REPLACE(symptom_name, '_', ' ')) IN ({placeholders})
    """, normalized_list)

    results = cursor.fetchall()
    conn.close()

    symptoms_data = [{
        'id': r['symptom_id'],
        'name': r['symptom_name'],
        'advice': r['doctor_advice'],
        'priority': r['priority']
    } for r in results]

    if len(symptoms_data) > 3:
        symptoms_data.sort(key=lambda x: x['priority'], reverse=True)
        symptoms_data = symptoms_data[:3]

    final_symptom_ids = [s['id'] for s in symptoms_data]

    return final_symptom_ids, symptoms_data

def fetch_recommendations(symptom_ids):
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ','.join(['?']*len(symptom_ids))
    cursor.execute(f"""
        SELECT DISTINCT R.rec_name, R.rec_type, R.instructions, R.disclaimer
        FROM Symptom_Recommendation_Mapping M
        JOIN Recommendations R ON M.rec_id = R.rec_id
        WHERE M.symptom_id IN ({placeholders})
        ORDER BY R.rec_type, R.rec_name
    """, symptom_ids)
    recommendations_list = cursor.fetchall()
    conn.close()
    return recommendations_list

def fetch_doctors(symptom_ids):
    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ','.join(['?']*len(symptom_ids))

    # Step 1: Get specialties from symptoms
    cursor.execute(f"""
        SELECT DISTINCT S.specialty_id, S.specialty_name
        FROM Symptom_Specialty_Mapping M
        JOIN Specialties S ON M.specialty_id = S.specialty_id
        WHERE M.symptom_id IN ({placeholders})
    """, symptom_ids)

    required_specialties = cursor.fetchall()
    specialty_ids = [s['specialty_id'] for s in required_specialties]

    doctors_found = []

    if specialty_ids:
        spec_placeholders = ','.join(['?']*len(specialty_ids))

        # Step 2: JOIN to get specialty name instead of specialty_id
        cursor.execute(f"""
            SELECT D.doctor_id,
                   D.name,
                   D.rating,
                   D.experience,
                   D.availability,
                   S.specialty_name,
                   D.biography
            FROM Doctors D
            JOIN Specialties S ON D.specialty_id = S.specialty_id
            WHERE D.specialty_id IN ({spec_placeholders})
            ORDER BY D.rating DESC, D.experience DESC
        """, specialty_ids)

        doctors_found = cursor.fetchall()

    conn.close()
    return required_specialties, doctors_found

def log_history(user_id, symptoms_data, user_age=None, chronic=False, intensity="none"):

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        for symptom in symptoms_data:

            adjusted_sev = adjust_severity(
                symptom['priority'],
                user_age=user_age,
                chronic=chronic,
                intensity=intensity
            )

            cursor.execute("""
                INSERT INTO Health_History 
                (user_id, symptom_name, severity, date_recorded)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                symptom['name'],
                adjusted_sev,
                now
            ))

        conn.commit()

    except Exception as e:
        print("History Log Error:", e)

    finally:
        conn.close()



#  General Routes
@app.route("/")
def homepage():
    return render_template("homepage.html") 

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("homepage"))


#  Doctor Routes
@app.route("/doctor_login", methods=["GET", "POST"])
def doctor_login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"].strip()
        name = request.form.get("name", "").strip()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT doctor_id, name FROM Doctors WHERE email=? AND password=?", (email, password))
        doctor = cursor.fetchone()

        if doctor:
            session["doctor_id"] = doctor["doctor_id"]
            session["doctor_name"] = doctor["name"]
            flash(f"Welcome Dr. {doctor['name']}!", "success")
            conn.close()
            return redirect(url_for("doctor_panel"))

        # New doctor registration
        if not name:
            flash("Name is required for new doctor registration.", "danger")
            conn.close()
            return redirect(url_for("doctor_login"))

        try:
            cursor.execute("""
                INSERT INTO Doctors (name, email, password, rating, experience, availability)
                VALUES (?, ?, ?, 0, 0, 'Available')
            """, (name, email, password))
            conn.commit()
            flash("Doctor registered successfully! Please update your profile.", "success")
        except Exception as e:
            flash(f"Registration error: {e}", "danger")
        finally:
            conn.close()

        return redirect(url_for("doctor_login"))

    return render_template("doctor_login.html")

@app.route("/doctor_panel")
def doctor_panel():
    if "doctor_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, specialty, biography FROM Doctors WHERE doctor_id=?", (doctor_id,))
    doctor_data = cursor.fetchone()

    cursor.execute("""
    SELECT A.appointment_id, A.user_id, U.name AS patient_name,
           A.appointment_date, A.appointment_time, A.status, A.reason
    FROM Appointments A
    JOIN Users U ON A.user_id = U.user_id
    WHERE A.doctor_id = ?
    ORDER BY A.appointment_date DESC, A.appointment_time DESC
""", (doctor_id,))

    appointments = cursor.fetchall()
    conn.close()

    return render_template(
        "doctor_session.html",
        doctor_name=doctor_data["name"],
        profile_data=doctor_data,
        appointments=appointments,
        active_section="appointments"
    )

@app.route("/doctor_profile")
def doctor_profile():
    if "doctor_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, specialty, biography FROM Doctors WHERE doctor_id=?", (doctor_id,))
    doctor_data = cursor.fetchone()
    conn.close()

    return render_template(
        "doctor_session.html",
        doctor_name=doctor_data["name"] if doctor_data else "Unknown",
        profile_data=doctor_data,
        active_section="profile"
    )
@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "doctor_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]
    name = request.form.get("name", "").strip()
    specialty = request.form.get("specialty", "").strip()
    biography = request.form.get("biography", "").strip()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Doctors 
        SET name=?, specialty=?, biography=? 
        WHERE doctor_id=?
    """, (name, specialty, biography, doctor_id))
    conn.commit()
    conn.close()

    session["doctor_name"] = name
    flash("Profile updated successfully!", "success")
    return redirect(url_for("doctor_profile"))



@app.route("/update_status/<int:appointment_id>/<string:status>")
def update_status(appointment_id, status):
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    if status not in ['Approved', 'Rejected']:
        flash("Invalid status update.", "danger")
        return redirect(url_for("doctor_panel"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Appointments SET status=? WHERE appointment_id=?", (status, appointment_id))
    conn.commit()
    conn.close()

    flash(f"Appointment {appointment_id} {status.lower()} successfully!", "success")
    return redirect(url_for("doctor_panel"))

#  Patient Routes
@app.route("/patient_login_form", methods=["GET", "POST"])
def patient_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        name = request.form.get("name", "").strip()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name FROM Users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()

        if user:
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            conn.close()
            return redirect(url_for("patient_dashboard"))

        elif name:
            try:
                cursor.execute("INSERT INTO Users (name, email, password) VALUES (?, ?, ?)",
                               (name.title(), email, password))
                conn.commit()
                session["user_id"] = cursor.lastrowid
                session["user_name"] = name.title()
                flash(f"New account created for {name.title()}! Welcome!", "success")
            except sqlite3.IntegrityError:
                flash("Email already registered. Please login.", "warning")
            except Exception as e:
                flash(f"Registration failed: {e}", "danger")
            finally:
                conn.close()
            return redirect(url_for("patient_dashboard"))

        flash("Invalid email or password. Provide a name to register.", "danger")
        conn.close()
        return render_template("patient_login_form.html", email=email, name=name)

    return render_template("patient_login_form.html")
@app.route("/symptom_analysis", methods=["POST"])
def symptom_analysis():

    # ----------------------------
    # 1️⃣ Session Validation
    # ----------------------------
    if "user_id" not in session:
        flash("Session expired.", "warning")
        return redirect(url_for("patient_login"))

    symptoms_text_raw = request.form.get("symptoms_input", "").strip()

    if not symptoms_text_raw:
        flash("Please describe your symptoms.", "danger")
        return redirect(url_for("patient_dashboard"))

    # ----------------------------
    # 2️⃣ Extract Symptoms via AI
    # ----------------------------
    from ai_engine import extract_symptoms, generate_ai_recommendations
    from sdi_engine import calculate_sdi

    ai_output = extract_symptoms(symptoms_text_raw)

    symptom_names_lower = ai_output.get("symptoms", [])
    intensity = ai_output.get("intensity", "none")

    if not symptom_names_lower:
        flash("No recognizable symptoms entered.", "warning")
        return redirect(url_for("patient_dashboard"))

    # ----------------------------
    # 3️⃣ Get Symptoms from DB
    # ----------------------------
    final_symptom_ids, symptoms_data = fetch_symptoms(symptom_names_lower)
    

    if not final_symptom_ids:
        flash("No matching symptoms found in database.", "warning")

        return redirect(url_for("patient_dashboard"))
    
    action = request.form.get("action").strip()
    if action == "analyze":
        recommendations = fetch_recommendations(final_symptom_ids)
        specialties, doctors = fetch_doctors(final_symptom_ids)

    # ----------------------------
    # 4️⃣ Log Health History
    # ----------------------------
        log_history(
        session["user_id"],
        symptoms_data,
        user_age=30,
        chronic=False,
        intensity=intensity
        )

    # ----------------------------
    # 5️⃣ Fetch Full Symptom History
    # ----------------------------
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT symptom_name, severity, date_recorded
        FROM Health_History
        WHERE user_id = ?
         ORDER BY date_recorded DESC
    """, (session["user_id"],))

        history_rows = cursor.fetchall()
        conn.close()

        history_data = [dict(row) for row in history_rows]

    # ----------------------------
    # 6️⃣ Fetch Age & Chronic Info
    # ----------------------------
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT age, disease FROM Users WHERE user_id = ?",
        (session["user_id"],)
    )

    user_info = cursor.fetchone()
    conn.close()

    user_age = user_info["age"] if user_info and user_info["age"] else 30
    user_disease = user_info["disease"] if user_info and user_info["disease"] else None

    # ----------------------------
    # 7️⃣ Fetch Previous SDI Scores
    # ----------------------------
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT normalized_score
        FROM SDI_History
        WHERE user_id = ?
        ORDER BY date_recorded DESC
        LIMIT 5
    """, (session["user_id"],))

    prev_rows = cursor.fetchall()
    conn.close()

    previous_scores = [row["normalized_score"] for row in prev_rows]

    # ----------------------------
    # 8️⃣ Calculate SDI
    # ----------------------------
  

    # ----------------------------
    # 9️⃣ Map Intensity → Phase
    # ----------------------------
    if intensity == "mild":
        phase = "low"
    elif intensity == "severe":
        phase = "high"
    else:
        phase = "moderate"

    # ----------------------------
    # 🔟 Generate AI Recommendations
    # ----------------------------
    ai_data = generate_ai_recommendations(
        symptoms=symptom_names_lower,
        phase=phase,
        sdi_score=50,
        age=user_age,
        chronic=True if user_disease else False
    )

    # ----------------------------
    # 1️⃣1️⃣ Save AI Assessment
    # ----------------------------
    fixed_sdi_score = 50
    try:
        conn = get_connection()
        print(" Attempting to save AI assessment...")
        cursor = conn.cursor()
        

        cursor.execute("""
        INSERT INTO AI_Assessments
        (user_id, symptoms, intensity, risk_level, sdi_score, doctor_required)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            ",".join(symptom_names_lower),
            intensity,
            ai_data.get("risk_level"),
            fixed_sdi_score,
            1 if ai_data.get("doctor_required") else 0
        ))

        conn.commit()
        print(" Inserted rows:", cursor.rowcount)
        conn.close()

    except Exception as e:
        print("AI Save Error:", e)

    # ----------------------------
    # 1️⃣2️⃣ Store Session Data
    # ----------------------------
    session["analysis"] = {
        "symptoms_data": symptoms_data,
       # "recommendations": [dict(r) for r in recommendations],
        # "specialties": [dict(s) for s in specialties],
        #"doctors": [dict(d) for d in doctors],
        "symptoms_text": symptoms_text_raw
    }


   
    if action == "analyze":
     return render_template(
        "patient_dashboard.html",
        user_name=session["user_name"],
        active_section="results",
        symptoms_data=symptoms_data,
        recommendations=recommendations,
        doctors=doctors,
        specialties=specialties,
        symptoms_text=symptoms_text_raw,
        ai_data=ai_data,
        show_booking_section=True if doctors else False
     )


    elif action == "risk_assessment":

     user_id = session["user_id"]

     import os
     BASE_DIR = os.path.dirname(os.path.abspath(__file__))
     DB_NAME = os.path.join(BASE_DIR, "health.db")


    # Get patient info + full history
     user_age, user_disease, history_data = get_patient_data(user_id)

     previous_scores = get_previous_scores(user_id)

     sdi_result = calculate_sdi(
        history_data,
        user_age,
        user_disease,
        previous_scores
     )

    # Also fetch general symptom info so page looks consistent

     return render_template(
        "patient_dashboard.html",
        user_name=session.get("user_name"),
        active_section="results",
        symptoms_text=symptoms_text_raw,
        
       
        

        # SDI variables
        sdi_score=sdi_result["normalized_score"],
        sdi_color=sdi_result["color"],
        sdi_alert=sdi_result["alert"],
        sdi_trend=sdi_result["trend"],
        sdi_patterns=sdi_result["patterns"]
     )

   
    elif action == "predict_disease":

        prediction, confidence = predict_disease_logic(symptom_names_lower)

        return render_template(
            "patient_dashboard.html",
            active_section="results",
            prediction=prediction,
            confidence=confidence
        )

    else:
        flash("Invalid action.", "danger")
        return redirect(url_for("patient_dashboard"))
@app.route("/patient_dashboard")
def patient_dashboard():
    return render_template(
        "patient_dashboard.html",
        user_name=session.get("user_name"),
        active_section="symptom",
        ai_data=None,  
        symptoms_data=None,
        recommendations=None,
        doctors=None
    )



# Appointment Routes
@app.route("/book_appointment", methods=["GET", "POST"])
def book_appointment():
    if "user_id" not in session:
        flash("Please log in to continue.", "warning")
        return redirect(url_for("patient_login"))

    user_id = session["user_id"]
    
    # Handle POST request (form submission)
    if request.method == "POST":
        doctor_id = request.form.get("doctor_id")
        appointment_date = request.form.get("appointment_date")
        appointment_time = request.form.get("appointment_time")
        reason = request.form.get("reason", "").strip()

        if not doctor_id or not appointment_date or not appointment_time:
            flash("All fields except 'Reason' are required.", "danger")
            return redirect(url_for("book_appointment"))

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Appointments (user_id, doctor_id, appointment_date, appointment_time, status, reason)
                VALUES (?, ?, ?, ?, 'Pending', ?)
            """, (user_id, doctor_id, appointment_date, appointment_time, reason))
            conn.commit()
            flash("Appointment request submitted successfully! Await doctor approval.", "success")
        except Exception as e:
            flash(f"Error booking appointment: {e}", "danger")
        finally:
            conn.close()

        return redirect(url_for("book_appointment"))
    
    

    conn = get_connection()
    cursor = conn.cursor()
    
    # Fetch all doctors  
    cursor.execute("""
        SELECT doctor_id, name, specialty
        FROM Doctors
        WHERE name IS NOT NULL AND name != ''
        ORDER BY name
    """)
    doctors_rows = cursor.fetchall()
    
    # Convert to list of dicts for easier template access
    all_doctors = []
    for row in doctors_rows:
        all_doctors.append({
            'doctor_id': row['doctor_id'],
            'name': row['name'],
            'specialty': row['specialty'] if row['specialty'] else 'General'
        })
    
    print(f"DEBUG: Found {len(all_doctors)} doctors")  # Debug
    for doc in all_doctors:
        print(f"DEBUG: Doctor - ID: {doc['doctor_id']}, Name: {doc['name']}, Specialty: {doc['specialty']}")
    
    # Fetch user's appointment history 
    cursor.execute("""
        SELECT A.appointment_id, D.name as doctor_name, A.appointment_date, A.appointment_time, 
               A.status, A.reason
        FROM Appointments A
        JOIN Doctors D ON A.doctor_id = D.doctor_id
        WHERE A.user_id = ?
        ORDER BY A.appointment_date DESC, A.appointment_time DESC
    """, (user_id,))
    appointments_rows = cursor.fetchall()
    
    user_appointments = []
    for row in appointments_rows:
        user_appointments.append({
            'appointment_id': row['appointment_id'],
            'doctor_name': row['doctor_name'],
            'appointment_date': row['appointment_date'],
            'appointment_time': row['appointment_time'],
            'status': row['status'],
            'reason': row['reason'] if row['reason'] else ''
        })
    
    conn.close()

    if not all_doctors:
        flash("No doctors available at the moment.", "info")

    return render_template(
        "patient_dashboard.html",
        user_name=session.get("user_name", "Patient"),
        all_doctors=all_doctors,
        user_appointments=user_appointments,
        active_section='appointments',
        selected_doctor_id = request.args.get("doctor_id", type=int)

    )
@app.route("/patient_appointments")
def patient_appointments():
    return redirect(url_for("book_appointment"))

#Chatbot
@app.route("/api_chat", methods=["POST"])
def api_chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip().lower()

        if not user_message:
            return jsonify({"error": "Empty message"}), 400

        
        greetings = ["hi", "hello", "hey", "good morning", "good evening", "good afternoon", "how are you"]
        if any(greet in user_message for greet in greetings):
            return jsonify({"response": "Hello! 👋 I'm your Smart Health Assistant. How are you feeling today?"})

        
        system_instruction = (
            "You are a friendly and knowledgeable AI Health Assistant. "
            "You can discuss topics such as symptoms, diseases, first aid, nutrition, "
            "mental health, wellness, and healthcare advice. "
            "If the user asks something unrelated to health (like programming, jokes, politics, etc.), "
            "reply: 'I'm sorry, I can only talk about health and wellness topics.' "
            "Always provide clear, simple, and supportive answers. "
            "End every health-related response with: "
            "'Note: I’m not a doctor. Please consult a healthcare professional for an accurate diagnosis.'"
        )

        
        payload = {
            "contents": [
                {"parts": [{"text": system_instruction}]},
                {"parts": [{"text": user_message}]}
            ]
        }

        #  4. Send the request to Gemini API
        response = requests.post(
            f"{API_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json=payload
        )

        response.raise_for_status()
        result = response.json()

        #  5. Extract model reply
        model_reply = result["candidates"][0]["content"]["parts"][0]["text"]

        return jsonify({"response": model_reply})

    except requests.exceptions.RequestException as e:
        print(" API Error:", e)
        return jsonify({"error": "Google Gemini API error"}), 500

    except Exception as e:
        print(" Server Error:", e)
        return jsonify({"error": "Internal server error"}), 500



# ML prediction
with open("disease_model.pkl", "rb") as f:
    model = pickle.load(f)

# Load symptom list properly
symptoms = pd.read_csv("symptom_list.csv")["Symptom"].tolist()



def predict_disease_logic(user_symptoms):

    user_symptoms = [s.lower() for s in user_symptoms]

    input_vector = [
        1 if symptom.lower() in user_symptoms else 0
        for symptom in symptoms
    ]

    prediction = model.predict([input_vector])[0]

    confidence = 0
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba([input_vector])
        confidence = round(max(proba[0]) * 100, 2)

    return prediction, confidence

@app.route("/predict", methods=["POST"])
def predict_route():

    data = request.get_json()
    user_symptoms = data.get("symptoms", [])

    prediction, confidence = predict_disease_logic(user_symptoms)

    return jsonify({
        "prediction": prediction,
        "confidence": confidence
    })

if __name__ == "__main__":
    app.run(debug=True)
