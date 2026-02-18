# DATA PROCESSING ADDENDUM (DPA)
## SVPMS - Smart Vendor & Purchasing Management System

**Effective Date:** [Date]

---

## 1. DEFINITIONS

**"Personal Data"** means any information relating to an identified or identifiable natural person.

**"Controller"** means the Customer who determines purposes and means of processing.

**"Processor"** means SVPMS, which processes Personal Data on behalf of Controller.

---

## 2. SCOPE OF PROCESSING

### 2.1 Categories of Personal Data
- User identity data (name, email, employee ID)
- Contact information (phone, address)
- Financial data (bank accounts - encrypted with AES-256)
- Authentication data (password hashes, MFA tokens)
- Usage data (IP addresses, login timestamps)

### 2.2 Purpose of Processing
- User authentication and authorization
- Purchase request workflows
- Vendor management
- Invoice processing and payment
- Audit logging and compliance

---

## 3. DATA SUBJECT RIGHTS

### 3.1 Right of Access (GDPR Article 15)
- API endpoint: `GET /api/v1/data-subject-access/{user_id}`
- Response time: 5 business days
- Format: JSON export of all user data

### 3.2 Right to Erasure (GDPR Article 17)
- Process: Pseudonymization of personal data
- Implementation: User email becomes `deleted_{uuid}@example.com`
- Retention: Financial records retained 7 years per compliance requirements

### 3.3 Right to Data Portability (GDPR Article 20)
- Format: JSON export via API
- Includes: All user-generated content and profile data

---

## 4. SECURITY MEASURES

### 4.1 Technical Measures
- **Encryption in transit:** TLS 1.3
- **Encryption at rest:** AES-256-GCM for sensitive fields
- **Database encryption:** AWS RDS encryption enabled
- **Access control:** MFA required for Finance and Admin roles
- **Network security:** VPC isolation, private subnets

### 4.2 Organizational Measures
- Background checks for employees with data access
- Confidentiality agreements
- Annual security awareness training
- Incident response plan
- Regular security audits

---

## 5. DATA BREACH NOTIFICATION

- **Internal Detection:** Continuous monitoring via CloudWatch, Prometheus
- **Notification to Customer:** Within 72 hours of becoming aware
- **Notification Content:**
  - Nature of the breach
  - Categories of data subjects affected
  - Likely consequences
  - Measures taken or proposed

---

## 6. DATA RETENTION

See `compliance/retention_matrix.csv` for complete retention schedule.

**Summary:**
- Financial records (PR, PO, invoices): 7 years
- User data: Duration of account + right to erasure
- Audit logs: 7 years
- Session data: TTL-based (15 min - 7 days)

### 6.1 Return or Deletion on Termination
Within 30 days of contract termination:
- Option 1: Return all Personal Data in portable format (JSON)
- Option 2: Delete all Personal Data except legally required records
- Certification of deletion provided

---

## 7. SUB-PROCESSORS

| Sub-processor | Service | Location | Data Processed |
|---------------|---------|----------|----------------|
| AWS | Infrastructure | US (us-east-1) | All data |
| Brevo | Email delivery | France/EU | Email addresses, names |
| Stripe | Payment processing | US | Bank account numbers, payment info |
| AWS Textract | OCR | US | Invoice documents |

### 7.1 Sub-processor Changes
- 30 days notice before adding new sub-processors
- Customer may object within 15 days

---

## 8. CONTACT INFORMATION

**Data Protection Officer:**  
Email: dpo@svpms.example.com

**Security Contact:**  
Email: security@svpms.example.com  
Phone: [24/7 Hotline]

---

**SIGNATURES**

**SVPMS (Processor)**

Signature: _____________________  
Name: [Name]  
Title: [Title]  
Date: _____________________

**CUSTOMER (Controller)**

Signature: _____________________  
Name: [Name]  
Title: [Title]  
Date: _____________________
