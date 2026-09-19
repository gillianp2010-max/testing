"""Generate 10 SQLite databases with synthetic vet practice data."""
import sqlite3
import random
import os
from datetime import datetime, timedelta

PRACTICES = [
    {"id": "vet_practice_01", "name": "Pawsitive Care Veterinary Clinic", "city": "Austin", "state": "TX", "phone_prefix": "512"},
    {"id": "vet_practice_02", "name": "Whiskers & Wings Animal Hospital", "city": "Seattle", "state": "WA", "phone_prefix": "206"},
    {"id": "vet_practice_03", "name": "Heartland Veterinary Partners", "city": "Denver", "state": "CO", "phone_prefix": "303"},
    {"id": "vet_practice_04", "name": "Bluebell Pet Wellness Center", "city": "Portland", "state": "OR", "phone_prefix": "503"},
    {"id": "vet_practice_05", "name": "Sunrise Animal Care Clinic", "city": "Phoenix", "state": "AZ", "phone_prefix": "602"},
    {"id": "vet_practice_06", "name": "Companion Care Veterinary Group", "city": "Atlanta", "state": "GA", "phone_prefix": "404"},
    {"id": "vet_practice_07", "name": "Greenfield Veterinary Hospital", "city": "Madison", "state": "WI", "phone_prefix": "608"},
    {"id": "vet_practice_08", "name": "Coral Reef Animal Clinic", "city": "Miami", "state": "FL", "phone_prefix": "305"},
    {"id": "vet_practice_09", "name": "Mountain View Pet Hospital", "city": "Boulder", "state": "CO", "phone_prefix": "720"},
    {"id": "vet_practice_10", "name": "Riverside Veterinary Clinic", "city": "Sacramento", "state": "CA", "phone_prefix": "916"},
]

FIRST_NAMES = ["James","Mary","John","Patricia","Robert","Jennifer","Michael","Linda","William","Elizabeth",
               "David","Barbara","Richard","Susan","Joseph","Jessica","Thomas","Sarah","Charles","Karen",
               "Christopher","Nancy","Daniel","Lisa","Matthew","Margaret","Anthony","Sandra","Mark","Ashley",
               "Donald","Kimberly","Steven","Emily","Paul","Donna","Andrew","Michelle","Joshua","Carol"]
LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
              "Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin",
              "Lee","Perez","Thompson","White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson"]
PET_NAMES = ["Bella","Max","Luna","Charlie","Lucy","Cooper","Bailey","Daisy","Rocky","Milo",
             "Sadie","Bear","Lola","Duke","Coco","Buddy","Molly","Oliver","Maggie","Tucker",
             "Sophie","Shadow","Chloe","Riley","Zeus","Lily","Jack","Dexter","Stella","Rex",
             "Zoe","Gizmo","Nala","Mocha","Winston","Penny","Oreo","Gracie","Bentley","Ruby"]
SPECIES = ["Dog","Cat","Bird","Rabbit","Guinea Pig","Hamster","Turtle","Ferret","Lizard","Snake"]
BREEDS = {
    "Dog": ["Labrador Retriever","German Shepherd","Golden Retriever","French Bulldog","Beagle","Poodle","Rottweiler","Yorkshire Terrier","Boxer","Dachshund"],
    "Cat": ["Persian","Maine Coon","Siamese","Ragdoll","Bengal","British Shorthair","American Shorthair","Scottish Fold","Sphynx","Abyssinian"],
    "Bird": ["Parakeet","Cockatiel","Canary","Lovebird","African Grey","Conure","Finch","Cockatoo","Macaw","Quaker Parrot"],
    "Rabbit": ["Holland Lop","Netherland Dwarf","Mini Lop","Lionhead","Flemish Giant","Rex","Dutch","English Spot"],
    "Guinea Pig": ["American","Abyssinian","Peruvian","Silkie","Teddy","Texel","Coronet","Skinny Pig"],
    "Hamster": ["Syrian","Roborovski","Winter White","Campbell's Dwarf","Chinese"],
    "Turtle": ["Red-Eared Slider","Box Turtle","Painted Turtle","Russian Tortoise","Hermann's Tortoise"],
    "Ferret": ["Sable","Albino","Cinnamon","Silver Mitt","Black Self","Champagne"],
    "Lizard": ["Bearded Dragon","Leopard Gecko","Crested Gecko","Blue-Tongue Skink","Iguana"],
    "Snake": ["Corn Snake","Ball Python","King Snake","Milk Snake","Hognose"],
}
VET_FIRST = ["Dr. Emily","Dr. Michael","Dr. Sarah","Dr. David","Dr. Jessica","Dr. Robert","Dr. Lisa","Dr. James",
             "Dr. Jennifer","Dr. Christopher","Dr. Amanda","Dr. Brian","Dr. Nicole","Dr. Kevin","Dr. Rachel"]
