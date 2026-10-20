<!-- ai-generated: 100% - Specification for Core Service Desk API based on Lab 1 requirements and DECISIONS.md -->
# Feature Specification: Core Service Desk

**Feature Branch**: `001-core-service-desk`

**Created**: 2026-10-19

**Status**: Draft

**Input**: User description: "Lab 1 - Core Service Desk: Core ticketing API: ticket creation, status lifecycle, business-hours SLA clock, closed ticket immutability, and VIP priority elevation per DECISIONS.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Core Ticket Submission & Incident Logging (Priority: P1)

As an employee or customer experiencing an IT issue, I want to submit a support ticket specifying the issue summary, description, reporter identity, urgency, and impact, so that the service desk can formally record, prioritize, and manage the incident.

**Why this priority**: Ticket submission is the fundamental entry point of the entire service desk lifecycle; without it, no triage, SLA calculation, or resolution workflows can function.

**Independent Test**: Can be fully tested by submitting a new ticket with valid summary, description, and impact/urgency attributes, verifying that the system records the incident with a unique identifier and initial active status.

**Acceptance Scenarios**:

1. **Given** a customer provides valid ticket details (summary, description, reporter, urgency, impact), **When** they submit the ticket, **Then** the ticket is registered with a unique ID, status `new`, an assigned priority, and a calculated SLA resolution target.
2. **Given** a customer submits a ticket with missing mandatory fields (e.g., missing summary or reporter), **When** submission is processed, **Then** the system rejects the submission with a clear explanatory validation message.

---

### User Story 2 - Priority Calculation & VIP Elevation (Priority: P1)

As a service desk manager, I want the system to calculate ticket priority using an urgency-by-impact matrix, while automatically elevating tickets from verified VIP reporters to at least P2 when the matrix yields P3 or P4, so that leadership and business-critical stakeholders receive prompt operational focus.

**Why this priority**: Direct implementation of architectural policy Decision C3; ensures high-level organizational friction is minimized without requiring manual re-triage by human dispatchers.

**Independent Test**: Can be fully tested by submitting tickets with varying combinations of impact and urgency from standard reporters versus VIP reporters, verifying that VIP submissions never fall below priority P2.

**Acceptance Scenarios**:

1. **Given** a ticket submitted by a standard (non-VIP) reporter with Low urgency and Low impact, **When** priority is computed, **Then** the priority is assigned as P4.
2. **Given** a ticket submitted by a verified VIP reporter with Low urgency and Low impact (matrix calculation P4), **When** priority is computed, **Then** the assigned priority is elevated to P2.
3. **Given** a ticket submitted by a verified VIP reporter with Medium urgency and Low impact (matrix calculation P3), **When** priority is computed, **Then** the assigned priority is elevated to P2.
4. **Given** a ticket submitted by any reporter with High urgency and High impact (matrix calculation P1), **When** priority is computed, **Then** the assigned priority remains P1.

---

### User Story 3 - SLA Target & Business-Hours Clock Calculation (Priority: P2)

As a customer and service desk supervisor, I want resolution deadlines to be calculated strictly against standard business operational hours across all priorities, so that expectations are predictable, realistic, and aligned with support staffing coverage.

**Why this priority**: Direct implementation of architectural policy Decision C1; establishes consistent and maintainable time-accounting behavior across the platform without exceptional weekend clock variations.

**Independent Test**: Can be fully tested by submitting tickets during off-hours, weekends, or near the end of a business day, verifying that SLA elapsed time and target resolution deadlines advance only during configured business hours.

**Acceptance Scenarios**:

1. **Given** a ticket is created at 16:30 on a Friday with an 8 business-hour SLA target, **When** the resolution deadline is calculated, **Then** the remaining 7.5 hours are scheduled into the following Monday starting at the opening of business hours.
2. **Given** a P1 critical ticket is logged during a weekend or holiday, **When** SLA target calculation runs, **Then** the SLA clock starts at the beginning of the next available business-hours window per Decision C1.

---

### User Story 4 - Ticket Lifecycle & Closed Immutability (Priority: P2)

As an auditor and service manager, I need resolved tickets to be finalized into a closed state, and once closed, remain permanently immutable so that historical compliance records and SLA performance reports are tamper-proof.

**Why this priority**: Direct implementation of architectural policy Decision C2; protects audit integrity and prevents corruption of historical operational statistics.

**Independent Test**: Can be fully tested by advancing a ticket to `closed` status and attempting subsequent modifications, re-opening actions, or updates; all update requests must be rejected.

**Acceptance Scenarios**:

1. **Given** an active ticket in progress, **When** the assigned engineer completes resolution and submits resolution notes, **Then** the ticket transitions to `resolved`.
2. **Given** a resolved ticket whose resolution is verified, **When** the ticket is moved to `closed`, **Then** the ticket status becomes permanently closed and its closing timestamp is recorded.
3. **Given** a ticket in `closed` status, **When** any user attempts to edit fields, update status, or reopen the ticket, **Then** the system rejects the operation and preserves the original record unmodified.
4. **Given** an issue recurs after ticket closure, **When** a user reports the recurrence, **Then** a new ticket is generated referencing the closed ticket ID via `related_to`.

