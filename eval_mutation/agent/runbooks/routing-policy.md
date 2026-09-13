# Routing policy

The following rules are authoritative. Cite their IDs in the filing rationale when a
boundary rule determines the decision.

## Default ownership

- **R-ID-1 — identity_access:** ordinary login, password reset, MFA recovery, account
  lockout, user permissions, role assignment, and SSO configuration.
- **R-BILL-1 — billing_payments:** charges, invoices, refunds, subscription state,
  payment processing, and money moved incorrectly.
- **R-TECH-1 — product_technical:** broken promised product behavior, API and
  integration failure, availability symptoms, processing failure, and product defects.
- **R-SEC-1 — security_privacy:** suspected or confirmed compromise, exposed
  credentials, vulnerability reports, unauthorized disclosure, and privacy rights.
- **R-FEED-1 — product_feedback:** new capability requests, non-defect UX feedback,
  and documentation suggestions.

## Precedence and boundaries

- **R-PRE-1:** compromise, credential exposure, or unauthorized access overrides an
  otherwise ordinary identity/access symptom and routes to security_privacy.
- **R-PRE-2:** a billing page or button that is visibly broken routes to
  product_technical unless the request says a charge, refund, invoice, subscription,
  or payment state itself is wrong. Incorrect movement or accounting of money routes
  to billing_payments.
- **R-PRE-3:** “I wish the product could” is product_feedback. “The documented or
  previously working product behavior is broken” is product_technical.
- **R-PRE-4:** privacy deletion/access requests and unintended data disclosure route
  to security_privacy even if the affected feature belongs to another team.
- **R-MAN-1:** use manual_triage only when missing or conflicting facts prevent these
  rules from selecting one owner. Difficulty alone is not a reason to abstain.

Choose exactly one team. Cross-team related tickets may still be linked.