VET_LAST = ["Carter","Mitchell","Nguyen","Patel","Garcia","Thompson","Anderson","Roberts","Lee","Walker",
            "Hall","Allen","Young","King","Wright","Lopez","Hill","Scott","Green","Adams"]
TREATMENT_TYPES = [
    "Annual Wellness Exam","Vaccination","Dental Cleaning","Spay/Neuter Surgery","Microchip Implantation",
    "X-Ray Imaging","Blood Work","Wound Treatment","Parasite Treatment","Ear Cleaning",
    "Skin Allergy Treatment","Orthopedic Consultation","Behavioral Consultation","Emergency Care",
    "Weight Management Consultation","Senior Health Screening","Eye Examination","Heartworm Test",
    "Feline Leukemia Test","Nutritional Counseling"
]
MEDICATIONS = [
    ("Amoxicillin","Antibiotic",15.00),("Rimadyl","Anti-inflammatory",25.00),("Apoquel","Allergy Medication",45.00),
    ("Frontline Plus","Flea/Tick Prevention",35.00),("Heartgard Plus","Heartworm Prevention",30.00),
    ("Metronidazole","Antibiotic",12.00),("Prednisolone","Steroid",18.00),("Gabapentin","Pain Management",22.00),
    ("Clavamox","Antibiotic",28.00),("Tramadol","Pain Management",20.00),("Cerenia","Anti-nausea",32.00),
    ("Revolution","Parasite Prevention",40.00),("Trazodone","Behavioral Medication",16.00),
    ("Meloxicam","Anti-inflammatory",14.00),("Doxycycline","Antibiotic",19.00),
]
APPOINTMENT_REASONS = [
    "Routine checkup","Vaccination booster","Not eating","Limping","Skin irritation",
    "Annual exam","Dental issues","Ear infection","Eye discharge","Vomiting",
    "Diarrhea","Weight loss","Spay/neuter follow-up","Behavioral concerns","Senior wellness check",
    "Nail trimming","Microchip scan","Post-surgery checkup","Allergy symptoms","Lethargy"
]
APPOINTMENT_STATUSES = ["Completed","Completed","Completed","Completed","Cancelled","No-show","Scheduled","Completed"]

SCHEMA_INFO = {
    "veterinarians": ["vet_id","first_name","last_name","specialization","hire_date","email","phone","license_number"],
    "owners": ["owner_id","first_name","last_name","email","phone","address","city","state","zip_code","registered_date"],
    "patients": ["patient_id","owner_id","name","species","breed","birth_date","gender","weight_kg","microchip_id","status"],
    "appointments": ["appointment_id","patient_id","vet_id","appointment_date","appointment_time","reason","status","notes"],
    "treatments": ["treatment_id","appointment_id","treatment_type","description","cost"],
    "prescriptions": ["prescription_id","appointment_id","medication_name","medication_type","dosage","duration","cost"],
    "invoices": ["invoice_id","owner_id","appointment_id","invoice_date","total_amount","payment_status","payment_method"],
}


def _generate_phone(prefix):
    return f"{prefix}-{random.randint(100,999)}-{random.randint(1000,9999)}"


def _random_date(start_date, end_date):
    delta = (end_date - start_date).days
    return start_date + timedelta(days=random.randint(0, max(delta, 0)))


