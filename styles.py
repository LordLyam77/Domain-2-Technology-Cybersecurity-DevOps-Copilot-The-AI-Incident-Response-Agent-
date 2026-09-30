"""
DevOps Copilot: Dark Theme & Observability Design System (CSS).

Provides styling inspired by modern incident management tools (Datadog, Grafana, PagerDuty):
- Dark palette (#0E1117 canvas, #161B22 card surfaces, #30363D borders)
- Inter for UI text and JetBrains Mono for logs, metrics, and code
- Prominent approval card with risk-colored borders
- Horizontal incident lifecycle stepper
- Compact log stream viewer with log-level color tagging
"""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

/* ==========================================================================
   1. GLOBAL RESETS & TYPOGRAPHY
   ========================================================================== */
:root {
    --bg-canvas: #0E1117;
    --bg-surface: #161B22;
    --bg-surface-elevated: #21262D;
    --bg-surface-hover: #292E36;
    --border-subtle: #30363D;
    --border-muted: #21262D;
    --text-primary: #C9D1D9;
    --text-secondary: #8B949E;
    --text-bright: #F0F6FC;
    --accent-blue: #58A6FF;
    --accent-blue-tint: rgba(88, 166, 255, 0.12);
    --status-critical: #F85149;
    --status-critical-bg: rgba(248, 81, 73, 0.12);
    --status-critical-border: rgba(248, 81, 73, 0.4);
    --status-warning: #D29922;
    --status-warning-bg: rgba(210, 153, 34, 0.12);
    --status-warning-border: rgba(210, 153, 34, 0.4);
    --status-healthy: #2EA043;
    --status-healthy-bg: rgba(46, 160, 67, 0.12);
    --status-healthy-border: rgba(46, 160, 67, 0.4);
}

html, body, .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    color: var(--text-primary);
}

/* Fix Streamlit Material Symbols Icon Font Display (Chevrons & Sidebar toggle) */
[data-testid="stIconMaterial"],
span[data-testid="stIconMaterial"],
.material-symbols-rounded,
.material-symbols-outlined,
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
[data-testid="stExpander"] summary [data-testid="stIconMaterial"] {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important;
    font-weight: normal !important;
    font-style: normal !important;
    font-size: 1.15rem !important;
    line-height: 1 !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    display: inline-block !important;
    white-space: nowrap !important;
    word-wrap: normal !important;
    direction: ltr !important;
    vertical-align: middle !important;
    -webkit-font-feature-settings: 'liga' 1 !important;
    font-feature-settings: 'liga' 1 !important;
    -webkit-font-smoothing: antialiased !important;
}

/* Ensure expander summary flex layout separates the chevron icon from the text */
[data-testid="stExpander"] summary {
    display: flex !important;
    align-items: center !important;
    gap: 0.6rem !important;
}

[data-testid="stExpander"] summary span:first-child {
    display: inline-flex !important;
    align-items: center !important;
    flex-shrink: 0 !important;
}

[data-testid="stExpander"] summary div[data-testid="stMarkdownContainer"] {
    flex-grow: 1 !important;
}

[data-testid="stSidebarCollapseButton"] button {
    overflow: hidden !important;
}

code, pre, .font-mono, [data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', SFMono-Regular, Consolas, monospace !important;
}

/* Three Standard Heading Sizes */
h1, .text-xl {
    font-size: 1.25rem !important;
    font-weight: 600 !important;
    color: var(--text-bright) !important;
    margin: 0 0 0.5rem 0 !important;
    letter-spacing: -0.01em;
}

h2, .text-lg {
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    color: var(--text-bright) !important;
    margin: 0.5rem 0 0.4rem 0 !important;
}

h3, .text-md {
    font-size: 0.92rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    margin: 0.4rem 0 0.3rem 0 !important;
}

p, span, label, div {
    font-size: 0.85rem;
    line-height: 1.45;
}

/* ==========================================================================
   2. APP HEADER & STATUS PILL
   ========================================================================== */
.header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    margin-bottom: 0.85rem;
}

.header-title-container {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.header-icon {
    font-size: 1.15rem;
    margin-right: 0.2rem;
}

.header-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-bright);
    letter-spacing: -0.01em;
}

.header-divider {
    color: var(--border-subtle);
    font-size: 1rem;
}

.header-subtitle {
    font-size: 0.82rem;
    color: var(--text-secondary);
    font-weight: 400;
}

.header-pill-container {
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

.header-pill {
    padding: 3px 9px;
    border-radius: 12px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}

.pill-live {
    background: var(--status-healthy-bg);
    color: #3FB950;
    border: 1px solid var(--status-healthy-border);
}

.pill-demo {
    background: var(--status-warning-bg);
    color: #E3B341;
    border: 1px solid var(--status-warning-border);
}

.header-model-pill {
    padding: 3px 9px;
    border-radius: 12px;
    font-size: 0.72rem;
    font-weight: 500;
    color: var(--text-secondary);
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-subtle);
    font-family: 'JetBrains Mono', monospace;
}

/* Pulse Animations & Status Indicator Dots */
@keyframes pulse-dot {
    0% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(248, 81, 73, 0.7); }
    70% { transform: scale(1); opacity: 1; box-shadow: 0 0 0 6px rgba(248, 81, 73, 0); }
    100% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(248, 81, 73, 0); }
}

@keyframes pulse-green {
    0% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(46, 160, 67, 0.7); }
    70% { transform: scale(1); opacity: 1; box-shadow: 0 0 0 6px rgba(46, 160, 67, 0); }
    100% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(46, 160, 67, 0); }
}

@keyframes pulse-amber {
    0% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(210, 153, 34, 0.7); }
    70% { transform: scale(1); opacity: 1; box-shadow: 0 0 0 6px rgba(210, 153, 34, 0); }
    100% { transform: scale(0.95); opacity: 0.8; box-shadow: 0 0 0 0 rgba(210, 153, 34, 0); }
}

.status-dot-critical {
    display: inline-block;
    width: 8px;
    height: 8px;
    background-color: var(--status-critical);
    border-radius: 50%;
    animation: pulse-dot 2s infinite;
    margin-right: 6px;
    vertical-align: middle;
}

.status-dot-healthy {
    display: inline-block;
    width: 8px;
    height: 8px;
    background-color: var(--status-healthy);
    border-radius: 50%;
    animation: pulse-green 2s infinite;
    margin-right: 6px;
    vertical-align: middle;
}

.status-dot-warning {
    display: inline-block;
    width: 8px;
    height: 8px;
    background-color: var(--status-warning);
    border-radius: 50%;
    animation: pulse-amber 2s infinite;
    margin-right: 6px;
    vertical-align: middle;
}

.frontend-badge {
    padding: 3px 8px;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 500;
    color: var(--accent-blue);
    background: var(--accent-blue-tint);
    border: 1px solid rgba(88, 166, 255, 0.3);
    display: inline-flex;
    align-items: center;
    gap: 4px;
    transition: all 0.2s ease;
}

.frontend-badge:hover {
    border-color: var(--accent-blue);
    box-shadow: 0 0 8px rgba(88, 166, 255, 0.25);
}

/* ==========================================================================
   3. HORIZONTAL PROGRESS STEPPER
   ========================================================================== */
.stepper-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.6rem 0.85rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    margin-bottom: 1rem;
    overflow-x: auto;
}

.step-item {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--text-secondary);
    white-space: nowrap;
}

.step-item.active {
    color: var(--accent-blue);
    font-weight: 600;
}

.step-item.completed {
    color: var(--text-primary);
}

.step-bubble {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
    font-weight: 600;
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-subtle);
    color: var(--text-secondary);
}

.step-item.active .step-bubble {
    background: var(--accent-blue);
    border-color: var(--accent-blue);
    color: #0E1117;
    box-shadow: 0 0 8px rgba(88, 166, 255, 0.4);
}

.step-item.completed .step-bubble {
    background: var(--status-healthy);
    border-color: var(--status-healthy);
    color: #FFFFFF;
}

.step-connector {
    flex: 1;
    height: 1px;
    background: var(--border-subtle);
    margin: 0 0.5rem;
    min-width: 16px;
}

.step-connector.completed {
    background: var(--status-healthy);
}

/* ==========================================================================
   4. CARDS & PANELS
   ========================================================================== */
.obs-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 1rem 1.15rem;
    margin-bottom: 0.85rem;
}

.obs-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.65rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid var(--border-muted);
}

.obs-card-title {
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text-bright);
    letter-spacing: -0.01em;
}

/* Compact Alert Banner */
.alert-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-left: 4px solid var(--status-critical);
    border-radius: 6px;
    margin-bottom: 0.85rem;
}

.alert-banner-title {
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--status-critical);
}

.alert-banner-desc {
    font-size: 0.82rem;
    color: var(--text-primary);
    margin-top: 2px;
}

