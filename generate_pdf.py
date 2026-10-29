"""Generate a styled PDF document for the Demo Video Script & Feature Guide."""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "SIH26264: Integrated AICTE Complaint Coordination Dashboard")
            self.drawRightString(558, 750, "Demo Video Script & Feature Guide")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)
        
        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        
        self.drawString(54, 32, "AICTE Confidential / Prototype Demonstration Guide — Uses Synthetic Data")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()


def build_pdf(filename="AICTE_Dashboard_Demo_Script_and_Feature_Guide.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    
    styles = getSampleStyleSheet()
    
    # Custom palette
    NAVY = colors.HexColor("#153a5b")
    TEAL = colors.HexColor("#0f766e")
    DARK = colors.HexColor("#0f172a")
    SLATE = colors.HexColor("#334155")
    MUTED = colors.HexColor("#64748b")
    LIGHT_BG = colors.HexColor("#f8fafc")
    BORDER_COL = colors.HexColor("#e2e8f0")
    
    # Paragraph styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=NAVY,
        alignment=TA_LEFT,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=TEAL,
        alignment=TA_LEFT,
        spaceAfter=14,
    )
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=NAVY,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=TEAL,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=DARK,
        spaceAfter=6,
    )
    script_dialogue = ParagraphStyle(
        'ScriptDialogue',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9.5,
        leading=14,
        textColor=DARK,
    )
    script_action = ParagraphStyle(
        'ScriptAction',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=NAVY,
    )
    meta_label = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=TEAL,
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=DARK,
    )
    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.white,
    )
    
    story = []
    
    # Document Header Banner
    story.append(Paragraph("AICTE COMPLAINT COORDINATION DASHBOARD", title_style))
    story.append(Paragraph("Problem Statement SIH26264 • Official Demo Video Script & Master Feature Guide", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=TEAL, spaceBefore=0, spaceAfter=12))
    
    # Metadata Overview Box
    meta_data = [
        [
            Paragraph("<b>Target Audience:</b> AICTE Evaluators & Jury", table_cell),
            Paragraph("<b>Target Duration:</b> 3 to 4 Minutes", table_cell),
            Paragraph("<b>Default Demo User:</b> admin / Demo@12345", table_cell),
        ],
        [
            Paragraph("<b>App URLs:</b> Local: :5173 | Vercel Live", table_cell),
            Paragraph("<b>Scope:</b> Oversight/Coordination (Zero Cloud LLM)", table_cell),
            Paragraph("<b>Data Status:</b> 301 Synthetic Cases (Seed 42)", table_cell),
        ]
    ]
    t_meta = Table(meta_data, colWidths=[170, 170, 164])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COL),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COL),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 14))
    
    # SECTION 1: VIDEO SCRIPT
    story.append(Paragraph("PART 1: Official 3-4 Minute Demo Video Script", h1_style))
    story.append(Paragraph("Your team can read the <i>Speaker Voiceover</i> column word-for-word while performing the matching <i>On-Screen Actions</i>.", body_style))
    story.append(Spacer(1, 4))
    
    scenes = [
        (
            "Scene 1: Problem Statement & Executive Vision (0:00 - 0:35)",
            "Start on the Login Page (/login). Point out prefilled admin / Demo@12345 credentials. Click 'Sign In' and land on the Dashboard.",
            "\"Technical education institutions across India receive hundreds of complaints every month through multiple AICTE cells—such as the Regulation Bureau (RB), Public Grievance Redressal Cell (PGRC), and Approval. Because these bureaus operate in separate silos without central monitoring, colleges often receive contradictory notices, duplicate inquiries are launched, and cases languish past prescribed timelines.\n\nWelcome to the Integrated AICTE Complaint Coordination & Monitoring Dashboard. Built strictly as an intelligent coordination layer over existing bureau systems, this single-window workspace gives AICTE leadership 100% real-time visibility across all five bureaus.\""
        ),
        (
            "Scene 2: Real-Time Executive Dashboard & SLA Visibility (0:35 - 1:15)",
            "Move mouse across top status tiles (Pending, Under process, Disposed, Transferred, Escalated). Hover over the 'Beyond SLA' red badge, the 'Cases by bureau and status' stacked bar chart, and monthly trends.",
            "\"At a glance, leadership sees the complete national workload. The top status tiles break down active grievances: Pending, Under Process, Transferred, Escalated, and Disposed.\n\nDown here, the Cases by Bureau and Status chart visualizes workload balance across Regulation, PGRC, Approval, Academic, and Finance. Right here, the Beyond SLA widget highlights cases exceeding their 30-day disposal deadline. In our system, SLA warnings trigger at 75% elapsed time, officer inactivity reminders fire after 7 days of silence, and automated escalation kicks in if overdue by 10 days.\""
        ),
        (
            "Scene 3: Innovation: Offline AI Overlap Center (1:15 - 1:55)",
            "Navigate to 'Overlap Center'. Point to exact header: 'Potential Overlapping Cases - Coordination Required'. Show Tier A and Tier B tabs. Open a Tier B flag with ~78% similarity. Click 'Review' -> Choose 'Regional Bureau' as lead -> Type coordination note -> Click 'Link for coordination'.",
            "\"Now for our core innovation: Cross-Bureau Overlap Detection. With no centralized coordination, students or faculty frequently file the same issue with both Regulation Bureau and PGRC.\n\nOur engine operates in two tiers:\n• Tier A Flags are campus-level alerts raised whenever an institution has open cases in 2 or more distinct bureaus simultaneously.\n• Tier B Flags use an offline ML engine combining character and word n-gram TF-IDF cosine similarity, category matching, and 90-day time proximity to score complaints from 0 to 1.\n\nHere, the system flagged two cases for the same college with 78% similarity. As an officer, I review them side by side, appoint the Regulation Bureau as Lead Coordinating Bureau, and link them. Notice that our engine runs 100% locally—zero cloud latency, zero external API cost, and zero privacy leakage.\""
        ),
        (
            "Scene 4: Case Tracking, RBAC Whistleblower Privacy & Immutable Audit (1:55 - 2:35)",
            "Open the linked case (e.g. RB-2026-00001). Show the pinned teal Coordination Banner. Highlight the 10 core fields. Scroll down to Action History. Click 'Dispose' -> Enter remarks -> Click 'Confirm'. Point out masked complainant reference.",
            "\"Opening the case, we see a complete 360-degree profile with all 10 core tracking fields mandated by AICTE: unique Case ID, receipt date, assigned officer, expected disposal date, and next action required. Notice the prominent teal banner confirming that this case is formally linked for multi-bureau coordination.\n\nFor privacy and whistleblower safety, strict Role-Based Access Control is enforced at the backend: complainant references are masked whenever viewed by officers outside that bureau or region.\n\nEvery status transition is governed by an append-only audit ledger—actions are INSERT-only, meaning no official can ever tamper with or delete past timestamps. Let's dispose this case—the status updates in real time, writing an immutable record with officer ID and timestamp.\""
        ),
        (
            "Scene 5: Centralized Institution Profiles & Offline AI Copilot (2:35 - 3:05)",
            "Click 'Institutions' in sidebar. Search for an institution (e.g. 'Synthetic Aster'). Open profile to show AICTE Permanent ID (SYN-00001) and unified complaints. Click '✨ AI Copilot' button in top header. Click 'Show cases beyond SLA'.",
            "\"Under Institutions, every technical college has a Centralized Profile keyed by its AICTE Permanent ID. Instead of checking separate databases, an officer sees all historical and active complaints across all five bureaus on one single page.\n\nTo empower non-technical officers, we added the AICTE Intelligence Copilot. Clicking the copilot in the header, an officer can query in plain English: 'Show cases beyond SLA' or 'Active RB vs PGRC overlaps'. In under 50 milliseconds, it parses intent locally and provides one-click deep links to the exact records.\""
        ),
        (
            "Scene 6: Official Reports, Rigorous AI Evaluation & Closing (3:05 - 3:40)",
            "Click 'Reports'. Show the 8 report types dropdown. Click 'CSV' to download spreadsheet. Click 'Evaluation' tab to show confusion matrix and precision/recall metrics.",
            "\"For audits and parliamentary reviews, the Reports module generates 8 official reports in one click—bureau workload, regional distributions, ageing bands, and disposal rates—downloadable in both Excel-ready CSV and JSON formats.\n\nFinally, under Evaluation, we hold our model accountable. Evaluated on a strict, held-out test split of 32 institution groups, our overlap engine achieved a 0.75 F1 score with 85.7% recall, beating the baseline rule without hallucinated metrics.\n\nThe AICTE Complaint Coordination Dashboard stops duplicate effort, eliminates conflicting bureau decisions, and ensures prompt grievance redressal for technical education across India. Thank you!\""
        )
    ]
    
    for title, action, speech in scenes:
        scene_content = [
            [Paragraph(f"<b>{title}</b>", table_header), ""],
            [
                Paragraph("<b>On-Screen Action:</b><br/>" + action.replace("\n", "<br/>"), script_action),
                Paragraph("<b>Speaker Voiceover:</b><br/>" + speech.replace("\n\n", "<br/><br/>"), script_dialogue),
            ]
        ]
        t_scene = Table(scene_content, colWidths=[180, 324])
        t_scene.setStyle(TableStyle([
            ('SPAN', (0,0), (1,0)),
            ('BACKGROUND', (0,0), (-1,0), NAVY),
            ('BACKGROUND', (0,1), (-1,1), LIGHT_BG),
            ('BOX', (0,0), (-1,-1), 1, BORDER_COL),
            ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COL),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(t_scene)
        story.append(Spacer(1, 8))
        
    story.append(PageBreak())
    
    # SECTION 2: MASTER FEATURE GUIDE
    story.append(Paragraph("PART 2: Complete Feature-by-Feature Operational Guide", h1_style))
    story.append(Paragraph("Step-by-step instructions for demonstrating and navigating every screen in the application.", body_style))
    story.append(Spacer(1, 4))
    
    features = [
        (
            "1. Real-Time Dashboard (/dashboard)",
            [
                "<b>Status Cards:</b> Amber for Pending, Blue for Under Process, Green for Disposed, Purple for Transferred, Red for Escalated.",
                "<b>Beyond SLA Badge:</b> Instantly filters complaints older than 30 days.",
                "<b>Advance Demo 30 Days Button:</b> Shifts the synthetic clock forward by 30 days to trigger real-time overdue alerts, reminder notifications, and automated system escalations.",
                "<b>Visual Workload Analytics:</b> Stacked bar chart for 5 bureaus (RB, PGRC, Approval, Academic, Finance), 12-month intake vs disposal trend, and 5-tier ageing histogram."
            ]
        ),
        (
            "2. Case Directory & 10 Core Tracking Fields (/cases & /cases/:id)",
            [
                "<b>Multi-Dimensional Search & Filters:</b> Search by Case ID, AICTE Permanent ID, institution name, bureau, region, status, priority, and beyond-SLA.",
                "<b>10 AICTE Mandated Fields:</b> (1) Unique Case ID, (2) Receipt Date, (3) Complaint Category, (4) Status, (5) Assigned Bureau, (6) Assigned Officer Name & ID, (7) Last Action Taken, (8) Date of Last Action, (9) Next Action Required, (10) Expected Disposal Date.",
                "<b>Workflow Transitions:</b> Strict finite state transitions (PENDING -> UNDER_PROCESS -> DISPOSED; TRANSFERRED; ESCALATED; REOPENED with mandatory remarks).",
                "<b>Append-Only Audit Ledger:</b> Every transition writes an immutable INSERT-only row into case_actions with actor identity, bureau code, and exact ISO timestamp."
            ]
        ),
        (
            "3. Cross-Bureau Overlap Coordination Center (/overlaps)",
            [
                "<b>Mandatory AICTE Header:</b> Prominently labeled 'Potential Overlapping Cases - Coordination Required'.",
                "<b>Tier A (Campus Coordination Flag):</b> Raised when >= 2 distinct bureaus have open cases for the same institution simultaneously.",
                "<b>Tier B (Semantic Match Flag):</b> Raised when cross-bureau cases at the same campus match on TF-IDF cosine similarity, category, and date proximity.",
                "<b>Composite Match Formula:</b> 0.45 * text_similarity + 0.30 * category_match + 0.15 * time_proximity + 0.10 * ref_overlap.",
                "<b>Coordination Actions:</b> (1) <i>Link for coordination</i> pins a persistent teal banner and designates a Lead Bureau; (2) <i>Dismiss</i> suppresses future re-triggering unless case summary changes."
            ]
        ),
        (
            "4. Centralized Institution Profiles (/institutions & /institutions/:id)",
            [
                "<b>Permanent Identification:</b> Keyed by unique AICTE Permanent ID (e.g. SYN-00001) and normalized institution names.",
                "<b>Consolidated Multi-Bureau History:</b> Shows all past, current, and transferred complaints ever registered for this campus in one place.",
                "<b>Fuzzy Resolver Engine:</b> Handles abbreviations (inst -> institute, engg -> engineering, tech -> technology) using RapidFuzz with >=0.92 auto-link."
            ]
        ),
        (
            "5. Automated Alerts & SLA Escalation Engine (/alerts)",
            [
                "<b>5 Distinct Notification Types:</b> DUE_SOON (75% of timeline), OVERDUE (past 30 days), REMINDER (7 days inactivity), ESCALATION (10 days overdue), OVERLAP (new cross-bureau duplicate detected).",
                "<b>Deduplication Rule:</b> At most one alert per (case, alert_type, day) to prevent officer notification fatigue.",
                "<b>Automated System Escalator:</b> Automatically escalates stalled cases and logs an ESCALATED audit action under the 'system' officer."
            ]
        ),
        (
            "6. Parliamentary & Audit Reports Generator (/reports)",
            [
                "<b>8 Official Report Types:</b> Bureau Workload, Regional Breakdown, Institution Summary, Ageing Distribution, Disposal Rate Analysis, Status Overview, Overlap Coordination Summary, Monthly Trend.",
                "<b>One-Click Export:</b> Available as clean, RFC-compliant CSV for Excel analysis or formatted JSON for integration."
            ]
        ),
        (
            "7. Mathematical AI Model Evaluation (/evaluation)",
            [
                "<b>Zero Hallucinated Metrics:</b> Evaluated on a 60/40 institution-group holdout split with seed 42.",
                "<b>Held-Out Performance:</b> Achieves 0.75 F1 score and 85.7% Recall on unseen colleges, outperforming the baseline heuristic rule (0.64 precision).",
                "<b>Full Transparency:</b> Displays confusion matrix (TP, FP, TN, FN) and false positive analysis for reviewer scrutiny."
            ]
        ),
        (
            "8. AICTE Query Copilot (Offline NLP Assistant)",
            [
                "<b>100% Offline / No External APIs:</b> Zero cloud LLM calls, zero network lag (<50ms execution), completely secure for restricted intranets.",
                "<b>Direct Deep-Linking:</b> Responds to natural queries ('Show cases beyond SLA', 'Active RB vs PGRC overlaps', 'Regulation Bureau workload') with direct actionable buttons."
            ]
        ),
    ]
    
    for title, points in features:
        content = [
            [Paragraph(f"<b>{title}</b>", table_header)],
            [Paragraph("<br/>".join([f"• {p}" for p in points]), table_cell)]
        ]
        t_feat = Table(content, colWidths=[504])
        t_feat.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), TEAL),
            ('BACKGROUND', (0,1), (-1,1), LIGHT_BG),
            ('BOX', (0,0), (-1,-1), 1, BORDER_COL),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
        ]))
        story.append(t_feat)
        story.append(Spacer(1, 6))
        
    story.append(Spacer(1, 10))
    story.append(Paragraph("PART 3: Quick Reference Credential Table", h1_style))
    
    cred_table_data = [
        [
            Paragraph("<b>Username</b>", table_header),
            Paragraph("<b>Password</b>", table_header),
            Paragraph("<b>Role & Privilege Level</b>", table_header),
            Paragraph("<b>Assigned Bureau / Region</b>", table_header),
        ],
        [
            Paragraph("<b>admin</b>", table_cell),
            Paragraph("Demo@12345", table_cell),
            Paragraph("ADMIN (All Bureaus, Demo Clock, Reports)", table_cell),
            Paragraph("National Headquarters (All Bureaus)", table_cell),
        ],
        [
            Paragraph("<b>senior</b>", table_cell),
            Paragraph("Demo@12345", table_cell),
            Paragraph("SENIOR_MGMT (Read All + Escalate Only)", table_cell),
            Paragraph("Executive Oversight", table_cell),
        ],
        [
            Paragraph("<b>rb_officer</b>", table_cell),
            Paragraph("Demo@12345", table_cell),
            Paragraph("BUREAU_OFFICER (Act on RB cases only)", table_cell),
            Paragraph("Regulation Bureau (RB)", table_cell),
        ],
        [
            Paragraph("<b>pgrc_officer</b>", table_cell),
            Paragraph("Demo@12345", table_cell),
            Paragraph("BUREAU_OFFICER (Act on PGRC cases only)", table_cell),
            Paragraph("Public Grievance Redressal Cell", table_cell),
        ],
        [
            Paragraph("<b>regional_north</b>", table_cell),
            Paragraph("Demo@12345", table_cell),
            Paragraph("REGIONAL_OFFICER (Act on North region)", table_cell),
            Paragraph("Northern Regional Office", table_cell),
        ],
    ]
    t_creds = Table(cred_table_data, colWidths=[90, 85, 185, 144])
    t_creds.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('BACKGROUND', (0,1), (-1,-1), LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COL),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COL),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_creds)
    
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully built: {filename}")

if __name__ == "__main__":
    build_pdf()

