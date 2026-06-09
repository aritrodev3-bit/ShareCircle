# frontend/components/status_badge.py

def status_badge(status: str) -> str:
    """Returns an HTML span chip for item or request status."""
    config = {
        "available":  ("rgba(167,209,41,0.12)",  "#BADE52"),
        "reserved":   ("rgba(123,175,212,0.12)", "#7BAFD4"),
        "donated":    ("rgba(97,107,78,0.25)",   "#9AA582"),
        "removed":    ("rgba(224,92,92,0.10)",   "#E05C5C"),
        "pending":    ("rgba(212,160,23,0.12)",  "#D4BA50"),
        "approved":   ("rgba(167,209,41,0.12)",  "#BADE52"),
        "rejected":   ("rgba(224,92,92,0.10)",   "#E05C5C"),
        "picked_up":  ("rgba(97,107,78,0.25)",   "#9AA582"),
        "cancelled":  ("rgba(97,107,78,0.25)",   "#9AA582"),
    }
    bg, color = config.get(status, ("rgba(97,107,78,0.25)", "#9AA582"))
    label = status.replace("_", " ").title()
    return (
        f'<span style="background:{bg}; color:{color}; border:0.5px solid {color}33; '
        f'border-radius:6px; padding:2px 8px; font-size:11px; font-weight:500;">'
        f'{label}</span>'
    )

def category_badge(category: str) -> str:
    """Returns an olive-tinted chip for item category."""
    return (
        f'<span style="background:rgba(97,111,57,0.35); color:#CEEA7A; '
        f'border-radius:6px; padding:2px 8px; font-size:11px; font-weight:500;">'
        f'{category.title()}</span>'
    )
