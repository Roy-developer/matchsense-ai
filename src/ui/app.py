"""Streamlit dashboard (APP-002).

The judge flow: match state -> momentum timeline -> insight -> Why? receipt ->
Critic decision -> audience switch. Nothing here computes football facts; it
only renders the deterministic pipeline's output.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from src.explainability.adversarial import adversarial_demo  # noqa: E402
from src.pipeline import receipt_payload, run_pipeline_from_dir  # noqa: E402
from src.ui.charts import control_timeline, event_volume  # noqa: E402

DATA_DIR = ROOT / "data" / "synthetic"

st.set_page_config(page_title="MatchSense AI", page_icon="⚽", layout="wide")


@st.cache_data(show_spinner=False)
def load_run(data_dir: str, match_id: str):
    return run_pipeline_from_dir(data_dir, match_id)


def render_truth_badge(layer: str) -> str:
    colours = {"observed": "#1f6feb", "derived": "#8250df", "interpreted": "#bf8700"}
    return (
        f"<span style='background:{colours.get(layer, '#555')};color:#fff;"
        f"padding:2px 8px;border-radius:10px;font-size:11px;'>{layer.upper()}</span>"
    )


def main() -> None:
    run = load_run(str(DATA_DIR), "MATCH-001")
    receipts = receipt_payload(run)

    st.title("MatchSense AI")
    st.caption(
        "Analytics determines what happened. Evidence proves why it happened. "
        "The LLM explains it without inventing facts."
    )

    summary = run.summary()
    left, mid, right = st.columns(3)
    left.metric(
        f"{summary['home_team']} v {summary['away_team']}",
        summary["score"],
        help="Synthetic match: deterministic for a fixed seed.",
    )
    mid.metric("Events processed", summary["events"])
    right.metric("Detections", f"{summary['detections']} (approved {summary['approved']})")

    st.divider()
    st.subheader("Momentum timeline")
    st.caption("Weighted control score per five-minute window. A shift needs several signals.")
    timeline = control_timeline(run.events)
    st.line_chart(timeline.set_index("minute"), height=300)

    with st.expander("Event volume per team"):
        st.bar_chart(event_volume(run.events).set_index("minute"), height=220)

    st.divider()
    st.subheader("Critic check — attempts that must be blocked")
    st.caption(
        "MatchSense does not publish the first AI explanation. These claims are "
        "deliberately unsupported; deterministic verification refuses all of them."
    )
    for attempt in adversarial_demo(run):
        verdict = "⛔ blocked" if attempt["blocked"] else "⚠️ not blocked"
        with st.expander(f"{verdict} · {attempt['case']}"):
            st.markdown(f"*Attempted claim:* {attempt['claim']}")
            st.markdown(f"*Status:* `{attempt['status']}`")
            for reason in attempt["reasons"]:
                st.markdown(f"- {reason}")

    st.divider()
    st.subheader("Insights")
    if not receipts:
        st.info("No control shifts detected for this match.")
        return

    for receipt, insight in zip(receipts, run.insights):
        detection = insight.detection
        approved = insight.verified is not None
        icon = "✅" if approved else "⛔"
        team_name = run.meta.home_team if detection.team_id == "HOME" else run.meta.away_team
        title = (
            f"{icon} {team_name} · {receipt['window']['start_minute']:.0f}-{receipt['window']['end_minute']:.0f}' · "
            f"confidence {receipt['truth_layers']['derived']['confidence']:.2f}"
        )

        with st.expander(title, expanded=approved):
            if approved:
                st.markdown(f"**Claim** — {insight.verified.claim}")
                st.markdown(f"*Why it matters:* {insight.verified.significance}")

                audience = st.radio(
                    "Audience",
                    ("fan", "analyst", "broadcast"),
                    horizontal=True,
                    key=f"aud-{receipt['insight_id']}",
                )
                narrative = insight.narratives.get(audience)
                if narrative:
                    st.success(f"**{narrative.headline}** — {narrative.body}")
                else:
                    st.warning("No approved narrative for this audience.")
            else:
                st.error(f"**Rejected claim** — {insight.rejected_claim}")
                st.markdown(f"*Critic reason:* {insight.critic_reason}")

            st.markdown("### Why? — Evidence Receipt")
            observed, derived, interpreted = st.columns(3)

            with observed:
                st.markdown(render_truth_badge("observed"), unsafe_allow_html=True)
                st.write(f"{len(receipt['truth_layers']['observed']['event_ids'])} events in window")
                st.json(receipt["provenance"], expanded=False)

            with derived:
                st.markdown(render_truth_badge("derived"), unsafe_allow_html=True)
                st.write(
                    f"Control score "
                    f"{receipt['truth_layers']['derived']['control_score_before']:.2f} → "
                    f"{receipt['truth_layers']['derived']['control_score_after']:.2f}"
                )
                st.write("Confidence breakdown")
                st.json(receipt["truth_layers"]["derived"]["confidence_breakdown"])
                st.json(receipt["truth_layers"]["derived"]["deltas"])

            with interpreted:
                st.markdown(render_truth_badge("interpreted"), unsafe_allow_html=True)
                st.write(f"Critic: **{receipt['critic']['decision']}**")
                if receipt["critic"]["reason"]:
                    st.write(receipt["critic"]["reason"])
                st.write(f"Algorithm: `{receipt['algorithm_version']}`")
                st.write(f"Verification: `{receipt['verification_status']}`")

            st.markdown("#### Triggered signals")
            st.dataframe(receipt["signals"], hide_index=True)


main()
