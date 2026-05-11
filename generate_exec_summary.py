from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import PageBreak
import datetime

OUTPUT = "MACAE_Executive_Summary.pdf"

# Brand colors
BLUE_DARK  = HexColor("#0f3460")
BLUE_MID   = HexColor("#1a6baa")
BLUE_LIGHT = HexColor("#e8f1fa")
ACCENT     = HexColor("#0078d4")   # Microsoft blue
GRAY_DARK  = HexColor("#2d2d2d")
GRAY_MID   = HexColor("#555555")
GRAY_LIGHT = HexColor("#f5f5f5")
WHITE      = white
RULE_COLOR = HexColor("#0078d4")


def build_styles():
    base = getSampleStyleSheet()

    styles = {}

    styles["cover_title"] = ParagraphStyle(
        "cover_title",
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=28,
        textColor=WHITE,
        alignment=TA_LEFT,
    )
    styles["cover_subtitle"] = ParagraphStyle(
        "cover_subtitle",
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        textColor=HexColor("#c8dff5"),
        alignment=TA_LEFT,
    )
    styles["section_header"] = ParagraphStyle(
        "section_header",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=ACCENT,
        spaceBefore=10,
        spaceAfter=3,
        tracking=60,
    )
    styles["body"] = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=8.5,
        leading=13,
        textColor=GRAY_DARK,
        alignment=TA_JUSTIFY,
    )
    styles["body_small"] = ParagraphStyle(
        "body_small",
        fontName="Helvetica",
        fontSize=7.8,
        leading=12,
        textColor=GRAY_MID,
        alignment=TA_JUSTIFY,
    )
    styles["bullet"] = ParagraphStyle(
        "bullet",
        fontName="Helvetica",
        fontSize=8.5,
        leading=13,
        textColor=GRAY_DARK,
        leftIndent=12,
        bulletIndent=0,
        spaceAfter=2,
    )
    styles["table_header"] = ParagraphStyle(
        "table_header",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=WHITE,
    )
    styles["table_cell"] = ParagraphStyle(
        "table_cell",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=GRAY_DARK,
    )
    styles["footer"] = ParagraphStyle(
        "footer",
        fontName="Helvetica",
        fontSize=7,
        leading=10,
        textColor=HexColor("#999999"),
        alignment=TA_CENTER,
    )
    styles["kpi_label"] = ParagraphStyle(
        "kpi_label",
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=ACCENT,
        alignment=TA_CENTER,
    )
    styles["kpi_desc"] = ParagraphStyle(
        "kpi_desc",
        fontName="Helvetica",
        fontSize=7.5,
        leading=11,
        textColor=GRAY_MID,
        alignment=TA_CENTER,
    )
    return styles


def header_band(canvas, doc):
    """Draws the top color band and footer on every page."""
    W, H = letter
    canvas.saveState()

    # Top band
    canvas.setFillColor(BLUE_DARK)
    canvas.rect(0, H - 0.45 * inch, W, 0.45 * inch, fill=1, stroke=0)

    # Title in band
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(0.6 * inch, H - 0.28 * inch,
                      "MULTI-AGENT CUSTOM AUTOMATION ENGINE  |  Executive Summary")

    # Page number right
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor("#aaccee"))
    canvas.drawRightString(W - 0.6 * inch, H - 0.28 * inch,
                           f"Page {doc.page}")

    # Bottom rule + footer text
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(1)
    canvas.line(0.6 * inch, 0.45 * inch, W - 0.6 * inch, 0.45 * inch)

    canvas.setFillColor(HexColor("#999999"))
    canvas.setFont("Helvetica", 7)
    today = datetime.date.today().strftime("%B %Y")
    canvas.drawString(0.6 * inch, 0.28 * inch,
                      f"Microsoft  |  Confidential  |  {today}")
    canvas.drawRightString(W - 0.6 * inch, 0.28 * inch,
                           "github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator")

    canvas.restoreState()


def make_section(title, styles):
    elems = []
    elems.append(Paragraph(title.upper(), styles["section_header"]))
    elems.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT, spaceAfter=4))
    return elems


def bullet_item(text, styles):
    return Paragraph(f"<bullet>•</bullet> {text}", styles["bullet"])


