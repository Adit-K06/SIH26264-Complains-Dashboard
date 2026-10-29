# AICTE Complaint Coordination Dashboard — Official User Guide
**Problem Statement:** SIH26264  
**Audience:** AICTE Bureau Officers, Regional Officers, Senior Management, and Administrators  
**Notice:** *Demo uses synthetic data. SLA values are placeholders, not official AICTE norms.*

---

## 1. System Overview & Login

The AICTE Complaint Coordination Dashboard provides unified visibility across existing AICTE Bureaus and Cells (Regulation Bureau, Public Grievance Redressal Cell, Approval Bureau, Academic Bureau, and Finance Bureau). It does not replace bureau systems; it acts as an intelligent coordination and cross-bureau overlap detection layer.

### Demo Credentials
| User Name | Role | Bureau / Region | Password |
| :--- | :--- | :--- | :--- |
| **Demo Administrator** (`admin`) | `ADMIN` | All Bureaus / All Regions | `Demo@12345` |
| **Demo Senior Manager** (`senior`) | `SENIOR_MGMT` | All Bureaus (Read & Escalate) | `Demo@12345` |
| **Demo RB Officer** (`rb_officer`) | `BUREAU_OFFICER` | Regulation Bureau (RB) | `Demo@12345` |
| **Demo PGRC Officer** (`pgrc_officer`) | `BUREAU_OFFICER` | Public Grievance Redressal Cell (PGRC) | `Demo@12345` |
| **Demo North Regional Officer** (`regional_north`) | `REGIONAL_OFFICER` | North Region | `Demo@12345` |

---

## 2. "First 10 Minutes" Role-Based Walkthroughs

### A. Bureau Officer (RB / PGRC)
1. **Sign in:** Enter your username (`rb_officer` or `pgrc_officer`) and password `Demo@12345`.
2. **Review Dashboard:** See active workload bars in **"Cases by bureau and status"** and urgent items under **"Beyond SLA"**.
3. **Open Cases:** Click **"Cases"** in the left sidebar navigation.
4. **Filter Your Bureau:** Select your bureau in the filter dropdown or type an institution name in the search bar.
5. **Inspect Case Detail:** Click on any case link (e.g., `RB-2026-00001`). View the 10 core fields: Case ID, Receipt Date, Category, Current Status, Bureau, Assigned Officer, Last Action, Next Action, Date of Last Action, and Expected Disposal Date. Note that complainant references outside your bureau appear masked to protect whistleblower privacy.
6. **Execute Case Transition:**
   - To begin processing, click **"Add action"** -> Select **"Under process"** and enter remarks -> Click **"Submit"**.
   - If an issue is resolved, click **"Dispose"** -> Enter final resolution remarks -> Click **"Confirm"**.
7. **Coordinate on Overlaps:** Click **"Overlap Center"** in the sidebar. Look for Tier B flags involving your bureau cases.

### B. Regional Officer (`regional_north`)
1. **Sign in:** Use username `regional_north` and password `Demo@12345`.
2. **Explore Regional Institutions:** Click **"Institutions"** in the left navigation.
3. **Inspect Institution History:** Click on an institution in the North region (e.g., *Synthetic Aster Institute of Engineering 01*). View all complaint cases across all five bureaus unified on one screen.
4. **Check Overlaps:** Look for institutions marked with the yellow **"Tier A"** badge indicating that multiple bureaus have concurrent complaints open for that campus.

### C. Senior Management (`senior`)
1. **Sign in:** Use username `senior` and password `Demo@12345`.
2. **High-Level Dashboard:** Check overall status metrics: **Pending**, **Under process**, **Disposed**, **Transferred**, and **Escalated** cards.
3. **Monitor Systemic Delays:** Click on the red **"Beyond SLA"** tile to inspect overdue cases across all bureaus.
4. **Intervene & Escalate:** Open an overdue or stalled case. Click the yellow **"Escalate"** button, type instructions for the handling bureau officer, and confirm. This logs an audited escalation event in the case timeline.
5. **Analyze Trends:** Review the **"Monthly case trend"** and **"Case ageing"** distribution charts.

