import sqlite3
import os

DB_NAME = 'health.db'

def get_specialty_name(specialty_id):
    mapping = {
        1: "General Physician (GP)",
        2: "Otolaryngologist (ENT)",
        3: "Gastroenterologist",
        4: "Dermatologist", 
        5: "Orthopedic"
    }
    return mapping.get(specialty_id, "General Physician (GP)")


def setup_database():

    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f" Existing database {DB_NAME} deleted for fresh setup.")
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    

   

    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Symptoms (
            symptom_id INTEGER PRIMARY KEY AUTOINCREMENT,
            symptom_name TEXT NOT NULL UNIQUE,
            description TEXT,
            doctor_advice TEXT,
            priority INTEGER DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Recommendations (
            rec_id INTEGER PRIMARY KEY AUTOINCREMENT,
            rec_name TEXT NOT NULL,
            rec_type TEXT NOT NULL CHECK(rec_type IN ('Home Remedy', 'Dietary', 'Ayurvedic', 'Tablet')),
            instructions TEXT NOT NULL,
            disclaimer TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Symptom_Recommendation_Mapping (
            mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
            symptom_id INTEGER NOT NULL,
            rec_id INTEGER NOT NULL,
            FOREIGN KEY (symptom_id) REFERENCES Symptoms (symptom_id) ON DELETE CASCADE,
            FOREIGN KEY (rec_id) REFERENCES Recommendations (rec_id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Specialties (
            specialty_id INTEGER PRIMARY KEY AUTOINCREMENT,
            specialty_name TEXT NOT NULL UNIQUE,
            description TEXT
        )
    ''')
    

    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Doctors (
            doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialty_id INTEGER NOT NULL,
            rating REAL,
            experience INTEGER,
            location_lat REAL,
            location_lon REAL,
            availability TEXT,
            email TEXT UNIQUE,
            password TEXT,
            specialty TEXT,           -- ADDED: Required for Flask Profile view
            biography TEXT,           -- ADDED: Required for Flask Profile view
            FOREIGN KEY (specialty_id) REFERENCES Specialties (specialty_id) ON DELETE CASCADE
        )
    ''')

    
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Symptom_Specialty_Mapping (
            map_id INTEGER PRIMARY KEY AUTOINCREMENT,
            symptom_id INTEGER NOT NULL,
            specialty_id INTEGER NOT NULL,
            FOREIGN KEY (symptom_id) REFERENCES Symptoms (symptom_id) ON DELETE CASCADE,
            FOREIGN KEY (specialty_id) REFERENCES Specialties (specialty_id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    password TEXT NOT NULL,
    age INT NOT NULL,
    disease TEXT
)
    ''')
    
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Appointments (
            appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            doctor_id INTEGER,
            appointment_date TEXT,
            appointment_time TEXT,
            status TEXT DEFAULT 'Pending',
            reason TEXT,       
            FOREIGN KEY (user_id) REFERENCES Users(user_id),
            FOREIGN KEY (doctor_id) REFERENCES Doctors(doctor_id)
        )
    ''')
    
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS Health_History(
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    symptom_name TEXT NOT NULL,
    severity INTEGER NOT NULL,
    date_recorded TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);
    ''')

    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS UserRecords (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    description TEXT,
    upload_date TEXT NOT NULL,
    FOREIGN KEY (user_
                   id) REFERENCES Users(user_id)
);
    ''')

    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS SDI_History (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    raw_score REAL,
    normalized_score REAL,
    risk_color TEXT,
    alert_level TEXT,
    trend TEXT,
    date_recorded DATETIME DEFAULT CURRENT_TIMESTAMP
);
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS AI_Assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    symptoms TEXT,
    intensity TEXT,
    risk_level TEXT,
    sdi_score REAL,
    doctor_required BOOLEAN,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);
''')

    cursor.executemany("INSERT INTO Symptoms (symptom_name, description, doctor_advice, priority) VALUES (?, ?, ?, ?)", symptoms)
    cursor.executemany("INSERT INTO Recommendations (rec_name, rec_type, instructions, disclaimer) VALUES (?, ?, ?, ?)", recommendations)
    cursor.executemany("INSERT INTO Specialties (specialty_name, description) VALUES (?, ?)", specialties_data)
    

    cursor.executemany(
        """INSERT INTO Doctors 
        (name, specialty_id, rating, experience, location_lat, location_lon, availability, email, password, specialty, biography) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
        doctors_final_data
    )
    
    cursor.executemany("INSERT INTO Symptom_Recommendation_Mapping (symptom_id, rec_id) VALUES (?, ?)", symptom_recommendation_mappings)
    cursor.executemany("INSERT INTO Symptom_Specialty_Mapping (symptom_id, specialty_id) VALUES (?, ?)", symptom_specialty_mappings)
    
    
    cursor.execute("INSERT INTO Users (user_id, name, email, password,age,disease) VALUES (1, 'Test Patient 1', 'test@user.com', 'pass','32','Diabeates');")
    cursor.execute("INSERT INTO Appointments (user_id, doctor_id, appointment_date, appointment_time, status) VALUES (1, 1, '2025-11-15', '11:00', 'Pending');")

    conn.commit()
    conn.close()

    print(f"\n {DB_NAME} has been created and populated successfully with all data.")


SYMPTOM_PHASE_DATA = {
    "abdominal_pain": {
        "low": "Mild discomfort in abdomen",
        "moderate": "Persistent abdominal pain affecting movement",
        "high": "Severe sharp or sudden abdominal pain"
    },
    "abnormal_menstruation": {
    "low": "Slight irregular cycle",
    "moderate": "Frequent irregular or delayed cycle",
    "high": "Heavy prolonged bleeding or severe cramps"
},

"acidity": {
    "low": "Occasional heartburn",
    "moderate": "Frequent burning sensation after meals",
    "high": "Severe burning with chest pain or vomiting"
},

"acute_liver_failure": {
    "low": "Mild jaundice symptoms",
    "moderate": "Severe fatigue with yellow skin",
    "high": "Confusion or liver-related coma"
},

"altered_sensorium": {
    "low": "Mild confusion",
    "moderate": "Disorientation to time/place",
    "high": "Loss of awareness or unresponsiveness"
},

"anxiety": {
    "low": "Occasional nervousness",
    "moderate": "Frequent anxiety episodes",
    "high": "Panic attack with breathing difficulty"
},

"back_pain": {
    "low": "Mild muscle stiffness",
    "moderate": "Persistent back pain limiting movement",
    "high": "Severe pain preventing standing or walking"
},

"belly_pain": {
    "low": "Light stomach discomfort",
    "moderate": "Persistent dull belly pain",
    "high": "Severe sharp belly pain with vomiting"
},

"blackheads": {
    "low": "Few scattered blackheads",
    "moderate": "Multiple clusters on face",
    "high": "Painful inflamed blackhead infections"
},

"bladder_discomfort": {
    "low": "Mild irritation during urination",
    "moderate": "Persistent burning sensation",
    "high": "Severe pain with blood in urine"
},

"blister": {
    "low": "Small painless blister",
    "moderate": "Multiple painful blisters",
    "high": "Infected spreading blisters"
},

"blood_in_sputum": {
    "low": "Small streaks of blood",
    "moderate": "Frequent blood-mixed sputum",
    "high": "Large amount of blood while coughing"
},

"bloody_stool": {
    "low": "Occasional small traces",
    "moderate": "Repeated visible bleeding",
    "high": "Heavy rectal bleeding"
},

"blurred_and_distorted_vision": {
    "low": "Temporary mild blurring",
    "moderate": "Persistent distorted vision",
    "high": "Sudden severe visual loss"
},

"breathlessness": {
    "low": "Shortness of breath during exertion",
    "moderate": "Breathlessness while walking",
    "high": "Breathing difficulty at rest or gasping"
},

"brittle_nails": {
    "low": "Slight nail weakness",
    "moderate": "Frequent nail breakage",
    "high": "Nails separating from nail bed"
},

"bruising": {
    "low": "Small occasional bruises",
    "moderate": "Frequent unexplained bruising",
    "high": "Large painful deep bruises"
},

"burning_micturition": {
    "low": "Mild burning sensation",
    "moderate": "Painful urination",
    "high": "Severe burning with fever"
},

"chest_pain": {
    "low": "Mild chest discomfort",
    "moderate": "Persistent dull chest pain",
    "high": "Sudden crushing chest pain"
},

"chills": {
    "low": "Mild cold sensation",
    "moderate": "Repeated shivering episodes",
    "high": "Violent shaking chills with fever"
},

"cold_hands_and_feets": {
    "low": "Occasional cold sensation",
    "moderate": "Frequent numb cold fingers/toes",
    "high": "Blue discoloration of extremities"
},

"coma": {
    "low": "Reduced response to stimuli",
    "moderate": "Very limited conscious response",
    "high": "Complete unconsciousness"
},

"congestion": {
    "low": "Mild nasal blockage",
    "moderate": "Persistent sinus congestion",
    "high": "Blocked breathing through nose"
},

"constipation": {
    "low": "Difficulty passing stool occasionally",
    "moderate": "No bowel movement for 3 days",
    "high": "Severe abdominal pain with constipation"
},

"continuous_feel_of_urine": {
    "low": "Occasional urge",
    "moderate": "Frequent urge without much urine",
    "high": "Constant urge with pain"
},

"continuous_sneezing": {
    "low": "Few sneezing episodes",
    "moderate": "Repeated sneezing throughout day",
    "high": "Uncontrolled severe sneezing"
},

"cough": {
    "low": "Occasional mild cough",
    "moderate": "Persistent cough for several days",
    "high": "Severe coughing interfering with breathing"
},

"cramps": {
    "low": "Mild muscle cramps",
    "moderate": "Frequent painful cramps",
    "high": "Severe muscle tightening restricting movement"
},

"dark_urine": {
    "low": "Slight dark color",
    "moderate": "Dark brown urine",
    "high": "Very dark urine with pain or jaundice"
},

"dehydration": {
    "low": "Mild dryness of mouth",
    "moderate": "Dizziness with thirst",
    "high": "Confusion or fainting due to dehydration"
},

"depression": {
    "low": "Low mood occasionally",
    "moderate": "Persistent sadness affecting work",
    "high": "Hopelessness or suicidal thoughts"
},

"diarrhoea": {
    "low": "1-2 loose stools",
    "moderate": "3-5 loose stools in a day",
    "high": "Continuous diarrhea with dehydration"
},

"dischromic_patches": {
    "low": "Small skin color changes",
    "moderate": "Spreading patches",
    "high": "Large visible discolored areas"
},

"distention_of_abdomen": {
    "low": "Mild bloating",
    "moderate": "Visible abdominal swelling",
    "high": "Severe tight abdominal swelling"
},

"dizziness": {
    "low": "Occasional lightheadedness",
    "moderate": "Frequent dizziness during activity",
    "high": "Sudden spinning sensation with fall risk"
},

"nodal_skin_eruptions": {
    "low": "Few small nodular eruptions",
    "moderate": "Multiple painful eruptions",
    "high": "Widespread inflamed nodules"
},

"obesity": {
    "low": "BMI slightly above normal",
    "moderate": "BMI 30–35 with fatigue",
    "high": "Severe obesity with breathing issues"
},

"pain_behind_the_eyes": {
    "low": "Mild eye pressure",
    "moderate": "Persistent aching behind eyes",
    "high": "Severe sharp eye pain with vision issues"
},

"pain_during_bowel_movements": {
    "low": "Mild discomfort during passing stool",
    "moderate": "Persistent pain each time",
    "high": "Severe sharp pain with bleeding"
},

"pain_in_anal_region": {
    "low": "Mild irritation",
    "moderate": "Persistent burning pain",
    "high": "Severe pain with swelling or bleeding"
},

"painful_walking": {
    "low": "Mild discomfort while walking",
    "moderate": "Pain limiting walking distance",
    "high": "Unable to walk without assistance"
},

"palpitations": {
    "low": "Occasional awareness of heartbeat",
    "moderate": "Frequent rapid heartbeat episodes",
    "high": "Continuous racing heart with dizziness"
},

"passage_of_gases": {
    "low": "Occasional gas",
    "moderate": "Frequent bloating and gas",
    "high": "Severe abdominal discomfort due to gas"
},

"patches_in_throat": {
    "low": "Small white patches",
    "moderate": "Painful throat patches",
    "high": "Severe throat swelling with breathing issues"
},

"phlegm": {
    "low": "Small amount of mucus",
    "moderate": "Frequent mucus production",
    "high": "Thick colored mucus with blood"
},

"polyuria": {
    "low": "Slight increase in urination",
    "moderate": "Frequent urination especially at night",
    "high": "Excessive urination with dehydration"
},

"prominent_veins_on_calf": {
    "low": "Visible veins without pain",
    "moderate": "Mild swelling with vein prominence",
    "high": "Painful swollen veins"
},

"puffy_face_and_eyes": {
    "low": "Mild morning puffiness",
    "moderate": "Noticeable swelling throughout day",
    "high": "Severe facial swelling with breathing issues"
},

"pus_filled_pimples": {
    "low": "Few small pimples",
    "moderate": "Multiple infected pimples",
    "high": "Painful spreading skin infection"
},

"receiving_blood_transfusion": {
    "low": "Mild reaction symptoms",
    "moderate": "Fever or rash after transfusion",
    "high": "Severe allergic or shock reaction"
},

"receiving_unsterile_injections": {
    "low": "No obvious symptoms",
    "moderate": "Local swelling",
    "high": "Fever or severe infection"
},

"red_sore_around_nose": {
    "low": "Mild skin irritation",
    "moderate": "Painful sore area",
    "high": "Infected spreading sore"
},

"red_spots_over_body": {
    "low": "Few scattered spots",
    "moderate": "Spreading rash",
    "high": "Whole body rash with fever"
},

"redness_of_eyes": {
    "low": "Slight redness",
    "moderate": "Persistent red eyes",
    "high": "Severe redness with vision pain"
},

"restlessness": {
    "low": "Occasional uneasiness",
    "moderate": "Difficulty staying still",
    "high": "Severe agitation with panic"
},

"runny_nose": {
    "low": "Mild nasal discharge",
    "moderate": "Continuous runny nose",
    "high": "Heavy discharge with breathing difficulty"
},

"rusty_sputum": {
    "low": "Small colored sputum",
    "moderate": "Persistent rusty mucus",
    "high": "Large thick bloody sputum"
},

"scurring": {
    "low": "Minor skin scaling",
    "moderate": "Noticeable skin peeling",
    "high": "Severe cracked bleeding skin"
},

"shivering": {
    "low": "Light shivering",
    "moderate": "Repeated shaking chills",
    "high": "Severe uncontrollable shaking"
},

"silver_like_dusting": {
    "low": "Minor dry skin patches",
    "moderate": "Visible flaky skin",
    "high": "Severe scaling with itching"
},

"sinus_pressure": {
    "low": "Mild facial pressure",
    "moderate": "Persistent sinus ache",
    "high": "Severe pressure with headache"
},

"skin_peeling": {
    "low": "Small dry peeling",
    "moderate": "Large peeling areas",
    "high": "Severe raw painful skin"
},

"skin_rash": {
    "low": "Small rash area",
    "moderate": "Spreading itchy rash",
    "high": "Widespread painful rash"
},

"slurred_speech": {
    "low": "Occasional speech difficulty",
    "moderate": "Persistent unclear speech",
    "high": "Sudden inability to speak properly"
},

"small_dents_in_nails": {
    "low": "Few nail dents",
    "moderate": "Multiple visible dents",
    "high": "Severe nail deformity"
},

"spinning_movements": {
    "low": "Mild dizziness episodes",
    "moderate": "Frequent spinning sensation",
    "high": "Severe vertigo with fall risk"
},

"spotting_urination": {
    "low": "Occasional spotting",
    "moderate": "Frequent spotting during urination",
    "high": "Heavy bleeding in urine"
},

"stiff_neck": {
    "low": "Mild neck stiffness",
    "moderate": "Painful limited movement",
    "high": "Severe stiffness with fever"
},

"stomach_bleeding": {
    "low": "Minor internal discomfort",
    "moderate": "Vomiting blood traces",
    "high": "Heavy internal bleeding"
},

"drying_and_tingling_lips": {
    "low": "Mild lip dryness",
    "moderate": "Persistent dryness with tingling",
    "high": "Painful cracked lips with swelling"
},

"enlarged_thyroid": {
    "low": "Slight visible neck swelling",
    "moderate": "Noticeable swelling affecting swallowing",
    "high": "Severe swelling causing breathing difficulty"
},

"excessive_hunger": {
    "low": "Frequent hunger between meals",
    "moderate": "Increased appetite with weight gain",
    "high": "Extreme hunger with dizziness"
},

"extra_marital_contacts": {
    "low": "No symptoms",
    "moderate": "Mild infection symptoms",
    "high": "Severe STD-related symptoms"
},

"family_history": {
    "low": "Mild genetic risk",
    "moderate": "Strong family disease history",
    "high": "Multiple early-onset family illnesses"
},

"fast_heart_rate": {
    "low": "Temporary increased heart rate",
    "moderate": "Persistent tachycardia",
    "high": "Rapid heart rate with dizziness or chest pain"
},

"fatigue": {
    "low": "Mild tiredness after activity",
    "moderate": "Persistent fatigue all day",
    "high": "Extreme exhaustion limiting activity"
},

"fluid_overload": {
    "low": "Mild swelling in legs",
    "moderate": "Noticeable body swelling",
    "high": "Severe swelling with breathing difficulty"
},

"foul_smell_of_urine": {
    "low": "Slight unusual smell",
    "moderate": "Persistent strong odor",
    "high": "Foul smell with pain and fever"
},

"headache": {
    "low": "Mild tolerable headache",
    "moderate": "Persistent pain affecting concentration",
    "high": "Severe or sudden worst headache"
},

"high_fever": {
    "low": "Temperature below 100°F",
    "moderate": "100–102°F",
    "high": "Above 102°F or lasting more than 3 days"
},

"hip_joint_pain": {
    "low": "Mild discomfort in hip",
    "moderate": "Persistent pain while walking",
    "high": "Severe pain restricting movement"
},

"history_of_alcohol_consumption": {
    "low": "Occasional use",
    "moderate": "Frequent alcohol intake",
    "high": "Heavy long-term consumption with health impact"
},

"increased_appetite": {
    "low": "Eating slightly more than normal",
    "moderate": "Frequent hunger with weight gain",
    "high": "Extreme overeating with metabolic issues"
},

"indigestion": {
    "low": "Occasional bloating",
    "moderate": "Frequent stomach discomfort after meals",
    "high": "Severe upper abdominal pain"
},

"inflammatory_nails": {
    "low": "Mild redness around nail",
    "moderate": "Swollen painful nail folds",
    "high": "Severe infected nail area"
},

"internal_itching": {
    "low": "Mild itching sensation",
    "moderate": "Persistent itching",
    "high": "Severe itching interfering with sleep"
},

"irregular_sugar_level": {
    "low": "Slight blood sugar changes",
    "moderate": "Frequent sugar spikes",
    "high": "Very high or very low sugar causing dizziness"
},

"irritability": {
    "low": "Occasional mood changes",
    "moderate": "Frequent irritability",
    "high": "Severe mood swings affecting relationships"
},

"irritation_in_anus": {
    "low": "Mild itching",
    "moderate": "Persistent burning sensation",
    "high": "Severe pain with bleeding"
},

"itching": {
    "low": "Mild localized itching",
    "moderate": "Frequent itching in multiple areas",
    "high": "Severe itching with skin damage"
},

"joint_pain": {
    "low": "Mild discomfort",
    "moderate": "Persistent pain with stiffness",
    "high": "Severe joint swelling and pain"
},

"knee_pain": {
    "low": "Mild pain while bending",
    "moderate": "Pain while walking or climbing stairs",
    "high": "Severe pain preventing walking"
},

"lack_of_concentration": {
    "low": "Occasional difficulty focusing",
    "moderate": "Frequent distraction",
    "high": "Severe inability to complete tasks"
},

"lethargy": {
    "low": "Mild sluggishness",
    "moderate": "Low energy throughout day",
    "high": "Extreme inactivity or weakness"
},

"loss_of_appetite": {
    "low": "Reduced interest in food",
    "moderate": "Skipping meals frequently",
    "high": "Almost no food intake"
},

"loss_of_balance": {
    "low": "Minor imbalance occasionally",
    "moderate": "Frequent stumbling",
    "high": "Falling due to imbalance"
},

"loss_of_smell": {
    "low": "Partial loss",
    "moderate": "Significant smell reduction",
    "high": "Complete smell loss"
},

"malaise": {
    "low": "General mild discomfort",
    "moderate": "Persistent unwell feeling",
    "high": "Severe weakness with inability to work"
},

"mild_fever": {
    "low": "99–100°F",
    "moderate": "100–101°F lasting days",
    "high": "Above 101°F with chills"
},

"mood_swings": {
    "low": "Occasional mood variation",
    "moderate": "Frequent unpredictable mood changes",
    "high": "Severe mood instability affecting behavior"
},

"movement_stiffness": {
    "low": "Mild stiffness after rest",
    "moderate": "Reduced movement flexibility",
    "high": "Severe stiffness limiting motion"
},

"mucoid_sputum": {
    "low": "Small amount of mucus",
    "moderate": "Frequent mucus production",
    "high": "Thick sticky mucus with breathing difficulty"
},

"muscle_pain": {
    "low": "Mild muscle soreness",
    "moderate": "Persistent pain affecting activity",
    "high": "Severe muscle pain limiting movement"
},

"muscle_wasting": {
    "low": "Minor muscle loss",
    "moderate": "Noticeable muscle thinning",
    "high": "Severe muscle shrinkage with weakness"
},

"muscle_weakness": {
    "low": "Mild weakness during activity",
    "moderate": "Difficulty lifting objects",
    "high": "Inability to perform basic movements"
},

"nausea": {
    "low": "Mild queasiness",
    "moderate": "Frequent nausea episodes",
    "high": "Severe nausea with vomiting"
},

"stomach_pain": {
    "low": "Mild stomach discomfort",
    "moderate": "Persistent stomach ache",
    "high": "Severe sharp stomach pain"
},

"sunken_eyes": {
    "low": "Slight hollow appearance",
    "moderate": "Noticeably sunken with fatigue",
    "high": "Deeply sunken with dehydration signs"
},

"sweating": {
    "low": "Mild sweating",
    "moderate": "Frequent sweating without exertion",
    "high": "Excessive sweating with weakness"
},

"swelled_lymph_nodes": {
    "low": "Small painless swelling",
    "moderate": "Noticeable tender swelling",
    "high": "Large painful swollen nodes with fever"
},

"swelling_joints": {
    "low": "Mild joint puffiness",
    "moderate": "Visible joint swelling",
    "high": "Severe swollen painful joints"
},

"swelling_of_stomach": {
    "low": "Mild bloating",
    "moderate": "Visible abdominal swelling",
    "high": "Severe tight swollen abdomen"
},

"swollen_blood_vessels": {
    "low": "Slight visible veins",
    "moderate": "Noticeably enlarged veins",
    "high": "Painful swollen bulging vessels"
},

"swollen_extremeties": {
    "low": "Mild swelling in hands/feet",
    "moderate": "Persistent swelling",
    "high": "Severe swelling limiting movement"
},

"swollen_legs": {
    "low": "Mild leg swelling",
    "moderate": "Swollen legs with discomfort",
    "high": "Severe swelling with pain or breathing issues"
},

"throat_irritation": {
    "low": "Mild scratchy throat",
    "moderate": "Persistent irritation",
    "high": "Severe pain with swallowing difficulty"
},

"toxic_look_(typhos)": {
    "low": "Mild tired appearance",
    "moderate": "Weakness with fever",
    "high": "Very ill appearance with confusion"
},

"ulcers_on_tongue": {
    "low": "Small painless ulcer",
    "moderate": "Painful mouth ulcers",
    "high": "Multiple large painful ulcers"
},

"unsteadiness": {
    "low": "Slight balance issue",
    "moderate": "Frequent imbalance",
    "high": "Severe instability with fall risk"
},

"visual_disturbances": {
    "low": "Occasional blurred vision",
    "moderate": "Persistent visual changes",
    "high": "Sudden severe loss of vision"
},

"vomiting": {
    "low": "1–2 vomiting episodes",
    "moderate": "Repeated vomiting",
    "high": "Continuous vomiting with dehydration"
},

"watering_from_eyes": {
    "low": "Mild eye tearing",
    "moderate": "Frequent watery eyes",
    "high": "Excessive tearing with pain"
},

"weakness_in_limbs": {
    "low": "Mild limb fatigue",
    "moderate": "Difficulty lifting limbs",
    "high": "Severe weakness affecting movement"
},

"weakness_of_one_body_side": {
    "low": "Mild imbalance on one side",
    "moderate": "Noticeable weakness in one arm/leg",
    "high": "Sudden paralysis of one side"
},

"weight_gain": {
    "low": "Small gradual gain",
    "moderate": "Noticeable rapid gain",
    "high": "Severe weight increase with swelling"
},

"weight_loss": {
    "low": "Small unintended weight loss",
    "moderate": "Noticeable weight reduction",
    "high": "Rapid extreme weight loss"
},

"yellow_crust_ooze": {
    "low": "Small crusty patch",
    "moderate": "Spreading crust formation",
    "high": "Severe infected oozing sores"
},

"yellow_urine": {
    "low": "Dark yellow urine",
    "moderate": "Persistent deep yellow color",
    "high": "Very dark urine with pain"
},

"yellowing_of_eyes": {
    "low": "Slight yellow tint",
    "moderate": "Noticeable yellow color",
    "high": "Bright yellow eyes with fatigue"
},

    "yellowish_skin": {
        "low": "Mild yellow tone",
        "moderate": "Clear jaundice appearance",
        "high": "Severe yellow skin with weakness"
    }
}

symptoms = [
    ('Abdominal Pain', 'Mild discomfort in abdomen', 'Consult GP', 1),
    ('Acidity', 'Occasional heartburn', 'Dietary changes recommended', 2),
    ('Anxiety', 'Occasional nervousness', 'Consult GP', 1),
    ('Back Pain', 'Mild muscle stiffness', 'Rest and physiotherapy', 2),
    ('Breathing Difficulty', 'Shortness of breath during exertion', 'Consult GP', 2),
    ('Chest Pain', 'Mild chest discomfort', 'Consult immediately', 3),
    ('Cold/Cough', 'Occasional mild cough', 'Home remedies', 1),
    ('Fatigue', 'Mild tiredness after activity', 'Rest and hydration', 1),
    ('Headache', 'Mild tolerable headache', 'Rest', 1),
    ('High Fever', 'Temperature above 100°F', 'Consult GP', 2)
]
# -----------------------------
# AUTO SYMPTOM → SPECIALTY MAPPING
# -----------------------------

symptom_specialty_mappings = []

# Specialty IDs
GP = 1
ENT = 2
GASTRO = 3
DERMA = 4
ORTHO = 5

def detect_specialty(symptom_name):
    name = symptom_name.lower()

    # Skin related → Dermatologist
    if any(word in name for word in [
        "rash", "itch", "skin", "pimple", "blister",
        "red_spots", "yellow_crust", "scurring",
        "blackheads", "nodal_skin"
    ]):
        return DERMA

    # Stomach / digestive → Gastro
    if any(word in name for word in [
        "stomach", "abdominal", "acidity", "indigestion",
        "gas", "vomit", "diarrhoea", "constipation",
        "belly", "liver"
    ]):
        return GASTRO

    # Bone / Joint → Orthopedic
    if any(word in name for word in [
        "back", "joint", "knee", "hip",
        "neck", "movement", "painful_walking"
    ]):
        return ORTHO

    # ENT related
    if any(word in name for word in [
        "nose", "ear", "throat", "sneeze",
        "congestion", "sinus", "voice"
    ]):
        return ENT

    # Default → General Physician
    return GP


# Generate automatic mapping
for index, symptom in enumerate(symptoms, start=1):
    specialty_id = detect_specialty(symptom[0])
    symptom_specialty_mappings.append((index, specialty_id))
recommendations = [
        ('Ginger Tea', 'Home Remedy', 'Boil fresh ginger slices in water for 10 minutes. Strain and drink warm.', 'Avoid if you have a bleeding disorder.'),
        ('Stay Hydrated', 'Dietary', 'Drink at least 8-10 glasses of water throughout the day.', None),
        ('Paracetamol', 'Tablet', 'Take one 500mg tablet. Do not exceed 4 tablets in 24 hours.', 'Consult a doctor if symptoms persist.'),
        ('Honey and Lemon', 'Home Remedy', 'Mix one tablespoon of honey and a few drops of lemon juice in warm water and sip slowly.', 'Do not give honey to children under 1 year old.'),
        ('Avipattikar Churna', 'Ayurvedic', 'Take 1-2 teaspoons with lukewarm water before meals.', 'Consult an Ayurvedic practitioner before use.'),
        ('Cold Milk', 'Dietary', 'Drink a glass of cold, plain milk to get instant relief from burning sensation.', 'Avoid if you are lactose intolerant.'),
        ('Tepid Sponge Bath', 'Home Remedy', 'Wipe the body with lukewarm water for cooling.', 'Avoid ice-cold water, as it can cause shivering.'),
        ('Rest and Ice', 'Home Remedy', 'Rest the affected joint and apply a cold pack for 15-20 minutes, 3 times a day.', 'Do not apply ice directly to the skin.'),
        ('Naproxen', 'Tablet', 'Take one 250mg tablet every 8 hours.', 'Consult a doctor if you have stomach problems or heart disease.'),
        ('Turmeric Milk', 'Dietary', 'Mix 1 teaspoon of turmeric powder in warm milk and drink before bed.', 'N/A')
            ]
    
specialties_data = [
        ('General Physician (GP)', 'A doctor who provides routine care and manages common illnesses.'), # ID 1
        ('Otolaryngologist (ENT)', 'Specializes in the ear, nose, and throat.'), # ID 2
        ('Gastroenterologist', 'Specializes in the digestive system and its disorders.'), # ID 3
        ('Dermatologist', 'Specializes in conditions of the skin, hair, and nails.'), # ID 4 
        ('Orthopedic', 'Specializes in bones and joints.') # ID 5
        ]
    
    #  doctors_data format: (Name, specialty_id, rating, experience, lat, lon, availability, email, password)
doctors_raw_data = [
        ('Dr. Priya Sharma', 1, 4.8, 12, 18.5204, 73.8567, 'Online/10:00-14:00', 'priya@gmail.com', '1234'),
        ('Dr. Anish Menon', 2, 4.5, 8, 18.5195, 73.8553, 'Offline/16:00-20:00', 'anish@gmail.com', 'abcd'),
        ('Dr. Sneha Varma', 3, 4.9, 18, 18.5220, 73.8580, 'Online/11:00-13:00', 'sneha@gmail.com', '5678'),
        ('Dr. Rohit Singh', 1, 4.2, 5, 18.5208, 73.8560, 'Offline/17:00-21:00', 'rohit@gmail.com', '9999'),
        ('Dr. Kabir Jain', 2, 4.7, 10, 18.5210, 73.8570, 'Online/15:00-17:00', 'kabir@gmail.com', '4321'),
        ('Dr. Sania Reddy', 5, 4.6, 9, 18.5225, 73.8585, 'Offline/09:00-14:00', 'sania@gmail.com', '2468')
        ]
    
doctors_final_data = []
for data in doctors_raw_data:
        specialty_text = get_specialty_name(data[1])
        # Create a detailed biography text using the data
        biography = f"{data[0]} is a board-certified {specialty_text} with {data[3]} years of experience. Available {data[6].split('/')[0]}."
        
        # New Tuple: (name, specialty_id, rating, experience, lat, lon, availability, email, password, specialty_TEXT, biography_TEXT)
        doctors_final_data.append(data + (specialty_text, biography))
    
symptom_recommendation_mappings = [
        (1, 1), (1, 2), (1, 3),
        (2, 1), (2, 4),
        (3, 5), (3, 6),
        (4, 3), (4, 7), (4, 10),
        (5, 8), (5, 9), (5, 10)
        ]
    



if __name__ == "__main__":
    setup_database()
