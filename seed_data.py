import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiep_backend.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import CustomerProfile, SellerProfile, ProviderProfile
from catalog.models import Category, Product

# 1. Create Sample Seller
seller_user, _ = User.objects.get_or_create(username="med_supplier", email="supplier@healthflow.com")
seller_profile, _ = SellerProfile.objects.get_or_create(user=seller_user, store_name="Apex Pharma & Supply Co.", verification_status=True)

# 2. Populate 8 Doctor Profiles (Fixes missing names & adds extra doctors)
doctors_data = [
    {"username": "dr_smith", "first_name": "Sarah", "last_name": "Smith", "specialty": "General Practice", "degrees": "MBBS, MD", "exp": 5, "fee": 50.00, "bio": "Primary healthcare provider focusing on routine checkups and preventive medicine."},
    {"username": "dr_jenkins", "first_name": "Marcus", "last_name": "Jenkins", "specialty": "Cardiology", "degrees": "MBBS, MD", "exp": 8, "fee": 65.00, "bio": "Specialist in cardiovascular health, hypertension management, and ECG diagnostics."},
    {"username": "dr_vance", "first_name": "Elena", "last_name": "Vance", "specialty": "Dermatology", "degrees": "MBBS, MD", "exp": 7, "fee": 55.00, "bio": "Expert in skin health, allergy treatment, and non-invasive dermatological procedures."},
    {"username": "dr_sarah", "first_name": "Sarah", "last_name": "Jenkins", "specialty": "Cardiology & Telemedicine", "degrees": "MBBS, FCPS (Cardiology)", "exp": 12, "fee": 75.00, "bio": "Specialist in preventive cardiology and digital health monitoring."},
    {"username": "dr_okari", "first_name": "Amara", "last_name": "Okari", "specialty": "Pediatrics", "degrees": "MD, FAAP", "exp": 10, "fee": 60.00, "bio": "Child healthcare specialist focused on developmental milestones and routine immunizations."},
    {"username": "dr_chen", "first_name": "David", "last_name": "Chen", "specialty": "Orthopedics", "degrees": "MD, FAAOS", "exp": 14, "fee": 90.00, "bio": "Specializing in joint pain, sports injuries, and musculoskeletal rehab protocols."},
    {"username": "dr_taylor", "first_name": "Robert", "last_name": "Taylor", "specialty": "Emergency Medicine", "degrees": "MD, FACEP", "exp": 11, "fee": 80.00, "bio": "Critical care consultant specializing in urgent triage and acute care response."},
    {"username": "dr_patel", "first_name": "Priya", "last_name": "Patel", "specialty": "Internal Medicine", "degrees": "MD, FACP", "exp": 9, "fee": 70.00, "bio": "Comprehensive care for adult complex medical conditions and chronic disease management."}
]

for doc in doctors_data:
    user, _ = User.objects.get_or_create(username=doc["username"])
    user.first_name = doc["first_name"]
    user.last_name = doc["last_name"]
    user.save()

    profile, _ = ProviderProfile.objects.get_or_create(user=user)
    profile.specialty = doc["specialty"]
    profile.degrees = doc["degrees"]
    profile.experience_years = doc["exp"]
    profile.consultation_fee = doc["fee"]
    profile.bio = doc["bio"]
    profile.credential_status = "Verified"
    profile.save()

# 3. Populate Categories
categories_data = [
    ("Cold-Chain Vaccines", "Vaccine vials, insulin, and temperature-controlled biologics."),
    ("Diagnostics & Testing", "Rapid test cassettes, PCR reagents, and diagnostic kits."),
    ("Surgical Gear", "Sterile disposable scalpel kits, drapes, and PPE gowns."),
    ("Telemetry & Devices", "IoT medical sensor units, blood pressure nodes, and pulse oximeters."),
    ("Emergency Care", "First responder trauma kits, oxygen regulators, and IV setups."),
    ("Medicines", "General prescription and over-the-counter pharmaceuticals."),
]

category_objects = {}
for name, desc in categories_data:
    cat, _ = Category.objects.get_or_create(name=name, defaults={'description': desc})
    category_objects[name] = cat

# 4. Populate Realistic Products
products_data = [
    {
        "name": "Smart Telemetry Vaccine Cooler Box",
        "category": category_objects["Cold-Chain Vaccines"],
        "price": 349.99,
        "stock": 25,
        "dosage": "N/A",
        "certifications": "ISO-13485, FDA Approved",
        "description": "Real-time GPS and temperature monitoring storage container for temperature-sensitive medical transport.",
        "image_url": "https://images.unsplash.com/photo-1584036561566-baf8f5f1b144?w=500"
    },
    {
        "name": "Rapid Antigen Test Cassettes (Pack of 50)",
        "category": category_objects["Diagnostics & Testing"],
        "price": 89.50,
        "stock": 140,
        "dosage": "Single-use diagnostic",
        "certifications": "CE Certified, WHO Listed",
        "description": "High-accuracy lateral flow rapid diagnostic tests for clinical point-of-care testing.",
        "image_url": "https://images.unsplash.com/photo-1615461066841-6116e61058f4?w=500"
    },
    {
        "name": "Sterile Surgical Procedure Kit",
        "category": category_objects["Surgical Gear"],
        "price": 45.00,
        "stock": 80,
        "dosage": "N/A",
        "certifications": "ISO-9001",
        "description": "Fully sterile single-use surgical instrument tray including forceps, scalpel, and drapes.",
        "image_url": "https://images.unsplash.com/photo-1583947215259-38e31be8751f?w=500"
    },
    {
        "name": "IoT Wireless Blood Oxygen Monitor",
        "category": category_objects["Telemetry & Devices"],
        "price": 120.00,
        "stock": 45,
        "dosage": "N/A",
        "certifications": "FDA Cleared, CE",
        "description": "Bluetooth and cellular connected continuous telemetry pulse oximeter for remote patient monitoring.",
        "image_url": "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=500"
    }
]

for prod in products_data:
    Product.objects.get_or_create(
        name=prod["name"],
        seller=seller_profile,
        defaults=prod
    )

print("Database updated with 8 detailed doctors, correct names, categories, and products!")