### D. System Administrator (`admin`)
1. **Sign in:** Use username `admin` and password `Demo@12345`.
2. **Advancing Demo Time:** Click **"Advance demo 30 days"** on the Dashboard header to simulate temporal progression, trigger automated reminder notifications, overdue alerts, and SLA escalations.
3. **Manage Overlaps:** Access **"Overlap Center"** to link related complaints or dismiss false positive flags.
4. **Generate Official Reports:** Go to **"Reports"**, select any of the 8 report types, and click **"CSV"** or **"JSON"** to download instant audit reports.
5. **Review AI Evaluation:** Access the **"Evaluation"** tab to inspect mathematically verified precision, recall, confusion matrix, and threshold tuning on held-out test splits.

---

## 3. How to Read the Dashboard

- **Status Tiles (Top Cards):**
  - **Pending (Amber):** Grievances received and acknowledged, awaiting initial review.
  - **Under process (Blue):** Actively under investigation or review.
  - **Disposed (Green):** Successfully resolved or closed cases.
  - **Transferred (Purple):** Formally routed to another bureau or regional cell.
  - **Escalated (Red):** Exceeded SLA thresholds or escalated by senior officials.
  - **Beyond SLA (Red Border):** Urgent list of open cases that have passed their expected disposal date.
- **Visual Analytics:**
  - **Cases by Bureau and Status:** Stacked bar chart showing workload balance across RB, PGRC, Approval, Academic, and Finance.
  - **Monthly Case Trend:** Dual line chart comparing intake volume against disposal velocity over the past 12 months.
  - **Case Ageing Bands:** Ageing distribution (0–7 days, 8–30 days, 31–60 days, 61–90 days, 90+ days).
  - **Open Overlaps:** Quick preview of uncoordinated cross-bureau complaint flags.

---

## 4. How to Review Overlaps (Overlap Center)

Header text: **"Potential Overlapping Cases - Coordination Required"**

### Understanding Overlap Tiers
- **Tier A (Campus Coordination Flag):** Triggered automatically whenever an institution has open complaint cases registered in 2 or more distinct bureaus simultaneously. No AI required; this is a strict coordination rule.
- **Tier B (Case Pair Flag):** Triggered when the AI engine detects high semantic or factual similarity between two specific cross-bureau cases at the same institution.

### Deciphering Similarity Scores & Reason Codes
Each Tier B flag provides a composite similarity score ($0.00$ to $1.00$) calculated as:
$$\text{Score} = 0.45 \times \text{Text Similarity} + 0.30 \times \text{Category Match} + 0.15 \times \text{Time Proximity} + 0.10 \times \text{Reference Overlap}$$

**Reason Code Meanings:**
- `HIGH_TEXT_SIMILARITY`: The grievance text has $\ge 70\%$ TF-IDF cosine similarity across word and character n-grams.
- `SAME_CATEGORY`: Both cases concern the same grievance domain (e.g., Admissions, Examination Services).
- `WITHIN_30_DAYS`: Both cases were received within 30 days of each other.
- `SHARED_REFERENCE`: Cases cite identical case, file, or portal reference numbers.
- `SHARED_COMPLAINANT_REF`: Complaints originated from the same complainant or grievance ticket identifier.
- `DIFFERENT_BUREAU`: The two complaints are being handled by different bureaus.

### Linking Cases
1. Click **"Review"** on an open overlap flag.
2. Select which bureau will serve as the **Lead Coordinating Bureau**.
3. Type coordination notes in the text box.
4. Click **"Link for coordination"**.
5. **Outcome:** A prominent teal coordination banner is pinned to both cases, cross-links are established in the database, and an immutable `LINKED` action is recorded on both audit timelines.

### Dismissing Flags
1. Click **"Dismiss"** on an open flag if complaints are distinct matters.
2. The flag moves to `DISMISSED` state.
3. **Suppression Guarantee:** Future automated scans will never re-raise this flag unless a case's summary text or status changes after the dismissal timestamp.

---

## 5. How to Read Alerts

Click **"Alerts"** in the left sidebar:
- **DUE_SOON:** Case is approaching 75% of prescribed disposal timeframe.
- **OVERDUE:** Case has passed its expected disposal date.
- **REMINDER:** No officer action has been recorded for 7 consecutive days.
- **ESCALATION:** Case is 10 days past due; automated system escalation applied.
- **OVERLAP:** New cross-bureau overlap detected requiring review.
- **Mark as Read:** Click the checkmark icon or **"Mark read"** to clear notifications.

---

## 6. How to Export Reports

1. Click **"Reports"** in the left sidebar.
2. Choose from the 8 available report types:
   - `Bureau Workload`
   - `Regional Breakdown`
   - `Institution Summary`
   - `Case Ageing Distribution`
   - `Disposal Rate Analysis`
   - `Status Overview`
   - `Overlap Coordination Summary`
   - `Monthly Performance Trend`
3. Click **"CSV"** to download an Excel-compatible spreadsheet, or **"JSON"** for data integration.

---

## 7. AICTE Intelligence Query Copilot (Offline NLP Assistant)

The dashboard includes a built-in **AI Copilot** accessible from the top header on any page (`✨ AI Copilot` button).

### Key Highlights for Evaluators:
- **Zero Cloud / External API Dependencies:** Operates 100% locally and offline without external network calls (no OpenAI key or paid subscriptions needed). Sub-50ms query response time.
- **Intent Recognition & Direct Deep-Linking:** Parses plain English requests and returns matching cases, institution summaries, bureau workload totals, or direct filtered links.

### Sample Officer Prompts to Demonstrate to Judges:
1. *"Show cases beyond SLA"* $\rightarrow$ Returns overdue cases count and one-click button to view the filtered list.
2. *"Active RB vs PGRC overlaps"* $\rightarrow$ Displays campus-level Tier A and case-pair Tier B counts with direct Overlap Center link.
3. *"Regulation Bureau workload"* $\rightarrow$ Summarizes total and open case balance for RB.
4. *"Complaints for Synthetic Aster Institute"* $\rightarrow$ Fetches campus permanent ID (`SYN-00001`) and latest complaint details.
5. *"Find scholarship delay grievances"* $\rightarrow$ Surfaces topic-specific complaints across technical institutions.

---

## 8. Recommended 3-Minute Demo Script

| Time | Screen | Action & Talking Point |
| :--- | :--- | :--- |
| **0:00 - 0:40** | **Dashboard** | Log in as `admin`. Point out the unified metrics across bureaus. Highlight the *Beyond SLA* tile and the *Cases by bureau and status* chart. Explain that AICTE officers currently have no single view across cells. |
| **0:40 - 1:15** | **AICTE Query Copilot** | Click **"AI Copilot"** in the header. Click prompt *"Active RB vs PGRC overlaps"* to show sub-50ms natural language retrieval with deep-links, demonstrating the offline NLP innovation. |
| **1:15 - 1:55** | **Overlap Center** | Navigate to *Overlap Center*. Show the header: *"Potential Overlapping Cases - Coordination Required"*. Review a Tier A institution flag where RB and PGRC both have active cases. Show a Tier B pair with high semantic similarity. Click **"Link for coordination"**, designate RB as lead, and submit. |
| **1:55 - 2:30** | **Case Detail & Actions** | Open the linked case. Show the teal banner: *"This case is linked for cross-bureau coordination"*. Click **"Dispose"**, add remarks, and confirm. Show the append-only timeline update. Point out masked complainant reference when viewing other bureaus. |
| **2:30 - 3:00** | **Institutions & Evaluation** | Open *Institutions*, select an institution to show cross-bureau case consolidation. Open *Evaluation*, explain the 0.75 F1 score on held-out institutions and conclude on operational impact: zero parallel contradictory actions and faster student redressal. |

---

## 9. Limitations & Constraints

1. **Synthetic Data Only:** All institutions, complaints, student names, and SLA deadlines are synthetic demo fixtures. SLA parameters are illustrative placeholders.
2. **File Attachments:** Document attachments are out of scope for this monitoring coordinator layer.
3. **No External Network Calls:** The AI matcher and Query Copilot operate 100% locally using TF-IDF, RapidFuzz, and local intent parsing; no external LLM APIs are invoked at runtime.

