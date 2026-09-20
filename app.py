import os, json
from io import BytesIO
import pandas as pd
import streamlit as st

st.set_page_config(page_title="AI Audit Risk Copilot", page_icon="🔎", layout="wide")

st.title("🔎 AI Audit Risk Copilot")
st.caption("Synthetic-data proof of concept • relationship-driven analytics • human review")

REQUIRED = ["Account", "Type", "FY25", "FY26"]


def analyze(df):
    df = df.copy()
    for c in ["FY25", "FY26"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["Absolute change"] = df["FY26"] - df["FY25"]
    df["% change"] = df.apply(
        lambda r: None if r["FY25"] == 0 else r["Absolute change"] / abs(r["FY25"]), axis=1
    )

    def val(name, year="FY26"):
        s = df.loc[df["Account"].astype(str).str.lower().eq(name.lower()), year]
        return float(s.iloc[0]) if len(s) else 0

    findings = []

    def add(priority, title, why, assertions, evidence, benign):
        findings.append({
            "priority": priority,
            "title": title,
            "why": why,
            "assertions": assertions,
            "evidence": evidence,
            "benign": benign,
        })

    revenue25, revenue26 = val("Revenue", "FY25"), val("Revenue")
    ar25, ar26 = val("Trade receivables", "FY25"), val("Trade receivables")
    if revenue25 and ar25:
        rg = revenue26 / revenue25 - 1
        ag = ar26 / ar25 - 1
        dso25 = ar25 / revenue25 * 365
        dso26 = ar26 / revenue26 * 365
        if ag - rg > 0.15:
            add(
                "High", "Trade receivables vs revenue",
                f"Receivables increased {ag:.1%} while revenue increased {rg:.1%}. Approximate DSO moved from {dso25:.0f} to {dso26:.0f} days.",
                "Revenue: occurrence / cut-off; Receivables: existence / valuation / rights",
                "AR ageing; subsequent receipts; invoice dates; credit notes; customer terms; top-customer movements; sales cut-off testing.",
                "New customers, extended credit terms, acquisitions, year-end billing patterns or a change in customer mix.",
            )

    adv25, adv26 = val("Customer advances", "FY25"), val("Customer advances")
    if revenue25 and adv25 and adv26 < adv25 and revenue26 > revenue25:
        add(
            "High", "Customer advances vs revenue",
            f"Customer advances fell {((adv26 / adv25) - 1):.1%} while revenue increased {((revenue26 / revenue25) - 1):.1%}. The movement should be reconciled to contract performance and revenue recognition.",
            "Revenue: occurrence / cut-off; Advances: completeness / existence / classification",
            "Opening-to-closing advance roll-forward; contracts/POs; amounts released to revenue; closing advance listing; subsequent revenue recognition.",
            "Customer contracts may have progressed to performance completion, reducing advances as revenue is recognised.",
        )

    opex25, opex26 = val("Other operating expenses", "FY25"), val("Other operating expenses")
    if opex25 and (opex26 / opex25 - 1) > 0.50:
        add(
            "Medium", "Other operating expenses and components",
            f"Other operating expenses increased {((opex26 / opex25) - 1):.1%}. Component-level changes can reveal classification, cut-off, accrual or unusual-spend risks.",
            "Completeness / cut-off / classification / occurrence",
            "GL detail; vendor listing; invoices/contracts; month-wise trend; large journals; accrual support; capitalisation policy.",
            "Planned campaigns, one-off professional fees, repairs, warranty events or business expansion.",
        )

    ppe25, ppe26 = val("PPE", "FY25"), val("PPE")
    cw25, cw26 = val("CWIP", "FY25"), val("CWIP")
    dep25, dep26 = val("Depreciation", "FY25"), val("Depreciation")
    if (ppe25 + cw25) and ((ppe26 + cw26) / (ppe25 + cw25) - 1) > 0.20:
        dep_growth = (dep26 / dep25 - 1) if dep25 else 0
        add(
            "High", "PPE + CWIP vs depreciation",
            f"PPE plus CWIP increased by {((ppe26 + cw26) / (ppe25 + cw25) - 1):.1%}, while depreciation increased {dep_growth:.1%}. This warrants investigation of additions, capitalisation timing and assets available for use.",
            "PPE: existence / rights / valuation; Depreciation: accuracy / cut-off; CWIP: valuation / classification",
            "Fixed asset register; additions invoices; CWIP ageing; capitalisation dates; physical verification; depreciation recalculation; approvals.",
            "Large projects may still be under construction, or assets may have been acquired late in the year.",
        )

    sup25, sup26 = val("Advances to suppliers", "FY25"), val("Advances to suppliers")
    if sup25 and (sup26 / sup25 - 1) < -0.50:
        add(
            "Medium", "Supplier advances",
            f"Supplier advances fell {((sup26 / sup25) - 1):.1%}. A large reduction should be reconciled to settlement, refunds, inventory/PPE receipts or expense recognition.",
            "Existence / rights / classification / cut-off",
            "Supplier-wise roll-forward; settlement evidence; GRNs; invoices; refunds; ageing; subsequent receipts.",
            "Normal conversion of advances into goods/services or refunds from suppliers.",
        )

    acc25, acc26 = val("Accrued expenses", "FY25"), val("Accrued expenses")
    if acc25 and (acc26 / acc25 - 1) > 0.40:
        add(
            "Medium", "Accrued expenses",
            f"Accrued expenses increased {((acc26 / acc25) - 1):.1%}. This may indicate higher unbilled costs or year-end accrual activity.",
            "Completeness / cut-off / valuation",
            "Accrual schedules; subsequent invoices; post-year-end payments; vendor confirmations; management estimates.",
            "Business growth or timing of invoices can naturally increase closing accruals.",
        )

    return df, findings


def build_ai_prompt(findings):
    return """You are an audit analytics assistant, not the final auditor.\n\nFor each finding below, improve the reasoning without concluding that a misstatement exists. Return:\n1. Why the relationship matters\n2. Plausible benign explanations\n3. Relevant audit assertions\n4. Information/evidence to request\n5. One concise management question\n6. Suggested procedures\n\nKeep outputs reviewable and explicitly preserve human judgement. Do not invent facts.\n\nFINDINGS:\n""" + json.dumps(findings, indent=2)


def make_download_xlsx(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Analysis")
    buf.seek(0)
    return buf


uploaded = st.file_uploader("Upload a synthetic trial balance Excel file", type=["xlsx", "xls"])

if uploaded:
    df = pd.read_excel(uploaded, sheet_name="Trial Balance")
    st.success("Uploaded dataset loaded.")
else:
    df = pd.read_excel("sample_data.xlsx", sheet_name="Trial Balance")
    st.info("Demo mode: using the included synthetic FY25/FY26 dataset.")

missing = [c for c in REQUIRED if c not in df.columns]
if missing:
    st.error(f"Missing required columns: {missing}")
    st.stop()

analysis, findings = analyze(df)

c1, c2, c3 = st.columns(3)
c1.metric("Accounts analysed", len(analysis))
c2.metric("Relationship tests", "6")
c3.metric("Risk signals", len(findings))

st.divider()
st.subheader("1 · Risk signals")
st.caption("Signals are hypotheses for human review — not audit conclusions.")

if not findings:
    st.success("No rule-based signals were generated. Human review is still required.")
else:
    for i, f in enumerate(findings, 1):
        with st.expander(f"{i}. {f['priority']} — {f['title']}", expanded=(i == 1)):
            st.markdown("**Why it matters**")
            st.write(f["why"])
            st.markdown("**Potential assertions**")
            st.write(f["assertions"])
            st.markdown("**Evidence to examine**")
            st.write(f["evidence"])
            st.markdown("**Possible benign explanations**")
            st.write(f["benign"])
            st.markdown("**Human review**")
            st.checkbox("Accept signal", key=f"accept{i}")
            st.text_area("Auditor comments", key=f"comment{i}", placeholder="Add your judgement / context here.")

st.subheader("2 · Underlying financial movements")
display_cols = ["Account", "Type", "FY25", "FY26", "Absolute change", "% change"]
st.dataframe(analysis[display_cols], use_container_width=True, hide_index=True)

col_a, col_b = st.columns(2)
with col_a:
    st.download_button(
        "⬇️ Download analysed Excel",
        data=make_download_xlsx(analysis),
        file_name="AI_Audit_Risk_Copilot_Analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
with col_b:
    st.download_button(
        "⬇️ Download findings JSON",
        data=json.dumps(findings, indent=2),
        file_name="AI_Audit_Risk_Copilot_Findings.json",
        mime="application/json",
    )

st.divider()
st.subheader("3 · AI reasoning hand-off")
st.write("The prototype separates deterministic analytics from AI reasoning. Copy the generated prompt into an approved AI environment (for this demonstration, ChatGPT) to turn the signals into a structured second-level review.")
prompt = build_ai_prompt(findings)
st.code(prompt, language="text")
st.download_button("⬇️ Download AI reasoning prompt", data=prompt, file_name="AI_reasoning_prompt.txt", mime="text/plain")

st.divider()
st.subheader("4 · How this prototype was built")
st.markdown("""
**Workflow:** Financial data → deterministic relationship tests → risk signals → AI reasoning → human review.

The prototype was built with **Python, Pandas, Streamlit and ChatGPT**. The financial dataset is completely synthetic. The AI hand-off is deliberately separated from the calculations so that the model does not decide what constitutes an audit finding by itself.
""")

st.warning("Proof of concept only. Use synthetic or explicitly authorised data. AI output is not an audit conclusion and requires professional review.")
