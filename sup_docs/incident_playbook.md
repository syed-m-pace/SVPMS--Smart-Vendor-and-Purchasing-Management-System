# Incident Response Playbook
## SVPMS Production Incidents

**Version:** 1.0  
**Owner:** Platform Team  
**Last Updated:** 2026-02-13

---

## INCIDENT CLASSIFICATION

### Severity Levels

**P0 - Critical (Response: Immediate)**
- Complete service outage
- Data breach or security compromise
- Payment processing failure

**P1 - High (Response: 30 min)**
- Partial service degradation (>5% error rate)
- Database connection failures
- Authentication system down

**P2 - Medium (Response: 2 hours)**
- Background job failures
- Integration errors (ERP, email)
- Performance degradation (<SLO)

**P3 - Low (Response: Next business day)**
- Minor bugs
- Feature requests
- Documentation issues

---

## INCIDENT RESPONSE WORKFLOW

### Phase 1: Detection & Triage (5 min)

1. **Alert Received**
   - PagerDuty notification
   - Monitoring alert (Grafana/CloudWatch)
   - User report

2. **Acknowledge Incident**
   ```bash
   # Acknowledge in PagerDuty
   # Check monitoring dashboards
   https://grafana.svpms.example.com/d/production
   ```

3. **Assess Severity**
   - Check error rate, latency, availability
   - Determine affected users/features
   - Classify as P0/P1/P2/P3

4. **Page On-Call**
   - P0/P1: Page immediately
   - P2: Slack notification
   - P3: Create ticket

### Phase 2: Investigation (15-30 min)

1. **Gather Information**
   ```bash
   # Check logs
   aws logs tail /ecs/svpms-api --follow
   
   # Check metrics
   # - Error rate
   # - Latency (p95, p99)
   # - Database connections
   # - CPU/Memory usage
   ```

2. **Identify Root Cause**
   - Recent deployments?
   - Database issues?
   - External service failures?
   - Traffic spike?

3. **Document Findings**
   - Update incident ticket
   - Share in #incidents Slack channel

### Phase 3: Mitigation (Immediate)

**Quick Mitigations:**

1. **Rollback Deployment**
   ```bash
   # Rollback to previous task definition
   aws ecs update-service \
     --cluster svpms-prod-cluster \
     --service svpms-api \
     --task-definition svpms-api:PREVIOUS_VERSION
   ```

2. **Scale Resources**
   ```bash
   # Increase ECS tasks
   aws ecs update-service \
     --cluster svpms-prod-cluster \
     --service svpms-api \
     --desired-count 10
   ```

3. **Restart Services**
   ```bash
   # Force new deployment
   aws ecs update-service \
     --cluster svpms-prod-cluster \
     --service svpms-api \
     --force-new-deployment
   ```

4. **Database Issues**
   - Check connection pool utilization
   - Kill long-running queries if needed
   - Consider read replica promotion

### Phase 4: Resolution (Variable)

1. **Implement Fix**
   - Deploy hotfix if needed
   - Apply configuration changes
   - Restore from backup if necessary

2. **Verify Resolution**
   ```bash
   # Check metrics returned to normal
   # Run smoke tests
   curl https://api.svpms.example.com/health
   
   # Verify error rate < 1%
   # Verify p95 latency < 500ms
   ```

3. **Monitor for Recurrence**
   - Watch for 30 minutes
   - Check error logs
   - Verify SLOs met

### Phase 5: Communication

**During Incident:**
- Update status page every 30 min
- Slack updates in #incidents
- Notify affected customers (P0/P1)

**After Resolution:**
- Send resolution notification
- Update incident ticket
- Schedule post-mortem (P0/P1)

---

## COMMON SCENARIOS

### Scenario 1: High Error Rate (5xx)

**Symptoms:** Error rate > 2%

**Actions:**
1. Check recent deployments → Rollback if recent
2. Check database connections → Scale if needed
3. Check external services → Enable circuit breaker
4. Check logs for stack traces

**Resolution:**
- Rollback deployment OR
- Scale database connections OR
- Disable failing integration

---

### Scenario 2: High Latency

**Symptoms:** p95 latency > 1000ms

**Actions:**
1. Check database query performance
2. Check Redis cache hit rate
3. Check external API latency
4. Check CPU/memory usage

**Resolution:**
- Add database indexes OR
- Increase cache TTL OR
- Scale ECS tasks

---

### Scenario 3: Authentication Failures

**Symptoms:** Cannot log in

**Actions:**
1. Check Redis (session store)
2. Check JWT key in Secrets Manager
3. Check SAML IdP status (if SSO)
4. Check database user table

**Resolution:**
- Restart Redis OR
- Rotate JWT keys OR
- Contact IdP support

---

### Scenario 4: Payment Processing Failure

**Symptoms:** Stripe webhooks failing

**Actions:**
1. Check Stripe dashboard
2. Check webhook endpoint health
3. Check webhook signature validation
4. Check Stripe API keys

**Resolution:**
- Retry failed webhooks OR
- Update Stripe API keys OR
- Fix webhook endpoint

---

## POST-INCIDENT

### Immediate (Within 24 hours)

- [ ] Update incident ticket with full timeline
- [ ] Share incident summary in #incidents
- [ ] Identify action items

### Short-term (Within 1 week)

- [ ] Conduct post-mortem (P0/P1 only)
- [ ] Document lessons learned
- [ ] Create preventive tasks
- [ ] Update runbooks

### Long-term (Within 1 month)

- [ ] Implement preventive measures
- [ ] Update monitoring/alerts
- [ ] Update documentation
- [ ] Train team on findings

---

## ESCALATION PATHS

**Level 1:** On-call engineer  
**Level 2:** Platform lead  
**Level 3:** Engineering manager  
**Level 4:** CTO

**External Escalations:**
- GCP Support: 1-800-XXX-XXXX (Premium)
- Stripe Support: support@stripe.com
- Brevo Support: contact@brevo.com

---

## CONTACTS

**On-Call:** PagerDuty rotation  
**Platform Lead:** platform-lead@company.com  
**Incident Channel:** #incidents (Slack)  
**Status Page:** https://status.svpms.example.com

---

## USEFUL COMMANDS

```bash
# Check service health
curl https://api.svpms.example.com/health

# Check logs
aws logs tail /ecs/svpms-api --since 1h --follow

# Check ECS tasks
aws ecs list-tasks --cluster svpms-prod-cluster

# Check database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM pg_stat_activity"

# Check Redis
redis-cli -h $REDIS_HOST ping

# Force deployment
aws ecs update-service --cluster svpms-prod --service svpms-api --force-new-deployment
```