---

### User Story 5 - Ticket Inspection & Retrieval (Priority: P3)

As a support technician or customer, I want to retrieve tickets by unique identifier or filter tickets by status and reporter, so that I can monitor progress, inspect incident details, and coordinate resolution work.

**Why this priority**: Supports operational workflows and visibility after ticket submission.

**Independent Test**: Can be fully tested by querying the service for an existing ticket by ID or filtering tickets by specific status and verifying that all recorded ticket attributes match accurately.

**Acceptance Scenarios**:

1. **Given** an existing ticket ID, **When** a user requests the ticket record, **Then** the complete ticket details including current status, priority, reporter, SLA target, and history references are returned.
2. **Given** multiple tickets across various statuses, **When** a filter query by status (e.g., `status=new`) is executed, **Then** all matching tickets are returned in chronological order.

### Edge Cases

- **After-Hours Submission**: Tickets submitted outside business hours are recorded immediately with creation timestamps preserved; SLA target calculation begins from the start of the next business window.
- **Immediate Closure Attempt**: Direct transitions from `new` to `closed` bypassing intermediate resolution are rejected to ensure lifecycle discipline.
- **Invalid Referenced Ticket**: Submitting a `related_to` reference with a non-existent or malformed ticket identifier is rejected with an invalid-reference error.
- **Reporter Status Changes**: If a reporter's VIP designation changes after a ticket is created, existing ticket priorities remain intact to preserve deterministic historical records.
- **Concurrent Status Updates**: When multiple agents attempt simultaneous status transitions on the same ticket, state conflict protections ensure only valid sequence transitions succeed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to submit support tickets containing summary, description, reporter identifier, urgency, and impact.
- **FR-002**: System MUST generate and assign a unique identifier and creation timestamp to each ticket upon creation.
- **FR-003**: System MUST compute ticket priority (P1, P2, P3, P4) based on a defined urgency-and-impact matrix.
- **FR-004**: System MUST elevate tickets submitted by verified VIP reporters to a minimum priority of P2 whenever the standard priority matrix evaluates to P3 or P4 (Decision C3).
- **FR-005**: System MUST compute SLA resolution deadlines using uniform business operational hours for all priority levels, including P1 incidents (Decision C1).
- **FR-006**: System MUST enforce valid lifecycle transitions (`new` -> `in_progress` -> `resolved` -> `closed`).
- **FR-007**: System MUST enforce strict immutability on all tickets in `closed` status, forbidding any modifications, comments, status changes, or reopening (Decision C2).
- **FR-008**: System MUST allow tickets to optionally link to a previously closed or related ticket via a `related_to` identifier attribute.
- **FR-009**: System MUST provide retrieval of individual tickets by unique identifier and querying of tickets by status or reporter.
- **FR-010**: System MUST validate all mandatory fields upon submission and return clear descriptive validation errors for invalid or missing inputs.

### Key Entities *(include if feature involves data)*

- **Ticket**: Represents an incident or service request.
  - *Attributes*: `id` (unique identifier), `summary` (string), `description` (string), `reporter` (identifier), `is_vip` (boolean flag), `urgency` (low, medium, high), `impact` (low, medium, high), `priority` (P1, P2, P3, P4), `status` (new, in_progress, resolved, closed), `created_at` (timestamp), `resolved_at` (timestamp, optional), `closed_at` (timestamp, optional), `sla_target` (timestamp), `related_to` (optional ticket identifier).
- **Reporter**: Represents the individual reporting the incident.
  - *Attributes*: `id` (user identifier), `name` (string), `is_vip` (boolean flag).
- **SLA Calendar**: Represents operational business hours definition (standard working days and hours) used for deadline calculations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of tickets submitted by VIP reporters receive an assigned priority of P1 or P2, verified across all possible impact and urgency combinations.
- **SC-002**: 100% of modification or reopen attempts on closed tickets are rejected, maintaining zero data mutation on closed records.
- **SC-003**: 100% of SLA deadline calculations across all priorities strictly count business operational hours and exclude non-business hours/weekends.
- **SC-004**: Users receive ticket registration confirmation with assigned priority and SLA target in under 2 seconds.
- **SC-005**: Authorized users can retrieve ticket details or filtered ticket lists in under 1 second.
- **SC-006**: 100% of ticket lifecycle transitions follow the defined state machine, with zero invalid status jumps permitted.

## Assumptions

- Standard business operational hours are defined as Monday through Friday, 08:00 to 17:00 (or equivalent configured business window) excluding weekends.
- The VIP status of a reporter is either provided during ticket submission or determinable from reporter identity.
- File attachments, email dispatch, and push notifications are outside the scope of Core Service Desk v1.
- All timestamps are represented in ISO 8601 standard format.
- Reopening closed tickets is intentionally excluded in favor of creating new tickets linked via `related_to`, as established by Decision C2.
