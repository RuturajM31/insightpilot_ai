"""InsightPilot AI — Business analytics dashboard.

LEARN: Streamlit creates the interface, Pandas calculates facts, and Plotly
creates charts. An LLM is not used to invent financial results.

Version 1.2: Preserves the verified multi-agent workflow and improves UI defaults.
Retail KPIs use the separately tested src/retail_kpis.py engine.

Two modes:
- Retail demo: business metrics using verified transaction labels.
- General CSV: safe first-look analysis without assuming revenue columns.

Created by Ruturaj. Run: python -m streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path
from html import escape
import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.retail_kpis import calculate_retail_kpis
from src.sales_trends import calculate_monthly_trends
from src.business_insights import generate_business_insights
from src.agents.agent_workflow import run_agent_workflow
import os

ROOT = Path(__file__).resolve().parent
PREPARED = ROOT / "data" / "online_retail_prepared.csv"
PREPARED_GZIP = ROOT / "data" / "online_retail_prepared.csv.gz"
CLOUD_MODE = os.getenv("INSIGHTPILOT_DEPLOYMENT", "local").lower() == "cloud"
NAVY = "#09111F"
CARD = "#122136"
TEAL = "#5CE2CE"
BLUE = "#6D9FFF"
WHITE = "#F4F8FF"
SOFT = "#9CB0C9"

st.set_page_config(page_title="InsightPilot AI | Ruturaj", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
:root {color-scheme:dark}
.stApp {background:radial-gradient(ellipse at 90% -15%, #173350 0%, #09111F 48%);color:#F4F8FF}
.block-container {max-width:1480px;padding:1.2rem 2rem 3rem}
[data-testid="stSidebar"] {background:#0D192B;border-right:1px solid #25364D}
[data-testid="stSidebar"] .block-container {padding-top:2rem}
h1,h2,h3 {letter-spacing:-.035em}
[data-testid="stVerticalBlockBorderWrapper"] {border-color:#28405A!important;border-radius:18px}
[data-testid="stTabs"] [data-baseweb="tab-list"] {gap:1rem;border-bottom:1px solid #2B3E56}
[data-testid="stTabs"] button {font-weight:650}
[data-testid="stFileUploader"] {border-radius:14px}
.hero {border:1px solid #2B526A;background:linear-gradient(110deg,#162E4A,#0F1C32 68%,#123B42);border-radius:24px;padding:31px 36px;margin:0 0 20px}
.eyebrow {font-size:.72rem;letter-spacing:.18em;color:#5CE2CE;font-weight:800;text-transform:uppercase}
.hero h1 {font-size:clamp(2.2rem,3.6vw,3.5rem);line-height:1.15;margin:10px 0 8px;color:#F4F8FF}
.hero p {font-size:1.08rem;color:#BDD0E3;margin:0}
.brand {font-size:1.72rem;font-weight:850;letter-spacing:-.04em}
.subtle {color:#9CB0C9;font-size:.9rem}
.section-head {font-size:1.22rem;font-weight:760;color:#F4F8FF;margin:16px 0 8px}
.kpi {min-height:150px;padding:18px 15px;border-radius:19px;border:1px solid #2A415B;background:linear-gradient(135deg,#172B44,#112038);overflow:hidden}
.kpi .label {color:#B6C5D8;font-size:.84rem;font-weight:650;line-height:1.4;min-height:42px;overflow-wrap:break-word}
.kpi .number {color:#F5F9FF;font-size:clamp(1.25rem,1.6vw,1.85rem);font-weight:800;letter-spacing:-.035em;margin-top:7px;overflow-wrap:anywhere}
.kpi .context {color:#82DCCC;font-size:.73rem;margin-top:10px;line-height:1.45}
.insight {border:1px solid #29546A;background:#102638;border-radius:17px;padding:18px 20px;height:100%}
.insight b {color:#66E4D0}
.insight-card {min-height:156px;margin-bottom:14px;background:linear-gradient(135deg,#11283D,#112035)}
.insight-eyebrow {font-size:.7rem;letter-spacing:.13em;font-weight:850;margin-bottom:10px}
.insight-heading {color:#F4F8FF;font-weight:800;font-size:1.03rem;margin-bottom:8px}
.insight-body {color:#BDCEE0;font-size:.91rem;line-height:1.55}
.note {color:#A8BED3;font-size:.84rem}
.copilot-label {font-size:.76rem;color:#5CE2CE;letter-spacing:.12em;font-weight:800}
.footer {color:#92A9C4;border-top:1px solid #284059;margin-top:24px;padding-top:17px;font-size:.82rem}
@media (max-width:800px) {.block-container{padding:1rem}.hero{padding:22px}.kpi{min-height:108px;padding:12px}.kpi .number{font-size:1.36rem}}
</style>""", unsafe_allow_html=True)


