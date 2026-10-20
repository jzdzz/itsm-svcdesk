---
svcdesk_decisions:
  C1: business      # wallclock | business
  C2: immutable      # reopen | immutable
  C3: vip            # matrix | vip
---
<!-- ai-generated: 50% - pros and cons analysis drafted with AI assistance, final decision made by me based on the analysis -->

# Decisions


## C1 - SLA clock for P1

**Decision:** Use of the business-hours clock for all priorities, including P1 tickets.

**Rejected alternative:** I rejected the 24/7 continuous wall-clock for P1 tickets to avoid introducing complex, exceptional date-time logic into the service code.

**Reason:** Consistency in time-calculation algorithms across the entire service desk is crucial for maintainability, reducing code complexity and preventing edge-case bugs related to time zones.

**Service owner:** IT Operations Manager, because they are responsible for uniform staffing distribution and predictable technical support schedules.

**Customer outcome:** Customers receive a predictable and consistent handling process for critical issues, regardless of whether they are raised during weekends or off-hours.

## C2 - Closed tickets and reopening

**Decision:** Closed tickets are strictly immutable; reopening is not allowed.

**Rejected alternative:** I rejected the automatic reopening of closed tickets within 7 days via client comments.

**Reason:** A closed status signifies official finality and resolution agreement; reopening closed issues corrupts historical reporting, auditing, and lifecycle integrity.

**Service owner:** User Support Manager, because they ensure reporting accuracy and proper closure of the ticket lifecycle.

**Customer outcome:** The business benefits from a reliable and permanent record history and if an issue recurs, a fresh ticket is created and linked via the related_to reference.

## C3 - VIP reporters and the priority matrix

**Decision:** Elevate tickets from VIP reporters to a minimum priority of P2 if the matrix yields P3 or P4.

**Rejected alternative:** Reject strict adherence to the priority matrix for VIP users, which would ignore their business criticality.

**Reason:** Key stakeholders and executive users require enhanced visibility due to the immediate, high-level impact their issues have on business operations.

**Service owner:** Business Relationship Director, because they oversee executive satisfaction and support for key organizational stakeholders.

**Customer outcome:** The organization ensures prioritized attention for leadership-level issues, minimizing executive downtime and high-level operational friction.
