# Disaster Recovery Restore Procedure
## SVPMS - Database and Application Restoration

**Version:** 1.0  
**Owner:** Platform Team  
**RPO:** 5 minutes | **RTO:** 1 hour

---

## 1. TRIGGER CONDITIONS

Execute this runbook when:
- Complete database loss or corruption
- GCP region failure
- Critical data integrity issue
- Ransomware attack

---

## 2. PRE-REQUISITES

**Access Required:**
- GCP Console (Admin role)
- Database credentials from Secrets Manager
- PagerDuty incident commander role

**Confirm:**
- [ ] Latest backup exists (< 24 hours old)
- [ ] DR team notified
- [ ] Incident ticket created

---

## 3. RESTORATION STEPS

### Step 1: Assess Damage (5 min)

```bash
# Check database status
aws rds describe-db-instances \
  --db-instance-identifier svpms-prod

# Check latest backup
aws rds describe-db-snapshots \
  --db-instance-identifier svpms-prod \
  --query 'DBSnapshots|sort_by(@, &SnapshotCreateTime)|[-1]'
```

### Step 2: Point-in-Time Recovery (15 min)

```bash
RECOVERY_TIME=$(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ)

aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier svpms-prod \
  --target-db-instance-identifier svpms-prod-restored \
  --restore-time $RECOVERY_TIME

# Wait for completion
aws rds wait db-instance-available \
  --db-instance-identifier svpms-prod-restored
```

### Step 3: Validate Database (10 min)

```bash
# Get endpoint
NEW_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier svpms-prod-restored \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

# Connect and validate
psql -h $NEW_ENDPOINT -U svpms_admin -d svpms

# Run validation queries
SELECT COUNT(*) FROM tenants;
SELECT MAX(created_at) FROM purchase_requests;
```

**Validation Checklist:**
- [ ] All tables present
- [ ] Row counts match
- [ ] Latest transactions present
- [ ] No orphaned records

### Step 4: Update Application (10 min)

```bash
# Update Secrets Manager
aws secretsmanager update-secret \
  --secret-id svpms/database-url \
  --secret-string "postgresql://svpms_admin:PASSWORD@$NEW_ENDPOINT:5432/svpms"

# Force Cloud Run deployment
aws ecs update-service \
  --cluster svpms-prod-cluster \
  --service svpms-api \
  --force-new-deployment
```

### Step 5: Smoke Tests (5 min)

```bash
# Health check
curl https://api.svpms.example.com/health

# Authentication test
curl -X POST https://api.svpms.example.com/auth/login \
  -d '{"email":"test@example.com","password":"test123"}'
```

---

## 4. POST-RECOVERY

- [ ] Update incident timeline
- [ ] Notify stakeholders
- [ ] Schedule post-mortem
- [ ] Test restored backups

---

## 5. CONTACTS

**Incident Commander:** +1-XXX-XXX-XXXX  
**GCP Support:** 1-800-XXX-XXXX