def h(value: object) -> str:
    """Escape user-controlled text before placing it into an HTML card."""
    return escape(str(value), quote=True)


@st.cache_data(show_spinner=False)
def retail_data() -> pd.DataFrame:
    # Prefer the compressed full dataset for free cloud deployment.
    # Both files contain the same prepared transactions.
    path = PREPARED_GZIP if PREPARED_GZIP.is_file() else PREPARED
    if not path.is_file():
        raise FileNotFoundError(
            "Prepared demo data missing. Place data/online_retail_prepared.csv.gz "
            "or data/online_retail_prepared.csv in the project."
        )
    df = pd.read_csv(
        path, encoding="utf-8-sig", low_memory=False,
        dtype={"InvoiceNo": "string", "StockCode": "string", "CustomerID": "string"},
        parse_dates=["InvoiceDate"],
    )
    expected = {"InvoiceNo", "InvoiceDate", "Country", "Description", "BusinessCategory", "TransactionType", "LineAmount", "ProductSalesAmount"}
    if expected - set(df.columns):
        raise ValueError("Prepared retail dataset is missing required fields.")
    return df


@st.cache_data(show_spinner=False)
def uploaded_data(raw: bytes) -> pd.DataFrame:
    """Parse CSV values only; never execute code from the uploaded file."""
    if len(raw) > 25 * 1024 * 1024:
        raise ValueError("Please use a CSV file smaller than 25 MB.")
    last_error = None
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding=encoding, low_memory=False)
            break
        except UnicodeDecodeError as exc:
            last_error = exc
    else:
        raise ValueError("Could not read the CSV encoding.") from last_error
    if df.empty or df.shape[1] == 0:
        raise ValueError("The CSV needs at least one data row and one column.")
    if len(df) > 1_000_000:
        raise ValueError("Please use a CSV with at most 1,000,000 rows.")
    if df.columns.duplicated().any():
        raise ValueError("Duplicate column names are not supported.")
    return df


