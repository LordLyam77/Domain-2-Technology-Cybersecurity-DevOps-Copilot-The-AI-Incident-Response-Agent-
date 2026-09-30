"""
Generate a professional, high-impact PowerPoint pitch deck for DevOps Copilot.
Theme: Modern Dark Mode Observability (Datadog/Grafana aesthetic).
Aspect Ratio: 16:9 widescreen.
Includes comprehensive speaker notes for every single slide.
"""

import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Theme Colors
    BG_DARK = RGBColor(14, 17, 23)        # #0E1117
    BG_CARD = RGBColor(22, 27, 34)        # #161B22
    BORDER_CARD = RGBColor(48, 54, 61)    # #30363D
    TEXT_BRIGHT = RGBColor(240, 246, 252) # #F0F6FC
    TEXT_MUTED = RGBColor(139, 148, 158)  # #8B949E
    ACCENT_BLUE = RGBColor(88, 166, 255)  # #58A6FF
    COLOR_GREEN = RGBColor(63, 185, 80)   # #3FB950
    COLOR_RED = RGBColor(248, 81, 73)     # #F85149
    COLOR_AMBER = RGBColor(227, 179, 65)  # #E3B341

    def add_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_DARK
        bg.line.fill.background()
        return bg

    def add_header(slide, category, title):
        add_bg(slide)
        header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(1.1))
        tf = header_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        # Category Tracker
        p0 = tf.paragraphs[0]
        p0.text = category.upper()
        p0.font.size = Pt(11)
        p0.font.bold = True
        p0.font.color.rgb = ACCENT_BLUE
        
        # Slide Title
        p1 = tf.add_paragraph()
        p1.text = title
        p1.font.size = Pt(24)
        p1.font.bold = True
        p1.font.color.rgb = TEXT_BRIGHT
        p1.space_before = Pt(4)

    def add_card(slide, left, top, width, height, title, body_bullets, accent_color=None, border_color=BORDER_CARD):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = BG_CARD
        card.line.color.rgb = accent_color if accent_color else border_color
        card.line.width = Pt(1.5 if accent_color else 1)
        
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.25)
        tf.margin_right = Inches(0.25)
        tf.margin_top = Inches(0.22)
        tf.margin_bottom = Inches(0.2)
        
        if title:
            p_title = tf.paragraphs[0]
            p_title.text = title
            p_title.font.size = Pt(16)
            p_title.font.bold = True
            p_title.font.color.rgb = accent_color if accent_color else TEXT_BRIGHT
            p_title.space_after = Pt(10)
        
        first = not bool(title)
        for bullet in body_bullets:
            p = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            p.text = bullet
            p.font.size = Pt(12)
            p.font.color.rgb = TEXT_MUTED if not bullet.startswith("👉") and not bullet.startswith("💡") else TEXT_BRIGHT
            p.space_after = Pt(6)
            p.level = 0
        return card

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    add_bg(s1)
    
    # Title decorative accent box
    dec = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(11.733), Inches(4.0))
    dec.fill.solid()
    dec.fill.fore_color.rgb = BG_CARD
    dec.line.color.rgb = ACCENT_BLUE
    dec.line.width = Pt(1.5)
    
    tf = dec.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Inches(0.8)
    tf.margin_right = Inches(0.8)
    
    p0 = tf.paragraphs[0]
    p0.text = "🛡️ DEVOPS COPILOT"
    p0.font.size = Pt(36)
    p0.font.bold = True
    p0.font.color.rgb = TEXT_BRIGHT
    
    p1 = tf.add_paragraph()
    p1.text = "The Autonomous AI Incident Response & Observability Agent"
    p1.font.size = Pt(20)
    p1.font.bold = True
    p1.font.color.rgb = ACCENT_BLUE
    p1.space_before = Pt(8)
    p1.space_after = Pt(16)
    
    p2 = tf.add_paragraph()
    p2.text = "From 3:00 AM Alert to Verified Cloud Recovery in Under 15 Seconds"
    p2.font.size = Pt(14)
    p2.font.color.rgb = TEXT_MUTED
    
    p3 = tf.add_paragraph()
    p3.text = "Christ University  •  Department of Computer Science & Engineering"
    p3.font.size = Pt(12)
    p3.font.color.rgb = COLOR_GREEN
    p3.space_before = Pt(24)

    s1.notes_slide.notes_text_frame.text = (
        "Good morning esteemed judges and evaluators. Today, we are presenting DevOps Copilot: "
        "an autonomous AI incident response agent designed to solve one of the most stressful, "
        "expensive problems in the modern software industry: catastrophic production outages at 3:00 AM."
    )

    # =========================================================================
    # SLIDE 2: THE PROBLEM
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "Industry Context & Challenge", "The $300,000/Hour Production Outage Nightmare")
    
    add_card(s2, Inches(0.8), Inches(1.8), Inches(3.6), Inches(4.8), 
             "🚨 The 3:00 AM Fire drill", [
                 "When payment or cloud services crash in production, alerts wake up on-call Site Reliability Engineers (SREs).",
                 "Every minute of downtime damages customer trust and costs enterprise companies up to $5,000+ per minute ($300k/hr).",
                 "Engineers face extreme cognitive fatigue and pressure while debugging in the dead of night."
             ], COLOR_RED)
             
    add_card(s2, Inches(4.85), Inches(1.8), Inches(3.6), Inches(4.8), 
             "🧩 Fragmented Tooling", [
                 "To diagnose an issue, engineers must manually correlate data across 4+ disconnected systems:",
                 "• Datadog / Grafana (Metrics)",
                 "• Splunk / CloudWatch (Server Logs)",
                 "• GitHub / ArgoCD (Deploy History)",
                 "• Jira / Confluence (Past Incidents)",
                 "Manual triage routinely takes 45 to 60 minutes just to find the culprit commit."
             ], COLOR_AMBER)

    add_card(s2, Inches(8.9), Inches(1.8), Inches(3.6), Inches(4.8), 
             "⚠️ The AI Safety Paradox", [
                 "Most AI chatbots are passive text-generators that hallucinate when given telemetry.",
                 "Conversely, fully autonomous 'rogue' agents that execute shell scripts blindly are far too dangerous for production.",
                 "👉 The industry needs an agent that autonomously investigates, but keeps humans in control of high-risk remediations."
             ], ACCENT_BLUE)

    s2.notes_slide.notes_text_frame.text = (
        "In production cloud environments, outages cost thousands of dollars per minute. Today, diagnosing an outage requires an SRE "
        "to manually cross-examine 4 separate tools: metrics, logs, git commits, and past postmortems. This manual triage takes 45-60 minutes. "
        "Generic LLMs hallucinate, and unconstrained autonomous scripts are too dangerous. We bridge this exact gap."
    )

    # =========================================================================
    # SLIDE 3: THE SOLUTION
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "Product Overview", "DevOps Copilot: Intelligent, Grounded, Safe Triage")

    add_card(s3, Inches(0.8), Inches(1.8), Inches(5.6), Inches(2.3),
             "⚡ 15-Second Multi-Tool Triage", [
                 "An autonomous ReAct agent powered by Google Gemini that calls real diagnostic functions (logs, deploys, status, postmortems) without guessing."
             ], ACCENT_BLUE)

    add_card(s3, Inches(6.8), Inches(1.8), Inches(5.6), Inches(2.3),
             "🛡️ Human-in-the-Loop Safety Gate", [
                 "Deterministic risk engine classifies remediations: HIGH-risk actions (rollbacks) are strictly locked behind human approval before touching production."
             ], COLOR_GREEN)

    add_card(s3, Inches(0.8), Inches(4.4), Inches(5.6), Inches(2.3),
             "🔄 Closed-Loop Health Verification", [
                 "Never assumes success. Post-remediation health telemetry validates that error rates actually dropped. If a fix fails, it re-triages automatically."
             ], COLOR_AMBER)

    add_card(s3, Inches(6.8), Inches(4.4), Inches(5.6), Inches(2.3),
             "📝 Automated Incident Postmortems", [
                 "Instantly synthesizes formal Markdown incident reports with root cause, failure timeline, key evidence, and preventative engineering recommendations."
             ], COLOR_GREEN)

    s3.notes_slide.notes_text_frame.text = (
        "DevOps Copilot is an autonomous incident response agent built on three core pillars: "
        "First, 15-second autonomous triage using tool calling. Second, strict human-in-the-loop safety gates so no high-risk action runs unapproved. "
        "Third, closed-loop verification where the agent tests whether the service actually recovered, rather than naively assuming success."
    )

    # =========================================================================
    # SLIDE 4: ARCHITECTURE
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "System Design", "Robust 3-Tier Layered Architecture")

    add_card(s4, Inches(0.8), Inches(1.8), Inches(3.6), Inches(4.8),
             "Layer 1: Observability UI\n(app.py)", [
                 "• Streamlit enterprise dark dashboard inspired by Datadog & Grafana.",
                 "• Real-time incident lifecycle stepper: Alert ➔ Investigate ➔ Root Cause ➔ Gate ➔ Verify.",
                 "• Interactive scenario selector tabs and offline safety-net demo switch.",
                 "• Dynamic metrics delta cards and color-tagged log stream viewer."
             ], ACCENT_BLUE)

    add_card(s4, Inches(4.85), Inches(1.8), Inches(3.6), Inches(4.8),
             "Layer 2: Intelligence Core\n(agent/)", [
                 "• coordinator.py: Multi-turn ReAct reasoning loop using tool calling.",
                 "• planner.py: Deterministic risk classification (HIGH vs LOW) & fallback generator.",
                 "• prompts.py: Strict zero-hallucination evidence citations & JSON schema.",
                 "• reporter.py: Automated incident postmortem report generation.",
                 "• gemini_gateway.py: 429 quota resilience & offline cache safety net."
             ], COLOR_AMBER)

    add_card(s4, Inches(8.9), Inches(1.8), Inches(3.6), Inches(4.8),
             "Layer 3: Cloud Simulation\n(simulation/)", [
                 "• environment.py: In-memory cloud telemetry engine simulating real microservices.",
                 "• Realistic telemetry datasets with benign log noise and timestamps.",
                 "• Dynamic state mutations: executing a rollback or restart updates real error rates and replica status."
             ], COLOR_GREEN)

    s4.notes_slide.notes_text_frame.text = (
        "Our architecture cleanly separates presentation, intelligence, and environment. "
        "The frontend is built in Streamlit styled after Datadog. The intelligence core handles the ReAct loop, risk evaluation, and postmortem reporting. "
        "The environment layer is a stateful simulation engine that behaves like a real cloud cluster, updating telemetry dynamically as actions are executed."
    )

    # =========================================================================
    # SLIDE 5: AUTONOMOUS REACT LOOP
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "Agent Intelligence", "The Autonomous ReAct Tool-Calling Loop")

    add_card(s5, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8),
             "🧠 How the Agent Reasons & Acts", [
                 "1. Alert Received: Ingests alert trigger on 'payment-service'.",
                 "2. Tool 1: get_status() -> Discovers error rate 43.5%, status CRITICAL.",
                 "3. Tool 2: get_deploys() -> Uncovers release v2.4.0 deployed 12m ago with commit: 'Reduced DB pool size to 10'.",
                 "4. Tool 3: get_logs() -> Isolates ConnectionPoolExhaustedException and 500 error spikes.",
                 "5. Tool 4: get_past_incidents() -> Matches historical postmortem INC-892 for pool reduction.",
                 "6. Structured JSON Synthesis -> Produces root cause diagnosis with confidence score and evidence list."
             ], ACCENT_BLUE)

    add_card(s5, Inches(6.8), Inches(1.8), Inches(5.6), Inches(4.8),
             "🔒 Why Tool Grounding Prevents Hallucination", [
                 "• Standard Chatbots hallucinate nonexistent error codes and phantom servers.",
                 "• DevOps Copilot enforces strict grounding: the prompt commands the LLM to cite only tool observation values.",
                 "• Telemetry is injected as verified role='tool' response parts in the multi-turn context.",
                 "• Structured JSON mode guarantees valid schema parsing, backed by automated retry handlers.",
                 "👉 The agent cannot invent facts because its reasoning is anchored in actual telemetry data."
             ], COLOR_GREEN)

    s5.notes_slide.notes_text_frame.text = (
        "Here is the heart of the agent: the ReAct loop. Unlike simple chatbots that guess answers, DevOps Copilot executes function calling. "
        "It checks service vital signs, queries git deployment records, filters server error logs, and compares against past postmortems. "
        "Because the LLM only receives verified tool results, hallucinations are dramatically reduced."
    )

    # =========================================================================
    # SLIDE 6: SAFETY GATE & RISK CLASSIFIER
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "Safety & Control", "Human-in-the-Loop Risk Governance")

    add_card(s6, Inches(0.8), Inches(1.8), Inches(3.6), Inches(4.8),
             "🚨 High Risk: Human Gate", [
                 "• Action: rollback",
                 "• Why: Code rollbacks alter production binaries and can cause schema mismatches.",
                 "• Governance: Strictly halts at the Approval Gate.",
                 "• UI: Glowing red card with full impact summary and one-click 'Approve Fix' or 'Reject Proposal' buttons."
             ], COLOR_RED)

    add_card(s6, Inches(4.85), Inches(1.8), Inches(3.6), Inches(4.8),
             "⚠️ Medium Risk: Partner Action", [
                 "• Action: escalate_and_enable_fallback",
                 "• Why: Switching payment gateways or cloud zones affects partner SLAs and transaction fees.",
                 "• Governance: Operator review required before routing traffic.",
                 "• UI: Amber approval card detailing vendor status and fallback failover provider."
             ], COLOR_AMBER)

    add_card(s6, Inches(8.9), Inches(1.8), Inches(3.6), Inches(4.8),
             "🟢 Low Risk: Safe Operations", [
                 "• Action: restart_service / flush cache",
                 "• Why: Pod restarts clear memory leaks and release hung connection pools safely.",
                 "• Governance: Low-blast radius; can auto-execute or provide quick 1-click confirmation.",
                 "• UI: Green confirmation card with instant recovery verification."
             ], COLOR_GREEN)

    s6.notes_slide.notes_text_frame.text = (
        "Safety is where our project truly shines. We built a deterministic Risk Classifier in planner.py. "
        "Destructive actions like rolling back code or rerouting third-party payment gateways are marked HIGH or MEDIUM risk. "
        "The system literally cannot execute them until a human operator clicks 'Approve Fix'. The AI advises; the human decides."
    )

    # =========================================================================
    # SLIDE 7: THE 5 REAL-WORLD SCENARIOS
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "Comprehensive Evaluation", "The 5 Production Incident Scenarios")

    add_card(s7, Inches(0.8), Inches(1.8), Inches(2.2), Inches(4.8),
             "1. Bad Deploy", [
                 "Spike to 43.5% errors right after v2.4.0 deploy.",
                 "Root Cause: Dave reduced DB pool to 10.",
                 "Fix: Rollback to v2.3.9.",
                 "Outcome: Recovers to 0.2% errors."
             ], ACCENT_BLUE)

    add_card(s7, Inches(3.2), Inches(1.8), Inches(2.2), Inches(4.8),
             "2. Fix Fails", [
                 "Deploy occurred, but rollback fails to fix it!",
                 "Catch: Error rate stays at 52.4%.",
                 "Re-triage: PostgreSQL pool saturation (500/500).",
                 "Fix: Database restart."
             ], COLOR_RED)

    add_card(s7, Inches(5.6), Inches(1.8), Inches(2.2), Inches(4.8),
             "3. Memory Leak", [
                 "No recent deploy! Uptime: 5 full days.",
                 "Status: JVM Heap at 96.1% (OOM).",
                 "Past Match: INC-402 ledger worker leak.",
                 "Fix: Safe pod restart."
             ], COLOR_GREEN)

    add_card(s7, Inches(8.0), Inches(1.8), Inches(2.2), Inches(4.8),
             "4. Vendor Outage", [
                 "Deploy v2.4.1 was harmless text copy.",
                 "Telemetry: Upstream PayGate 504 timeouts.",
                 "Intelligence: Refuses rollback; reroutes to StripeSecondary."
             ], COLOR_AMBER)

    add_card(s7, Inches(10.4), Inches(1.8), Inches(2.2), Inches(4.8),
             "5. Low Confidence", [
                 "Conflicting signals: Deploy vs replica lag.",
                 "Score: 52% (<60% threshold).",
                 "Honest AI: 3 operator choices (Failover, Rollback, Investigate)."
             ], ACCENT_BLUE)

    s7.notes_slide.notes_text_frame.text = (
        "We tested DevOps Copilot against 5 distinct real-world failure patterns. "
        "From classic bad code deployments, to failed fixes and secondary investigations, to insidious 5-day memory leaks, "
        "upstream third-party vendor outages, and ambiguous telemetry where the AI transparently presents 3 choices to the human."
    )

    # =========================================================================
    # SLIDE 8: CLOSED-LOOP VERIFICATION & POSTMORTEMS
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "Verification & Governance", "Closed-Loop Verification & Automated Postmortems")

    add_card(s8, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8),
             "🔄 The Verification Loop (Never Assume Success)", [
                 "• In real DevOps, applying a patch doesn't guarantee the service is cured.",
                 "• Upon executing any action, the app transitions to the 'verifying' stage.",
                 "• It pulls fresh telemetry from get_status():",
                 "  - Compares pre-fix vs. post-fix error rates and latencies.",
                 "  - If healthy (e.g. 0.2%), confirms recovery and transitions to 'done'.",
                 "  - If still critical (Scenario 2), flags 'VERIFICATION FAILED' and triggers secondary triage.",
                 "👉 Closed-loop verification ensures zero unmonitored failures."
             ], COLOR_GREEN)

    add_card(s8, Inches(6.8), Inches(1.8), Inches(5.6), Inches(4.8),
             "📝 Automated Incident Postmortem (SRE Standard)", [
                 "• Writing postmortems manually takes engineers hours of administrative work.",
                 "• reporter.py automatically synthesizes a complete Markdown report:",
                 "  1. Executive Summary & Impact Window",
                 "  2. Detailed Incident Timeline",
                 "  3. Root Cause Analysis & Supporting Evidence",
                 "  4. Remediations Executed & Failed Attempts",
                 "  5. Action Items & Preventative Engineering",
                 "• Includes a 1-click 'Download Report (.md)' button for team wikis."
             ], ACCENT_BLUE)

    s8.notes_slide.notes_text_frame.text = (
        "Two features set this project apart from academic prototypes. First, closed-loop verification: we don't assume a fix worked, "
        "we actively measure before-and-after telemetry. Second, automated postmortem generation. As soon as the incident resolves, "
        "our reporter synthesizes an executive-ready postmortem report complete with timeline, root cause, and action items."
    )

    # =========================================================================
    # SLIDE 9: DEMO SAFETY NET & PRODUCTION RESILIENCE
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "Engineering Excellence", "Enterprise Resilience & The Demo Safety Net")

    add_card(s9, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8),
             "🛡️ Offline Demo Mode & Gateway Architecture", [
                 "• Single point of contact: gemini_gateway.py wraps all Gemini API calls.",
                 "• Multi-model cascading fallback: if primary hits 429 quota, cascades across flash-lite models automatically.",
                 "• 100% Offline Safety Net: In venue environments with spotty Wi-Fi, the 'Offline Demo Mode' toggle runs verified cached traces with zero latency.",
                 "• Automatic Disconnect Fallback: Even if demo mode is off, network timeouts gracefully fall back to cache without crashing."
             ], COLOR_AMBER)

    add_card(s9, Inches(6.8), Inches(1.8), Inches(5.6), Inches(4.8),
             "🧪 100% Automated Test Coverage", [
                 "• test_simulation.py: 11 comprehensive unit tests validating state mutations, memory flushes, replica failovers, and timeline charts.",
                 "• test_app.py: 7 end-to-end Streamlit AppTests verifying UI button clicks, approval gates, rejections, fallback plans, and offline recovery.",
                 "• Continuous verification ensures every scenario and edge case is rock solid.",
                 "👉 Verified production-grade code, not a fragile hackathon demo."
             ], COLOR_GREEN)

    s9.notes_slide.notes_text_frame.text = (
        "We engineered this project with true enterprise resilience. Through gemini_gateway.py, all API calls feature cascading fallback. "
        "If a venue has spotty Wi-Fi, our Offline Demo Mode allows 100% local presentation with zero latency. "
        "Furthermore, our automated test suites (test_app.py and test_simulation.py) pass with 100% green coverage."
    )

    # =========================================================================
    # SLIDE 10: CONCLUSION & FUTURE SCOPE
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "Summary & Roadmap", "The Future of Autonomous Site Reliability Engineering")

    add_card(s10, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8),
             "🎯 Key Accomplishments", [
                 "• Reduced incident triage time from 45 minutes to < 15 seconds.",
                 "• Multi-tool autonomous ReAct loop eliminating manual correlation.",
                 "• Deterministic human-in-the-loop safety gating for all high-risk actions.",
                 "• Closed-loop verification catching failed hypotheses in real time.",
                 "• 5 diverse real-world failure scenarios fully simulated and tested."
             ], COLOR_GREEN)

    add_card(s10, Inches(6.8), Inches(1.8), Inches(5.6), Inches(4.8),
             "🚀 Production Roadmap", [
                 "• Live Webhooks: Direct ingestion from Prometheus Alertmanager & PagerDuty.",
                 "• Kubernetes Operator: Native k8s controller executing pod rollouts and horizontal pod autoscaling.",
                 "• Enterprise RBAC & Audit: Cryptographic audit log of AI recommendations and human approvals for SOC2 compliance.",
                 "• Multi-Cloud Topology: Cross-region dependency graphs across AWS, GCP, and Azure."
             ], ACCENT_BLUE)

    s10.notes_slide.notes_text_frame.text = (
        "To conclude: DevOps Copilot transforms incident response from a chaotic 3:00 AM fire drill into a calm, 15-second guided workflow. "
        "It empowers on-call engineers with AI speed, while protecting production with human safety gates. "
        "Thank you, and we welcome your questions!"
    )

    output_path = "DevOps_Copilot_Presentation.pptx"
    prs.save(output_path)
    print(f"Presentation saved successfully to: {output_path}")

if __name__ == "__main__":
    create_deck()