def build_pdf():
    S = build_styles()
    W, H = letter
    margin = 0.6 * inch
    top_margin = 0.75 * inch + 0.45 * inch  # below header band

    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=top_margin,
        bottomMargin=0.65 * inch,
    )

    story = []

    # ── PAGE 1 ───────────────────────────────────────────────────────────────

    # Hero banner
    hero_data = [[
        Paragraph(
            "<b>Multi-Agent Custom Automation Engine</b>",
            ParagraphStyle("ht", fontName="Helvetica-Bold", fontSize=18,
                           leading=24, textColor=WHITE)
        ),
    ]]
    hero_table = Table(hero_data, colWidths=[W - 2 * margin])
    hero_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_MID),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
    ]))
    story.append(hero_table)

    # Tagline under hero
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "An open-source Azure solution accelerator that deploys coordinated AI agents to automate "
        "complex, multi-department business workflows — from a single natural-language task description.",
        ParagraphStyle("tag", fontName="Helvetica-Oblique", fontSize=9, leading=14,
                       textColor=GRAY_MID, alignment=TA_JUSTIFY)
    ))
    story.append(Spacer(1, 10))

    # ── KPI row ──────────────────────────────────────────────────────────────
    kpi_data = [
        [
            Paragraph("5+", S["kpi_label"]),
            Paragraph("3", S["kpi_label"]),
            Paragraph("Azure", S["kpi_label"]),
            Paragraph("1-cmd", S["kpi_label"]),
        ],
        [
            Paragraph("Validated Industry\nUse Cases", S["kpi_desc"]),
            Paragraph("Specialized Agent\nDomains (MCP)", S["kpi_desc"]),
            Paragraph("Native Cloud\nDeployment", S["kpi_desc"]),
            Paragraph("azd up\nDeployment", S["kpi_desc"]),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[(W - 2 * margin) / 4] * 4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), BLUE_LIGHT),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LINEAFTER",     (0, 0), (2, -1), 0.5, HexColor("#c0d8ef")),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 12))

    # ── Two-column layout: Purpose | Architecture ─────────────────────────
    col_w = (W - 2 * margin - 0.2 * inch) / 2

    # Left col
    left = []
    left += make_section("Purpose & Problem Statement", S)
    left.append(Paragraph(
        "Organizations face mounting pressure to automate cross-departmental workflows — "
        "onboarding new hires, reviewing contracts, coordinating marketing launches — each "
        "requiring input from multiple teams. Traditional point solutions demand a custom app "
        "per workflow, creating silos, duplicated effort, and fragile integrations.",
        S["body"]
    ))
    left.append(Spacer(1, 5))
    left.append(Paragraph(
        "MACAE solves this with a <b>single, reusable orchestration platform</b>. Users "
        "describe what they need in plain language; the engine recruits the right AI agents, "
        "builds a plan, executes each step, and validates the result — with full auditability.",
        S["body"]
    ))
    left.append(Spacer(1, 10))
    left += make_section("Key Benefits", S)
    benefits = [
        "<b>Process Efficiency</b> — automates repetitive coordination tasks end-to-end",
        "<b>Error Reduction</b> — multi-agent validation catches mistakes before completion",
        "<b>Resource Optimization</b> — humans focus on judgment; agents handle execution",
        "<b>Scalability</b> — one platform handles unlimited workflow types without rebuilding",
        "<b>GenAI Adoption</b> — reduces friction of deploying AI across the organization",
        "<b>Cost Efficiency</b> — usage-based Azure pricing with no fixed per-workflow cost",
    ]
    for b in benefits:
        left.append(bullet_item(b, S))
        left.append(Spacer(1, 1))

    # Right col
    right = []
    right += make_section("Solution Architecture", S)
    right.append(Paragraph(
        "A three-tier, fully containerized architecture deployed on Microsoft Azure:",
        S["body"]
    ))
    right.append(Spacer(1, 4))

    arch_data = [
        [Paragraph("Layer", S["table_header"]),
         Paragraph("Technology", S["table_header"]),
         Paragraph("Role", S["table_header"])],
        ["Frontend",  "React / TypeScript\nFluent UI v9",      "Chat UI for task input & monitoring"],
        ["Backend",   "Python / FastAPI\nAzure AI Agent SDK",  "Orchestration & agent coordination"],
        ["MCP Server","Python / FastMCP",                      "Domain tools exposed to agents"],
        ["Data",      "Azure Cosmos DB",                       "Tasks, plans, audit history"],
        ["AI Engine", "Azure OpenAI\n(GPT-4 class)",           "Agent reasoning & generation"],
        ["Infra",     "Container Apps\nKey Vault · Managed ID","Hosting, secrets, identity"],
    ]
    col_w_arch = [col_w * 0.22, col_w * 0.38, col_w * 0.40]
    arch_table = Table(
        [[Paragraph(str(r[0]), S["table_header"] if i == 0 else S["table_cell"]),
          Paragraph(str(r[1]), S["table_header"] if i == 0 else S["table_cell"]),
          Paragraph(str(r[2]), S["table_header"] if i == 0 else S["table_cell"])]
         for i, r in enumerate(arch_data)],
        colWidths=col_w_arch
    )
    arch_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  BLUE_DARK),
        ("BACKGROUND",    (0, 1), (-1, 1),  BLUE_LIGHT),
        ("BACKGROUND",    (0, 2), (-1, 2),  WHITE),
        ("BACKGROUND",    (0, 3), (-1, 3),  BLUE_LIGHT),
        ("BACKGROUND",    (0, 4), (-1, 4),  WHITE),
        ("BACKGROUND",    (0, 5), (-1, 5),  BLUE_LIGHT),
        ("BACKGROUND",    (0, 6), (-1, 6),  WHITE),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("GRID",          (0, 0), (-1, -1), 0.3, HexColor("#c0d8ef")),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    right.append(arch_table)
    right.append(Spacer(1, 8))
    right += make_section("Agentic Flow", S)
    right.append(Paragraph(
        "1. <b>Orchestrator Agent</b> receives the task and generates an execution plan.<br/>"
        "2. <b>Specialized Sub-Agents</b> execute plan steps using MCP domain tools.<br/>"
        "3. <b>Validation Layer</b> cross-checks results before surfacing output.<br/>"
        "4. <b>Full audit trail</b> persisted to Cosmos DB for traceability.",
        S["body"]
    ))

    two_col = Table([[left, right]], colWidths=[col_w, col_w], rowHeights=None)
    two_col.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
        ("LINEAFTER",    (0, 0), (0, -1),  0.5, HexColor("#c0d8ef")),
        ("RIGHTPADDING", (0, 0), (0, -1),  8),
        ("LEFTPADDING",  (1, 0), (1, -1),  8),
    ]))
    story.append(two_col)

    # ── PAGE 2 ───────────────────────────────────────────────────────────────
    story.append(PageBreak())

    # ── Use Cases table ────────────────────────────────────────────────────
    story += make_section("Validated Use Cases", S)

    uc_header = [
        Paragraph("Use Case",   S["table_header"]),
        Paragraph("Persona",    S["table_header"]),
        Paragraph("Challenge",  S["table_header"]),
        Paragraph("MACAE Outcome", S["table_header"]),
    ]
    uc_rows = [
        ["Employee Onboarding",       "HR Manager",              "Disconnected steps: IT setup, paperwork, compliance training require manual coordination and cause delays.", "Agents automate each onboarding step in sequence — ID card, payroll, benefits, mentor assignment — in minutes."],
        ["Product Marketing Launch",  "Marketing Executive",     "Release plans require sign-off from Engineering, Design, and Compliance, leading to misalignment and delays.", "Dynamic agent team drafts timelines, assigns owners, and validates compliance automatically."],
        ["RFP / Contract Review",     "VP Finance / Legal",      "Manual review under tight deadlines misses compliance gaps and slows decision-making.", "AI agents review documents, flag risks, recommend remediation, and log decisions with full traceability."],
        ["Retail Customer Remediation","Customer Success Mgr",   "Fragmented data, manual workflows, and difficulty engaging the right teams slow resolution.", "Agents analyze satisfaction signals, identify root cause, and orchestrate remediation steps across teams."],
        ["Contract Compliance",       "Compliance Counsel",      "Reviewing contracts for regulatory compliance is labor-intensive and error-prone.", "Agents scan contracts, surface violations, generate remediation plans, and maintain audit logs."],
    ]

    uc_col_w = [(W - 2 * margin) * p for p in [0.18, 0.14, 0.34, 0.34]]
    uc_table_data = [uc_header]
    for i, row in enumerate(uc_rows):
        bg = BLUE_LIGHT if i % 2 == 0 else WHITE
        uc_table_data.append([Paragraph(c, S["table_cell"]) for c in row])

    uc_table = Table(uc_table_data, colWidths=uc_col_w, repeatRows=1)
    uc_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  BLUE_DARK),
        *[("BACKGROUND",  (0, i+1), (-1, i+1), BLUE_LIGHT if i % 2 == 0 else WHITE)
          for i in range(len(uc_rows))],
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("GRID",          (0, 0), (-1, -1), 0.3, HexColor("#c0d8ef")),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(uc_table)
    story.append(Spacer(1, 14))

    # ── Bottom two-column: Tech Stack | Security & Deployment ─────────────
    col_w2 = (W - 2 * margin - 0.2 * inch) / 2

    left2 = []
    left2 += make_section("Technology Stack", S)
    tech_rows = [
        ("Backend",        "Python 3.x · FastAPI · Azure AI Agent SDK (Magentic) · FastMCP"),
        ("Frontend",       "React 18 · TypeScript · Fluent UI v9 · Vite · Axios"),
        ("AI / LLM",       "Azure OpenAI Service (GPT-4 class) · Azure AI Foundry"),
        ("Data",           "Azure Cosmos DB (NoSQL)"),
        ("Infrastructure", "Azure Container Apps · Container Registry · Key Vault · Managed Identity"),
        ("IaC / Deploy",   "Bicep · Azure Developer CLI (azd) · GitHub Actions"),
        ("Testing",        "pytest · vitest · Dev Containers · GitHub Codespaces"),
        ("Extensibility",  "MCP (Model Context Protocol) — plug in any domain tool"),
    ]
    for label, detail in tech_rows:
        left2.append(Paragraph(
            f"<b>{label}:</b> <font color='#555555'>{detail}</font>",
            S["body_small"]
        ))
        left2.append(Spacer(1, 3))

    right2 = []
    right2 += make_section("Security & Compliance", S)
    sec_items = [
        "Azure Managed Identity — no passwords or secrets in code",
        "Azure Key Vault — all service credentials stored and rotated centrally",
        "Azure AD authentication — optional per-endpoint enforcement",
        "GitHub secret scanning recommended for all forks",
        "Optional WAF + VNet integration for Container Apps",
        "Microsoft Responsible AI transparency documentation included",
    ]
    for item in sec_items:
        right2.append(bullet_item(item, S))
        right2.append(Spacer(1, 2))

    right2.append(Spacer(1, 8))
    right2 += make_section("Deployment & Cost", S)
    right2.append(Paragraph(
        "Deployed via <b>azd up</b> (Azure Developer CLI ≥ 1.18) in a single command. "
        "Supported regions include East US, East US2, UK South, Sweden Central, Japan East. "
        "Cost is primarily <b>usage-based</b> (OpenAI tokens, Cosmos DB RUs, Container App compute) "
        "with a small fixed fee for Azure Container Registry. "
        "Resources are fully teardown-able with <b>azd down</b>.",
        S["body_small"]
    ))
    right2.append(Spacer(1, 8))
    right2 += make_section("Getting Started", S)
    right2.append(Paragraph(
        "① Clone the repo &nbsp;&nbsp; ② Run <b>azd up</b> &nbsp;&nbsp; "
        "③ Open the web UI &nbsp;&nbsp; ④ Submit a task in plain language<br/>"
        "<br/>Supports: GitHub Codespaces, VS Code Dev Containers, local setup.",
        S["body_small"]
    ))

    bottom_col = Table([[left2, right2]], colWidths=[col_w2, col_w2])
    bottom_col.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
        ("LINEAFTER",    (0, 0), (0, -1),  0.5, HexColor("#c0d8ef")),
        ("RIGHTPADDING", (0, 0), (0, -1),  8),
        ("LEFTPADDING",  (1, 0), (1, -1),  8),
    ]))
    story.append(bottom_col)
    story.append(Spacer(1, 12))

    # ── Call-to-action banner ─────────────────────────────────────────────
    cta_data = [[
        Paragraph(
            "Open Source on GitHub &nbsp;·&nbsp; "
            "github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator",
            ParagraphStyle("cta", fontName="Helvetica-Bold", fontSize=8.5,
                           leading=13, textColor=WHITE, alignment=TA_CENTER)
        )
    ]]
    cta_table = Table(cta_data, colWidths=[W - 2 * margin])
    cta_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), ACCENT),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
    ]))
    story.append(cta_table)

    doc.build(story, onFirstPage=header_band, onLaterPages=header_band)
    print(f"PDF written to: {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