def choose_explorer_columns(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Prioritize business measurements and categories, not dates or IDs.

    Theory: column-role inference uses names and types as *hints*, not proof.
    Users can still change the selected column from the dropdown.
    """
    id_suffixes = ("id", "code", "number", "no")
    numeric = [
        name for name in df.select_dtypes(include="number").columns
        if not str(name).lower().replace("_", "").endswith(id_suffixes)
    ]

    def numeric_priority(name: str) -> tuple[int, str]:
        label = str(name).lower()
        if any(word in label for word in ("revenue", "sales", "amount")):
            return (0, label)
        if any(word in label for word in ("price", "profit", "cost")):
            return (1, label)
        return (2, label)

    numeric.sort(key=numeric_priority)

    def is_date_like(name: str) -> bool:
        label = str(name).lower().replace("_", "")
        return any(word in label for word in ("date", "time", "timestamp"))

    categories = [
        name for name in df.columns
        if name not in numeric
        and not is_date_like(name)
        and (
            pd.api.types.is_object_dtype(df[name])
            or isinstance(df[name].dtype, pd.CategoricalDtype)
            or pd.api.types.is_string_dtype(df[name])
        )
        and 1 <= df[name].nunique(dropna=True) <= 100
    ]

    def category_priority(name: str) -> tuple[int, str]:
        label = str(name).lower()
        if "category" in label or "segment" in label:
            return (0, label)
        if "product" in label or "country" in label:
            return (1, label)
        return (2, label)

    categories.sort(key=category_priority)
    return numeric, categories


def kpi(label: str, value: str, context: str) -> None:
    st.markdown(
        f'<div class="kpi"><div class="label">{h(label)}</div>'
        f'<div class="number">{h(value)}</div>'
        f'<div class="context">{h(context)}</div></div>',
        unsafe_allow_html=True,
    )


def style_chart(fig: go.Figure, height: int = 390) -> go.Figure:
    fig.update_layout(
        template="plotly_dark", height=height, paper_bgcolor=CARD,
        plot_bgcolor=CARD, font=dict(color="#DCE7F4", size=12),
        margin=dict(l=46, r=38, t=18, b=48),
        title=dict(text=""), hoverlabel=dict(bgcolor="#1C3653"),
        showlegend=False,
    )
    fig.update_xaxes(gridcolor="#28415B", zerolinecolor="#28415B", title_text="", automargin=True, tickfont=dict(size=11))
    fig.update_yaxes(gridcolor="#28415B", zerolinecolor="#28415B", title_text="", automargin=True, tickfont=dict(size=11))
    return fig


def graph(fig: go.Figure, height: int = 390) -> None:
    st.plotly_chart(style_chart(fig, height), use_container_width=True, theme=None, config={"displaylogo": False, "responsive": True})


def section(label: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="section-head">{h(label)}</div>', unsafe_allow_html=True)
    if subtitle:
        st.caption(subtitle)


with st.sidebar:
    st.markdown('<div class="brand">◈ InsightPilot <span style="color:#5CE2CE">AI</span></div>', unsafe_allow_html=True)
    st.caption("DECISION INTELLIGENCE STUDIO")
    st.divider()
    st.markdown("**DATA WORKSPACE**")
    uploaded = st.file_uploader("Upload your CSV", type=["csv"], help="CSV files up to 25 MB")
    demo = st.toggle("Use retail demo", value=True, disabled=uploaded is not None)
    st.divider()
    st.markdown("**EXPLORE**")
    st.caption("Interactive analytics · Data-quality checks · Business evidence")
    st.caption("Copilot chat · verified Analyst → Insights → QA workflow")
    st.divider()
    st.markdown('Created by **<span style="color:#5CE2CE">Ruturaj</span>**', unsafe_allow_html=True)
    st.caption("AI Applications · Final project")

st.markdown("""<div class="hero"><div class="eyebrow">DATA / EVIDENCE / DECISIONS</div>
<h1>InsightPilot AI<span style="color:#5CE2CE">.</span></h1>
<p>A smarter workspace for turning messy data into clear decisions.<br>
<span style="color:#5CE2CE;font-weight:700">Designed &amp; developed by Ruturaj</span></p></div>""", unsafe_allow_html=True)

try:
    if uploaded is not None:
        data = uploaded_data(uploaded.getvalue())
        is_retail = False
        source = uploaded.name
    elif demo:
        data = retail_data()
        is_retail = True
        source = "UCI Online Retail — prepared dataset"
    else:
        st.info("Upload a CSV or enable the retail demo in the sidebar.")
        st.stop()
except (ValueError, OSError, pd.errors.ParserError) as exc:
    st.error(f"Unable to load dataset: {exc}")
    st.stop()

st.caption(f"ACTIVE DATASET  ·  {source}  ·  {len(data):,} rows")

if is_retail:
    # NOTE: The classifications come from src/data_cleaning.py, not an LLM.
    countries = sorted(data["Country"].dropna().astype(str).unique().tolist())
    left, right = st.columns([2.2, 1], gap="medium")
    with left:
        chosen = st.multiselect("Countries", countries, default=[], placeholder="All countries")
    with right:
        dates = data["InvoiceDate"].dropna()
        date_range = st.date_input("Date range", value=(dates.min().date(), dates.max().date()),
                                   min_value=dates.min().date(), max_value=dates.max().date())
    filtered = data
    if chosen:
        filtered = filtered[filtered["Country"].isin(chosen)]
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
        filtered = filtered[(filtered["InvoiceDate"] >= start) & (filtered["InvoiceDate"] < end)]
    if filtered.empty:
        st.warning("No transactions match these filters. Try another selection.")
        st.stop()

    products = filtered[(filtered["BusinessCategory"] == "Product") & (filtered["TransactionType"] == "Sale")]
    returns = filtered[(filtered["BusinessCategory"] == "Product") & (filtered["TransactionType"] == "Cancellation")]
    verified_kpis = calculate_retail_kpis(filtered)
    gross = verified_kpis["gross_product_sales"]
    aov = verified_kpis["average_order_value"]
    returns_abs = -float(returns["LineAmount"].sum())
    invoice_count = verified_kpis["sales_orders"]
    country_count = int(filtered["Country"].nunique())
    st.markdown('<div class="section-head">Business performance</div>', unsafe_allow_html=True)
    cards = st.columns(4, gap="medium")
    with cards[0]: kpi("Product sales (gross)", f"£{gross/1e6:,.2f}M" if gross >= 1e6 else f"£{gross:,.0f}", "Positive identified product transactions")
    with cards[1]: kpi("Sales invoices", f"{invoice_count:,}", "Distinct invoices with product sales")
    with cards[2]: kpi("Average order value", f"£{aov:,.2f}", "Gross product sales ÷ sales invoices")
    with cards[3]: kpi("Product cancellations", f"£{returns_abs/1e6:,.2f}M" if returns_abs >= 1e6 else f"£{returns_abs:,.0f}", "Not a verified refund total")
    st.caption(f"Markets covered: {country_count:,} countries in the current selection.")
    st.caption("Figures are based on our documented transaction categories, not audited financial statements. Returns and discounts need careful interpretation.")

    tab1, tab2, tab3, tab4 = st.tabs(["◈ Executive dashboard", "▦ Explore transactions", "◇ Data quality", "✧ AI Copilot"])
    with tab1:
        section("Performance at a glance", "Use the country and date filters above to explore different periods.")
        c1, c2 = st.columns([1.32, 1], gap="medium")
        with c1:
            with st.container(border=True):
                st.markdown("**Monthly product sales**")
                monthly = products.groupby(products["InvoiceDate"].dt.to_period("M"))["ProductSalesAmount"].sum().sort_index()
                trend = pd.DataFrame({"Month": monthly.index.to_timestamp(), "Sales": monthly.values})
                fig = px.area(trend, x="Month", y="Sales", markers=True, color_discrete_sequence=[TEAL])
                fig.update_traces(line=dict(width=3), fillcolor="rgba(92,226,206,0.13)")
                fig.update_yaxes(tickprefix="£", tickformat="~s")
                fig.update_xaxes(tickformat="%b %Y", dtick="M2", tickangle=0)
                graph(fig)
        with c2:
            with st.container(border=True):
                st.markdown("**Top countries by product sales**")
                by_country = products.groupby("Country", dropna=False)["ProductSalesAmount"].sum().nlargest(8).sort_values()
                fig = px.bar(x=by_country.values, y=by_country.index.astype(str), orientation="h", color_discrete_sequence=[BLUE])
                fig.update_xaxes(tickprefix="£", tickformat="~s")
                fig.update_layout(margin=dict(l=110, r=28, t=18, b=45))
                graph(fig)
        c3, c4 = st.columns([1.32, 1], gap="medium")
        with c3:
            with st.container(border=True):
                st.markdown("**Best-selling products · by sales value**")
                named = products.dropna(subset=["Description"]).copy()
                top = named.groupby("Description")["ProductSalesAmount"].sum().nlargest(8).sort_values()
                labels = [str(v)[:30] + ("…" if len(str(v)) > 30 else "") for v in top.index]
                fig = px.bar(x=top.values, y=labels, orientation="h", color_discrete_sequence=[TEAL])
                fig.update_traces(customdata=top.index.astype(str).tolist(), hovertemplate="%{customdata}<br>Sales: £%{x:,.0f}<extra></extra>")
                fig.update_xaxes(tickprefix="£", tickformat="~s")
                fig.update_layout(margin=dict(l=155, r=22, t=18, b=45))
                graph(fig)
        with c4:
            with st.container(border=True):
                st.markdown("**Key findings**")
                if not monthly.empty:
                    best_month = monthly.idxmax()
                    st.markdown(f'<div class="insight"><b>Highest sales month</b><br>{h(str(best_month))}<br><span class="subtle">£{monthly.max():,.0f} in classified product sales</span></div>', unsafe_allow_html=True)
                st.write("")
                if not by_country.empty:
                    leader = by_country.idxmax()
                    st.markdown(f'<div class="insight"><b>Leading market</b><br>{h(leader)}<br><span class="subtle">Largest product-sales total in this selection</span></div>', unsafe_allow_html=True)
                st.caption("The source starts in December 2010 and ends on 9 December 2011. Partial months should not be compared directly with full months.")
        # Sales growth uses the tested function from src/sales_trends.py.
        # It respects the current country and date filters.
        section("Month-over-month growth", "How product sales changed compared with the previous calendar month.")
        trends = calculate_monthly_trends(filtered)
        complete = trends.loc[trends["MoMGrowthPct"].notna()].copy()
        if not complete.empty:
            latest = complete.iloc[-1]
            latest_month = latest["Month"].strftime("%B %Y")
            change = float(latest["MoMGrowthPct"])
            direction = "increased" if change > 0 else "decreased" if change < 0 else "were unchanged"
            st.markdown(
                f'<div class="insight"><b>Latest valid monthly comparison: {h(latest_month)}</b><br>'
                f'Product sales {direction} by <b>{abs(change):.2f}%</b> versus the previous month.'
                f'</div>', unsafe_allow_html=True,
            )
            st.write("")
            growth_fig = px.bar(
                complete, x="Month", y="MoMGrowthPct",
                color="MoMGrowthPct", color_continuous_scale=["#EF807A", "#29465B", TEAL],
                color_continuous_midpoint=0,
                hover_data={"MoMGrowthPct": ":.2f", "ProductSales": ":,.2f"},
            )
            growth_fig.update_layout(coloraxis_showscale=False)
            growth_fig.update_yaxes(ticksuffix="%")
            growth_fig.update_xaxes(tickformat="%b %Y", dtick="M2", tickangle=0)
            growth_fig.update_traces(hovertemplate="%{x|%b %Y}<br>Growth: %{y:+.2f}%<extra></extra>")
            with st.container(border=True):
                st.markdown("**Monthly sales growth (%)**")
                graph(growth_fig, height=330)
        else:
            st.info("No comparable complete months are available for these filters.")

        # Interpret the same filtered transactions using the tested rules engine.
        # No LLM is involved; we never guess why performance changed.
        section("Business insights", "Verified observations from your selected records — not AI-generated guesses.")
        findings = generate_business_insights(filtered)
        for offset in range(0, len(findings), 2):
            pair = st.columns(2, gap="medium")
            for panel, finding in zip(pair, findings[offset:offset + 2]):
                kind = finding["type"]
                symbol = {"success": "↗", "warning": "!", "info": "i"}.get(kind, "i")
                accent = {"success": TEAL, "warning": "#FFB574", "info": BLUE}.get(kind, BLUE)
                with panel:
                    st.markdown(
                        '<div class="insight insight-card">'
                        f'<div class="insight-eyebrow" style="color:{accent}">{symbol} VERIFIED FINDING</div>'
                        f'<div class="insight-heading">{h(finding["title"])}</div>'
                        f'<div class="insight-body">{h(finding["message"])}</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
        st.caption("Insight rules run on the current country/date selection. A calendar coverage check cannot certify source completeness.")

        with st.expander("View monthly figures and coverage"):
            display = trends.copy()
            display["Month"] = display["Month"].dt.strftime("%Y-%m")
            display = display.rename(columns={
                "ProductSales": "Gross product sales (£)",
                "MoMGrowthPct": "Growth (%)",
                "IsCompleteMonth": "Full calendar-date coverage",
            })
            st.dataframe(display, use_container_width=True, hide_index=True)
            st.caption(
                "Coverage means the selected records start/end on the relevant calendar boundaries. "
                "It does not prove that every transaction is present. "
                "December 2011 is incomplete in the original source. "
                "Filtering dates may create additional partial months."
            )
    with tab2:
        section("Transaction explorer", "Browse the records that power the figures.")
        selected_type = st.selectbox("Transaction type", ["All"] + sorted(filtered["TransactionType"].dropna().unique().tolist()))
        view = filtered if selected_type == "All" else filtered[filtered["TransactionType"] == selected_type]
        st.dataframe(view.head(500), use_container_width=True, hide_index=True)
        st.caption(f"Showing {min(len(view), 500):,} of {len(view):,} matching records.")
        st.download_button("Download filtered CSV", view.to_csv(index=False).encode("utf-8-sig"), "insightpilot_filtered.csv", "text/csv")
    with tab3:
        section("Data quality report", "These checks describe the data; they do not delete any records.")
        q = pd.DataFrame({"Column": filtered.columns, "Missing": filtered.isna().sum().values,
                          "Missing %": (filtered.isna().mean().values * 100).round(2), "Type": filtered.dtypes.astype(str).values})
        st.dataframe(q, use_container_width=True, hide_index=True)
        st.info(f"Exact duplicate rows in selected data: {filtered.duplicated().sum():,}. Duplicates are preserved pending business review.")
    with tab4:
        # The multi-agent workflow retains Python-verified facts and only
        # displays LLM interpretations that pass our explicit QA gate.
        section("Ask InsightPilot", "Verified facts, optional AI explanation, and auditable agent trace.")
        st.info(
            "Analyst → Insights (Llama 3.2 via local Ollama) → QA. "
            "Your selected countries and dates control all calculations. "
            "Local Ollama is optional; verified Python answers work everywhere."
        )
        llm_enabled = st.toggle(
            "Enable local AI explanations (requires Ollama on this computer)",
            value=(not CLOUD_MODE and os.getenv("INSIGHTPILOT_USE_OLLAMA", "0") == "1"),
            disabled=CLOUD_MODE,
            key="copilot_llm_enabled",
        )
        if CLOUD_MODE:
            st.caption("Cloud deployment: verified analytics mode; local Ollama is not accessible to this server.")
        elif llm_enabled:
            st.caption("Local Ollama can be slow. If it is unavailable, the verified answer remains visible.")
        else:
            st.caption("Verified-only mode. Suitable for Streamlit Community Cloud without an inference provider.")

        # Reset the conversation when filters change so an earlier answer
        # cannot be mistaken for a finding about the new selection.
        selection_key = (tuple(sorted(chosen)), tuple(str(x) for x in date_range), bool(llm_enabled), source)
        if st.session_state.get("copilot_selection") != selection_key:
            st.session_state["copilot_selection"] = selection_key
            st.session_state["copilot_history"] = []

        examples = [
            "What was our best sales month?",
            "Which month had the strongest growth?",
            "What was the largest decline?",
            "What were our total sales?",
            "Are any months incomplete?",
            "Why did sales decline?",
        ]
        with st.expander("Example questions", expanded=False):
            for example in examples:
                st.markdown(f"• {example}")

        # A form works reliably inside Streamlit tabs and only submits
        # the question when the user presses Send (or Enter).
        with st.form("retail_copilot_question", clear_on_submit=True):
            question = st.text_input(
                "Ask a business question",
                placeholder="e.g. Which month had the strongest growth?",
                max_chars=500,
            )
            submitted = st.form_submit_button("✧ Ask InsightPilot", type="primary")

        if submitted:
            if not question.strip():
                st.warning("Please type a business question first.")
            else:
                try:
                    with st.spinner("Analyst → Insights → QA working..."):
                        response = run_agent_workflow(
                            filtered, question, use_llm=(llm_enabled and not CLOUD_MODE),
                        )
                    st.session_state["copilot_history"].append({
                        "question": question.strip(),
                        "verified_answer": response["verified_answer"],
                        "ai_explanation": response["ai_explanation"],
                        "evidence": response["evidence"],
                        "engine": response["engine"],
                        "qa_status": response["qa_status"],
                        "qa_findings": response["qa_findings"],
                        "agent_trace": response["agent_trace"],
                    })
                except (ValueError, TypeError, KeyError) as exc:
                    st.error(f"Unable to answer that question: {exc}")

        for item in st.session_state["copilot_history"]:
            with st.chat_message("user"):
                st.write(item["question"])
            with st.chat_message("assistant"):
                st.markdown("**Verified finding**")
                st.write(item["verified_answer"])
                if item["ai_explanation"]:
                    st.markdown("**AI interpretation · QA approved**")
                    st.write(item["ai_explanation"])
                elif item["qa_status"] == "not_run":
                    st.caption("This question is outside the supported analytics scope; no LLM or QA review was needed.")
                elif llm_enabled and item["qa_status"] == "rejected":
                    st.warning("The QA Agent rejected the AI interpretation. The verified finding is still valid.")
                elif llm_enabled:
                    st.caption("No approved AI interpretation was available for this question.")
                if item["evidence"]:
                    with st.expander("Supporting evidence"):
                        for entry in item["evidence"]:
                            st.write(f"• {entry}")
                with st.expander("Agent execution trace and QA findings"):
                    for step in item["agent_trace"]:
                        st.write(step)
                    for finding in item["qa_findings"]:
                        st.write(f"• {finding}")
                st.caption(f"Engine: {item['engine']} · QA: {item['qa_status']}")

        if st.session_state["copilot_history"]:
            if st.button("Clear conversation", key="clear_copilot"):
                st.session_state["copilot_history"] = []
                st.rerun()
        st.caption(
            "AI explanations are optional, can be rejected, and are not guaranteed correct. "
            "The figures are produced by Python. This Copilot supports defined retail questions, "
            "not arbitrary questions about any uploaded CSV."
        )

else:
    # Generic dataset: show universal statistics; never assume numeric IDs are revenue.
    section("Dataset health", "A safe first look at your uploaded file.")
    missing = int(data.isna().sum().sum())
    duplicates = int(data.duplicated().sum())
    cards = st.columns(4, gap="medium")
    for col, item in zip(cards, [("Records", f"{len(data):,}", "Total rows"),
                                 ("Columns", str(len(data.columns)), "Detected fields"),
                                 ("Missing cells", f"{missing:,}", "Across all columns"),
                                 ("Exact duplicates", f"{duplicates:,}", "No rows removed")]):
        with col: kpi(*item)
    tab1, tab2, tab3 = st.tabs(["◈ Visual explorer", "▦ Data preview", "◇ Data quality"])
    # Meaningful measures and categories appear first; dates are excluded.
    numerical, category = choose_explorer_columns(data)
    with tab1:
        section("Visual explorer", "These are descriptive charts; they do not assume a particular business domain.")
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("**Numerical distribution**")
                if numerical:
                    column = st.selectbox("Measurement", numerical)
                    values = data[[column]].dropna()
                    if len(values) > 20000: values = values.sample(20000, random_state=42)
                    fig = px.histogram(values, x=column, nbins=45, color_discrete_sequence=[BLUE])
                    graph(fig)
                else:
                    st.info("No suitable numerical measurements detected.")
        with c2:
            with st.container(border=True):
                st.markdown("**Category breakdown**")
                if category:
                    column = st.selectbox("Category", category)
                    counts = data[column].fillna("Missing").astype(str).value_counts().head(8).sort_values()
                    fig = px.bar(x=counts.values, y=counts.index, orientation="h", color_discrete_sequence=[TEAL])
                    graph(fig)
                else:
                    st.info("No small category columns detected.")
        st.caption("Business-friendly defaults are suggested automatically. Use the dropdowns to choose other available measurements and categories.")
    with tab2:
        section("Data preview")
        st.dataframe(data.head(300), use_container_width=True, hide_index=True)
        st.download_button("Download dataset summary", pd.DataFrame({"column":data.columns,"type":data.dtypes.astype(str).values,
           "missing":data.isna().sum().values}).to_csv(index=False), "insightpilot_column_summary.csv", "text/csv")
    with tab3:
        section("Data quality report")
        quality = pd.DataFrame({"Column":data.columns, "Missing":data.isna().sum().values,
                               "Missing %":(data.isna().mean().values*100).round(2),"Type":data.dtypes.astype(str).values})
        st.dataframe(quality, use_container_width=True, hide_index=True)
        st.info(f"Exact duplicate rows: {duplicates:,}. No changes have been made to your uploaded data.")

st.markdown('<div class="footer">◈ INSIGHTPILOT AI &nbsp;·&nbsp; Developed by <b style="color:#5CE2CE">Ruturaj</b> &nbsp;·&nbsp; Python / Pandas / Plotly / Streamlit &nbsp;·&nbsp; Analytics version 1.2 · Multi-agent Copilot</div>', unsafe_allow_html=True)