.alert-banner-meta {
    font-size: 0.75rem;
    color: var(--text-secondary);
    font-family: 'JetBrains Mono', monospace;
    text-align: right;
    white-space: nowrap;
}

/* Empty State Card */
.empty-state-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 2.5rem 1.5rem;
    text-align: center;
    margin: 1.5rem 0;
}

.empty-state-pill {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    background: var(--status-healthy-bg);
    color: #3FB950;
    border: 1px solid var(--status-healthy-border);
    margin-bottom: 0.8rem;
}

.empty-state-title {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-bright);
    margin-bottom: 0.4rem;
}

.empty-state-subtitle {
    font-size: 0.85rem;
    color: var(--text-secondary);
    max-width: 480px;
    margin: 0 auto 1.5rem auto;
}

/* Root Cause Card */
.root-cause-header {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-bright);
    margin-bottom: 0.5rem;
}

.evidence-list {
    margin: 0.4rem 0;
    padding-left: 1.2rem;
    color: var(--text-primary);
}

.evidence-item {
    font-size: 0.82rem;
    margin-bottom: 0.25rem;
}

.reasoning-text {
    font-size: 0.8rem;
    color: var(--text-secondary);
    line-height: 1.45;
    margin-top: 0.4rem;
}

/* Amber Callout Box */
.amber-callout {
    background: var(--status-warning-bg);
    border: 1px solid var(--status-warning-border);
    border-left: 4px solid var(--status-warning);
    border-radius: 6px;
    padding: 0.75rem 0.9rem;
    margin: 0.7rem 0;
    color: #E3B341;
    font-size: 0.82rem;
}

/* ==========================================================================
   5. APPROVAL CARD (MOST PROMINENT ELEMENT)
   ========================================================================== */
.approval-card-high {
    background: #1C1517;
    border: 2px solid var(--status-critical);
    border-radius: 8px;
    padding: 1.15rem 1.25rem;
    margin: 1rem 0;
    box-shadow: 0 0 16px rgba(248, 81, 73, 0.12);
}

.approval-card-medium {
    background: #1B1812;
    border: 2px solid var(--status-warning);
    border-radius: 8px;
    padding: 1.15rem 1.25rem;
    margin: 1rem 0;
    box-shadow: 0 0 16px rgba(210, 153, 34, 0.12);
}

.approval-card-low {
    background: #111A14;
    border: 2px solid var(--status-healthy);
    border-radius: 8px;
    padding: 1.15rem 1.25rem;
    margin: 1rem 0;
    box-shadow: 0 0 16px rgba(46, 160, 67, 0.12);
}

.approval-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text-bright);
    margin-bottom: 0.2rem;
}

.approval-action-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    font-family: 'JetBrains Mono', monospace;
    text-transform: uppercase;
}

.badge-risk-high {
    background: var(--status-critical-bg);
    color: #FF7B72;
    border: 1px solid var(--status-critical-border);
}

.badge-risk-medium {
    background: var(--status-warning-bg);
    color: #F2CC60;
    border: 1px solid var(--status-warning-border);
}

.badge-risk-low {
    background: var(--status-healthy-bg);
    color: #56D364;
    border: 1px solid var(--status-healthy-border);
}

/* ==========================================================================
   6. LOG VIEWER (DATADOG / GRAFANA STYLE)
   ========================================================================== */
.log-stream-container {
    background: #0D1117;
    border: 1px solid var(--border-subtle);
    border-radius: 6px;
    padding: 0.65rem 0.8rem;
    max-height: 290px;
    overflow-y: auto;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.73rem;
    line-height: 1.5;
}

.log-stream-line {
    display: flex;
    gap: 0.5rem;
    padding: 1px 0;
    white-space: pre-wrap;
    word-break: break-all;
}

.log-stream-line.highlight {
    background: rgba(248, 81, 73, 0.08);
    border-left: 2px solid var(--status-critical);
    padding-left: 4px;
}

.log-ts {
    color: #6E7681;
    flex-shrink: 0;
}

.log-level-error {
    color: #FF7B72;
    font-weight: 600;
    flex-shrink: 0;
}

.log-level-warn {
    color: #F2CC60;
    font-weight: 600;
    flex-shrink: 0;
}

.log-level-info {
    color: #8B949E;
    flex-shrink: 0;
}

.log-level-fatal {
    color: #FF7B72;
    font-weight: 700;
    background: rgba(248, 81, 73, 0.2);
    padding: 0 4px;
    border-radius: 2px;
    flex-shrink: 0;
}

