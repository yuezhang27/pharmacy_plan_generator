-- Mock data for pharmacy_plan_generator
-- Run this in TablePlus: connect to pharmacy_db, then execute this SQL
-- PostgreSQL
--
-- If you get "duplicate key" errors: your DB may already have data.
-- Option 1: Run the DELETE block below first (removes ALL data)
-- Option 2: Change MRN/NPI values in this script to avoid conflicts

-- Optional: clear existing data before insert (uncomment if needed)
/*
DELETE FROM careplan_careplan;
DELETE FROM careplan_patient;
DELETE FROM careplan_provider;
*/

-- Insert Patients (MRN 6 digits, unique)
INSERT INTO careplan_patient (id, first_name, last_name, mrn, dob, created_at) VALUES
(101, 'Jane', 'Smith', '100001', '1979-06-08', NOW()),
(102, 'John', 'Doe', '100002', '1985-03-15', NOW()),
(103, 'Maria', 'Garcia', '100003', '1992-11-22', NOW()),
(104, 'Robert', 'Johnson', '100004', '1968-07-30', NOW()),
(105, 'Emily', 'Chen', '100005', '1990-01-12', NOW());

-- Insert Providers (NPI 10 digits, unique)
INSERT INTO careplan_provider (id, name, npi, created_at) VALUES
(101, 'Dr. Sarah Williams', '1001234567', NOW()),
(102, 'Dr. Michael Brown', '1009876543', NOW()),
(103, 'Dr. Lisa Anderson', '1001122334', NOW());

-- Insert Care Plans (status=completed, with generated_content)
INSERT INTO careplan_careplan (
    id, patient_id, provider_id, primary_diagnosis, additional_diagnosis,
    medication_name, medication_history, patient_records, status,
    generated_content, error_message, created_at, updated_at
) VALUES
(201, 101, 101, 'G70.00', 'Z79.4', 'IVIG', 'Prior prednisone', 'Female, DOB 1979-06-08. MRN 100001. Generalized myasthenia gravis. Patient records include clinical history.', 'completed',
'=== Care Plan ===

1. Problem List / Drug Therapy Problems
- Medication adherence concern with chronic condition
- Need for monitoring of IVIG response

2. Goals (SMART Goals)
- Patient will receive IVIG per prescribed schedule
- Monitor symptom improvement within 4 weeks

3. Pharmacist Interventions
- Patient education on IVIG administration
- Coordinate with infusion center

4. Monitoring Plan
- Lab schedule: CBC, metabolic panel monthly
- Clinical follow-up in 4 weeks', '', NOW(), NOW()),

(202, 102, 101, 'E11.9', '', 'Metformin', 'None', 'Male, DOB 1985-03-15. Type 2 diabetes. New diagnosis.', 'completed',
'=== Care Plan ===

1. Problem List / Drug Therapy Problems
- Newly diagnosed Type 2 diabetes
- Need for medication initiation

2. Goals (SMART Goals)
- A1C target <7% within 6 months
- Patient will understand medication timing

3. Pharmacist Interventions
- Initiate Metformin therapy
- Diabetes education referral

4. Monitoring Plan
- A1C every 3 months
- Renal function annually', '', NOW(), NOW()),

(203, 103, 102, 'M79.3', 'G89.29', 'Gabapentin', 'Ibuprofen PRN', 'Female, chronic pain. Panniculitis and neuropathic pain.', 'completed',
'=== Care Plan ===

1. Problem List / Drug Therapy Problems
- Panniculitis and neuropathic pain
- Multiple pain medications

2. Goals (SMART Goals)
- Reduce pain score by 2 points in 8 weeks
- Titrate gabapentin to effective dose

3. Pharmacist Interventions
- Gabapentin titration schedule
- Review NSAID use with PPI

4. Monitoring Plan
- Pain assessment at each visit
- Renal function every 6 months', '', NOW(), NOW()),

(204, 101, 103, 'G70.00', '', 'Prednisone', 'IVIG', 'Same patient Jane Smith. Adjunct therapy for myasthenia gravis.', 'completed',
'=== Care Plan ===

1. Problem List / Drug Therapy Problems
- Adjunct immunosuppression needed
- Monitor steroid side effects

2. Goals (SMART Goals)
- Reduce IVIG frequency with steroid taper
- Minimize steroid-related adverse effects

3. Pharmacist Interventions
- Prednisone taper protocol
- Calcium/vitamin D supplementation

4. Monitoring Plan
- Blood glucose, bone density
- Ophthalmology referral for long-term use', '', NOW(), NOW()),

(205, 104, 102, 'I10', '', 'Lisinopril', 'None', 'Male, newly diagnosed hypertension.', 'completed',
'=== Care Plan ===

1. Problem List / Drug Therapy Problems
- Newly diagnosed hypertension
- No prior medications

2. Goals (SMART Goals)
- BP <130/80 within 3 months
- Medication adherence >80%

3. Pharmacist Interventions
- Initiate lisinopril
- Home BP monitoring education

4. Monitoring Plan
- BP check in 2 weeks
- Potassium and creatinine at 4 weeks', '', NOW(), NOW());

-- Reset sequences so Django auto-increment works correctly after manual inserts
SELECT setval(pg_get_serial_sequence('careplan_patient', 'id'), (SELECT MAX(id) FROM careplan_patient));
SELECT setval(pg_get_serial_sequence('careplan_provider', 'id'), (SELECT MAX(id) FROM careplan_provider));
SELECT setval(pg_get_serial_sequence('careplan_careplan', 'id'), (SELECT MAX(id) FROM careplan_careplan));
