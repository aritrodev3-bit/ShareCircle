# frontend/chart_theme.py
PLOTLY_LAYOUT = dict(
    paper_bgcolor="#1F2211",
    plot_bgcolor="#1F2211",
    font=dict(family="Inter, sans-serif", color="#9AA582", size=12),
    title_font=dict(color="#E8EDE0", size=15, family="Inter, sans-serif"),
    colorway=["#A7D129", "#616F39", "#7BAFD4", "#D4A017", "#E05C5C"],
    xaxis=dict(
        gridcolor="rgba(167,209,41,0.06)",
        linecolor="rgba(167,209,41,0.08)",
        tickfont=dict(color="#9AA582"),
    ),
    yaxis=dict(
        gridcolor="rgba(167,209,41,0.06)",
        linecolor="rgba(167,209,41,0.08)",
        tickfont=dict(color="#9AA582"),
    ),
    margin=dict(l=40, r=20, t=50, b=40),
    hoverlabel=dict(
        bgcolor="#272B14",
        bordercolor="rgba(167,209,41,0.16)",
        font_color="#E8EDE0",
    ),
)

def apply_theme(fig):
    """Call fig.update_layout(**PLOTLY_LAYOUT) and return fig."""
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig
