"""Streamlit presentation helpers. No scoring or filter behavior lives here."""

from pathlib import Path

import streamlit as st

CSS_PATH = Path(__file__).with_name("theme.css")


def apply_theme() -> None:
    st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def score_color(score: float) -> str:
    if score >= 80:
        return "#16a34a"
    if score >= 65:
        return "#ca8a04"
    return "#ea580c"


def score_ring(score: float) -> str:
    color = score_color(score)
    return (
        f'<div class="score-wrap"><div class="score-ring" style="background:conic-gradient({color} {score}%, #e2e8f0 0)">'
        f'<div class="score-ring-inner">{score:.1f}</div></div>'
        f"<div><div style='font-size:0.8rem;color:#64748b;font-weight:600'>Opportunity Score</div>"
        f"<div style='font-size:0.85rem;color:#64748b'>Deterministic rank for this domain</div></div></div>"
    )


def chips(values: list[str]) -> str:
    if not values:
        return "<span style='color:#64748b'>None observed</span>"
    return "<div class='chip-row'>" + "".join(f"<span class='chip'>{item}</span>" for item in values[:16]) + "</div>"