.log-msg {
    color: var(--text-primary);
}

/* ==========================================================================
   7. INVESTIGATION FEED (STEP ROWS)
   ========================================================================== */
.investigation-step-row {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    padding: 0.35rem 0;
    border-bottom: 1px solid var(--border-muted);
    font-size: 0.8rem;
}

.investigation-step-row:last-child {
    border-bottom: none;
}

.step-icon {
    font-size: 0.8rem;
}

.step-tool {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    color: var(--accent-blue);
    background: var(--accent-blue-tint);
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 0.72rem;
}

.step-args {
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-secondary);
    font-size: 0.72rem;
}

.step-result {
    color: var(--text-primary);
    font-size: 0.78rem;
}

/* ==========================================================================
   8. STREAMLIT WIDGET OVERRIDES
   ========================================================================== */
/* Metrics */
[data-testid="stMetric"] {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 6px;
    padding: 0.65rem 0.85rem !important;
}

[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
    color: var(--text-secondary) !important;
}

[data-testid="stMetricValue"] {
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    color: var(--text-bright) !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.75rem !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* Buttons */
[data-testid="baseButton-secondary"] {
    background: var(--bg-surface-elevated) !important;
    border: 1px solid var(--border-subtle) !important;
    color: var(--text-primary) !important;
    border-radius: 6px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.35rem 0.85rem !important;
    transition: all 0.15s ease !important;
}

[data-testid="baseButton-secondary"]:hover {
    background: var(--bg-surface-hover) !important;
    border-color: var(--text-secondary) !important;
    color: var(--text-bright) !important;
}

[data-testid="baseButton-primary"] {
    background: #238636 !important;
    border: 1px solid rgba(240, 246, 252, 0.1) !important;
    color: #FFFFFF !important;
    border-radius: 6px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    padding: 0.35rem 0.85rem !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2) !important;
    transition: all 0.15s ease !important;
}

[data-testid="baseButton-primary"]:hover {
    background: #2EA043 !important;
    border-color: rgba(240, 246, 252, 0.2) !important;
}

/* Sidebar Styling & Scenario Tabs */
[data-testid="stSidebar"] {
    background: #0D1117 !important;
    border-right: 1px solid var(--border-subtle) !important;
}

.sidebar-section-title {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-secondary);
    margin: 1.1rem 0 0.4rem 0;
}

/* Modern Observability Scenario Tabs */
[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stRadioGroup"] {
    display: flex !important;
    flex-direction: column !important;
    gap: 0.35rem !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stRadioGroup"] > div {
    margin-bottom: 0 !important;
}

[data-testid="stSidebar"] [data-testid="stRadioOption"] {
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    border-left: 3px solid var(--border-subtle) !important;
    border-radius: 6px !important;
    padding: 0.5rem 0.7rem !important;
    margin: 0 !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
}

[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {
    background: var(--bg-surface-elevated) !important;
    border-color: var(--text-secondary) !important;
    border-left-color: var(--accent-blue) !important;
}

/* Selected Scenario Card Tab */
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"],
[data-testid="stSidebar"] div[data-selected="true"] [data-testid="stRadioOption"] {
    background: rgba(88, 166, 255, 0.08) !important;
    border: 1px solid var(--accent-blue) !important;
    border-left: 3px solid var(--accent-blue) !important;
    box-shadow: 0 0 10px rgba(88, 166, 255, 0.12) !important;
}

/* Hide default radio circle for clean card appearance */
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child {
    display: none !important;
}

/* Scenario Card Text Styling */
[data-testid="stSidebar"] [data-testid="stRadioOption"] [data-testid="stMarkdownContainer"] p {
    font-size: 0.79rem !important;
    font-weight: 500 !important;
    line-height: 1.35 !important;
    color: var(--text-primary) !important;
    margin: 0 !important;
}

[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] div[data-selected="true"] [data-testid="stRadioOption"] [data-testid="stMarkdownContainer"] p {
    color: var(--text-bright) !important;
    font-weight: 600 !important;
}

/* Expanders */
[data-testid="stExpander"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 6px !important;
    margin-bottom: 0.65rem !important;
}

[data-testid="stExpander"] summary {
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: var(--text-primary) !important;
}

/* Custom Scrollbars */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: var(--bg-canvas);
}
::-webkit-scrollbar-thumb {
    background: var(--border-subtle);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: var(--text-secondary);
}
</style>
"""