def _create_practice_database(practice, db_dir):
    db_path = os.path.join(db_dir, f"{practice['id']}.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE veterinarians (
        vet_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        specialization TEXT,
        hire_date TEXT,
        email TEXT,
        phone TEXT,
        license_number TEXT UNIQUE
    );
    CREATE TABLE owners (
        owner_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        address TEXT,
        city TEXT,
        state TEXT,
        zip_code TEXT,
        registered_date TEXT
    );
    CREATE TABLE patients (
        patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        species TEXT NOT NULL,
        breed TEXT,
        birth_date TEXT,
        gender TEXT,
        weight_kg REAL,
        microchip_id TEXT,
        status TEXT DEFAULT 'Active',
        FOREIGN KEY (owner_id) REFERENCES owners(owner_id)
    );
    CREATE TABLE appointments (
        appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        vet_id INTEGER NOT NULL,
        appointment_date TEXT NOT NULL,
        appointment_time TEXT NOT NULL,
        reason TEXT,
        status TEXT,
        notes TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY (vet_id) REFERENCES veterinarians(vet_id)
    );
    CREATE TABLE treatments (
        treatment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id INTEGER NOT NULL,
        treatment_type TEXT NOT NULL,
        description TEXT,
        cost REAL,
        FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
    );
    CREATE TABLE prescriptions (
        prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id INTEGER NOT NULL,
        medication_name TEXT NOT NULL,
        medication_type TEXT,
        dosage TEXT,
        duration TEXT,
        cost REAL,
        FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
    );
    CREATE TABLE invoices (
        invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        appointment_id INTEGER NOT NULL,
        invoice_date TEXT NOT NULL,
        total_amount REAL,
        payment_status TEXT,
        payment_method TEXT,
        FOREIGN KEY (owner_id) REFERENCES owners(owner_id),
        FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
    );
    """)

    num_vets = random.randint(5, 8)
    used_vet_names = set()
    specializations = ["General Practice","Surgery","Dermatology","Cardiology","Dentistry","Emergency Medicine","Internal Medicine","Exotic Animals","Orthopedics","Ophthalmology"]
    for _ in range(num_vets):
        while True:
            vf = random.choice(VET_FIRST); vl = random.choice(VET_LAST)
            full = f"{vf} {vl}"
            if full not in used_vet_names:
                used_vet_names.add(full); break
        spec = random.choice(specializations)
        hire = _random_date(datetime(2010,1,1), datetime(2023,12,31)).strftime("%Y-%m-%d")
        email = f"{vf.replace('Dr. ','').lower()}.{vl.lower()}@{practice['name'].split()[0].lower()}vet.com"
        phone = _generate_phone(practice["phone_prefix"])
        license_num = f"VET-{practice['state']}-{random.randint(10000,99999)}"
        cursor.execute("INSERT INTO veterinarians (first_name,last_name,specialization,hire_date,email,phone,license_number) VALUES (?,?,?,?,?,?,?)",
                       (vf, vl, spec, hire, email, phone, license_num))

    num_owners = random.randint(200, 400)
    owner_ids = []
    for _ in range(num_owners):
        fn = random.choice(FIRST_NAMES); ln = random.choice(LAST_NAMES)
        email = f"{fn.lower()}.{ln.lower()}{random.randint(1,999)}@email.com"
        phone = _generate_phone(practice["phone_prefix"])
        addr = f"{random.randint(100,9999)} {random.choice(['Main','Oak','Maple','Cedar','Pine','Elm','Washington','Park','Lake','Hill'])} St"
        zip_code = f"{random.randint(10000,99999)}"
        reg_date = _random_date(datetime(2015,1,1), datetime(2024,12,31)).strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO owners (first_name,last_name,email,phone,address,city,state,zip_code,registered_date) VALUES (?,?,?,?,?,?,?,?,?)",
                       (fn, ln, email, phone, addr, practice["city"], practice["state"], zip_code, reg_date))
        owner_ids.append(cursor.lastrowid)

    patient_ids = []
    for oid in owner_ids:
        num_pets = random.choices([1,2,3], weights=[60,30,10])[0]
        for _ in range(num_pets):
            pname = random.choice(PET_NAMES)
            species = random.choices(SPECIES, weights=[35,35,8,6,5,4,3,2,1,1])[0]
            breed = random.choice(BREEDS.get(species, ["Mixed"]))
            dob = _random_date(datetime(2010,1,1), datetime(2024,6,30)).strftime("%Y-%m-%d")
            gender = random.choice(["Male","Female"]) if species in ["Dog","Cat"] else random.choice(["Male","Female","Unknown"])
            weight = round(random.uniform(0.1, 45.0), 2)
            microchip = f"ISO-{random.randint(100000000000,999999999999)}" if random.random() > 0.3 else None
            status = random.choices(["Active","Inactive","Deceased"], weights=[85,10,5])[0]
            cursor.execute("INSERT INTO patients (owner_id,name,species,breed,birth_date,gender,weight_kg,microchip_id,status) VALUES (?,?,?,?,?,?,?,?,?)",
                           (oid, pname, species, breed, dob, gender, weight, microchip, status))
            patient_ids.append((cursor.lastrowid, oid))

    for pid, oid in patient_ids:
        num_appts = random.choices([1,2,3,4,5], weights=[25,25,20,15,15])[0]
        for _ in range(num_appts):
            appt_date = _random_date(datetime(2022,1,1), datetime(2025,9,18))
            appt_time = f"{random.randint(8,17):02d}:{random.choice(['00','15','30','45'])}"
            reason = random.choice(APPOINTMENT_REASONS)
            status = random.choice(APPOINTMENT_STATUSES)
            notes = f"Visit for: {reason}. Patient appeared {'normal' if random.random() > 0.3 else 'alert and responsive'}." if status == "Completed" else None
            vid = random.randint(1, num_vets)
            cursor.execute("INSERT INTO appointments (patient_id,vet_id,appointment_date,appointment_time,reason,status,notes) VALUES (?,?,?,?,?,?,?)",
                           (pid, vid, appt_date.strftime("%Y-%m-%d"), appt_time, reason, status, notes))
            appt_id = cursor.lastrowid
            if status == "Completed":
                num_treatments = random.randint(1, 3)
                total_cost = 0
                for _ in range(num_treatments):
                    ttype = random.choice(TREATMENT_TYPES)
                    cost = round(random.uniform(50, 500), 2)
                    total_cost += cost
                    desc = f"{ttype} performed during appointment for {reason}."
                    cursor.execute("INSERT INTO treatments (appointment_id,treatment_type,description,cost) VALUES (?,?,?,?)",
                                   (appt_id, ttype, desc, cost))
                num_rx = random.choices([0,1,2], weights=[40,40,20])[0]
                for _ in range(num_rx):
                    med = random.choice(MEDICATIONS)
                    dosage = f"{random.randint(1,2)} {'tablet' if random.random() > 0.5 else 'ml'} {'once' if random.random() > 0.5 else 'twice'} daily"
                    duration = f"{random.randint(7,30)} days"
                    cursor.execute("INSERT INTO prescriptions (appointment_id,medication_name,medication_type,dosage,duration,cost) VALUES (?,?,?,?,?,?)",
                                   (appt_id, med[0], med[1], dosage, duration, med[2]))
                    total_cost += med[2]
                pay_status = random.choices(["Paid","Pending","Overdue"], weights=[85,10,5])[0]
                pay_method = random.choice(["Credit Card","Cash","Debit Card","Check","Insurance"]) if pay_status == "Paid" else None
                cursor.execute("INSERT INTO invoices (owner_id,appointment_id,invoice_date,total_amount,payment_status,payment_method) VALUES (?,?,?,?,?,?)",
                               (oid, appt_id, appt_date.strftime("%Y-%m-%d"), round(total_cost, 2), pay_status, pay_method))

    conn.commit()
    conn.close()


def generate_all_databases(db_dir):
    """Generate all 10 vet practice databases in the given directory."""
    os.makedirs(db_dir, exist_ok=True)
    random.seed(42)
    for practice in PRACTICES:
        _create_practice_database(practice, db_dir)
    return len(PRACTICES)
