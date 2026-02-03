# Pharmacy Care Plan Auto-Generator – Design Document

## 1. Background

**Customer**  
A specialty pharmacy.

**Primary users**  
Internal medical staff (pharmacists / medical assistants).  
Patients do not access this system.

**Business goal**  
Automatically generate pharmacist care plans based on patient clinical records, in order to:

- reduce manual preparation time (currently 20–40 minutes per patient),
- meet compliance requirements,
- support reimbursement workflows (Medicare and pharma),
- reduce backlog caused by staff shortage.

A generated care plan is printed and handed to the patient.

---

## 2. Scope

### In scope (P0 + P1, confirmed)

1. Patient / order duplication detection
2. Care Plan generation using LLM
3. Provider duplication detection
4. Reporting export for pharma / compliance
5. Care Plan file download

All above items are mandatory for the initial delivery.

### Out of scope (current phase)

- Patient-facing features
- Physician use cases
- Editing care plans inside the system
- Advanced analytics and dashboards

---

## 3. Core Business Rules

### 3.1 Care Plan definition

- One care plan corresponds to **one order**, i.e. **one medication**.
- A care plan must include the following sections:

- Problem list / Drug therapy problems
- Goals
- Pharmacist interventions
- Monitoring plan

---

## 4. User Workflow (High Level)

1. Medical assistant opens the web form.
2. User enters patient, provider, diagnosis and medication information.
3. System validates all inputs.
4. System performs duplication checks (patient, order, provider).
5. If blocking errors exist, submission is stopped.
6. If warnings exist, the user may explicitly confirm and continue.
7. System calls an LLM to generate a care plan.
8. User downloads the generated care plan file.
9. User exports reporting data for pharma/compliance.

---

## 5. Inputs

The system must support the following input fields.

| Field                     | Type                 | Notes                                     |
| ------------------------- | -------------------- | ----------------------------------------- |
| Patient First Name        | string               | required                                  |
| Patient Last Name         | string               | required                                  |
| Patient MRN               | 6-digit string       | unique patient identifier                 |
| Patient DOB               | date                 | required (used for duplication detection) |
| Referring Provider Name   | string               | required                                  |
| Referring Provider NPI    | 10-digit string      | unique provider identifier                |
| Patient Primary Diagnosis | ICD-10 code          | required                                  |
| Additional Diagnosis      | list of ICD-10 codes | optional                                  |
| Medication Name           | string               | required                                  |
| Medication History        | list of strings      | optional                                  |
| Patient Records           | free text or PDF     | required                                  |

---

## 6. Validation Rules

### 6.1 Field validation

- All required fields must be present.
- MRN must be exactly 6 digits.
- NPI must be exactly 10 digits.
- ICD-10 fields must follow ICD-10 format.
- Patient Records must be either:
  - plain text, or
  - a PDF file.

### 6.2 Production validation requirements

- Every input must be validated before submission.
- Validation errors must be clearly presented to the user.
- No partial or inconsistent data may be persisted.

---

## 7. Duplication Detection Rules

### 7.1 Order / medication duplication

| Scenario                                           | Result  | Action                        |
| -------------------------------------------------- | ------- | ----------------------------- |
| Same patient + same medication + same calendar day | ERROR   | Must block submission         |
| Same patient + same medication + different day     | WARNING | User may confirm and continue |

---

### 7.2 Patient duplication

| Scenario                             | Result  | Action                        |
| ------------------------------------ | ------- | ----------------------------- |
| Same MRN, but name or DOB different  | WARNING | User may confirm and continue |
| Same name and DOB, but MRN different | WARNING | User may confirm and continue |

---

### 7.3 Provider duplication

| Scenario                              | Result | Action            |
| ------------------------------------- | ------ | ----------------- |
| Same NPI, but provider name different | ERROR  | Must be corrected |

NPI is treated as the unique provider identifier.

---

## 8. Error vs Warning Behavior

### Error

- Submission is blocked.
- User must fix the data before continuing.
- No care plan generation is triggered.

Typical error scenarios:

- Invalid required fields
- Same patient + same medication + same day
- Same NPI with conflicting provider names
- LLM generation failure

### Warning

- Submission is allowed only after explicit user confirmation.
- A warning does not prevent care plan generation.

Typical warning scenarios:

- Possible duplicate patient records
- Same patient and same medication on different days

---

## 9. Care Plan Generation

- The system must call an LLM to generate the care plan.
- The LLM input consists of:
  - structured form data,
  - extracted or raw patient record text.
- The LLM output must strictly follow the required care plan structure:

- Problem list
- Goals
- Pharmacist interventions
- Monitoring plan

- The generated result is provided as a downloadable text-based file.

---

## 10. Reporting Export

- The system must provide a quick export function for internal and pharma reporting.
- The export must support structured data (e.g. CSV or Excel).
- At minimum, the export must include:
  - patient identifiers,
  - provider identifiers,
  - medication,
  - diagnosis,
  - care plan generation timestamp,
  - duplication warning indicators.

---

## 11. File Download

- Each generated care plan must be downloadable by the user.
- The file is intended to be printed and uploaded into external internal systems.

---

## 12. Non-Functional Requirements

### 12.1 Production readiness

- All inputs are validated.
- Integrity rules always enforce consistency.
- Errors must be:
  - safe (no sensitive data leakage),
  - clear to the user,
  - contained (no system-wide failures).
- Code must be modular and navigable.
- Critical logic (especially duplication detection and validation) must be covered by automated tests.
- The project must run end-to-end out of the box.

---

## 13. Data Integrity and Consistency

- Provider records must be unique by NPI.
- Patients must be uniquely identified by MRN.
- One care plan corresponds to exactly one medication order.
- All duplication decisions must be deterministic and auditable.

---

## 14. Example Input and Output

### Example patient record input (simplified)

- Female, DOB 1979-06-08
- MRN 00012345
- Primary diagnosis: generalized myasthenia gravis
- Medication: IVIG
- Patient records include clinical history and treatment recommendations

### Example care plan output sections

- Problem list / drug therapy problems
- Goals (SMART goals)
- Pharmacist interventions
- Monitoring plan and lab schedule

These sections must always be present in the generated output.

---

## 15. Assumptions and Open Points

- The system is used only by internal medical staff.
- Patients do not directly access the system.
- Generated care plans are not edited in the system.
- PDF parsing and text extraction quality requirements will be defined during implementation.
- Data privacy and LLM deployment/compliance constraints will be confirmed separately.
