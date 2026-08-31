"""Helpers pequenos para as páginas Streamlit."""

from __future__ import annotations

import streamlit as st

from ..database.connection import get_engine
from ..database.repository import fetch_dataframe


@st.cache_resource
def cached_engine():
    return get_engine()


def show_sql_page(title: str, sql: str, description: str = ""):
    st.title(title)
    if description:
        st.caption(description)
    try:
        frame = fetch_dataframe(cached_engine(), sql)
        st.dataframe(frame, use_container_width=True)
    except Exception as exc:
        st.error(f"Não foi possível consultar o banco: {exc}")

