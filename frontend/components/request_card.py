# frontend/components/request_card.py
import streamlit as st
from components.status_badge import status_badge

def render_request_card(
    request: dict,
    viewer_role: str,
    on_approve: callable = None,
    on_reject: callable = None,
    on_pickup: callable = None,
    on_cancel: callable = None
):
    # Format dates nicely
    created_at_str = request.get("created_at", "")
    if isinstance(created_at_str, str) and created_at_str:
        try:
            # Strip timezone if needed and format
            created_at_str = created_at_str.split(".")[0].replace("T", " ")
        except Exception:
            pass

    status = request.get("status")
    message = request.get("message")
    ngo_note = request.get("ngo_note")

    # Construct the metadata details depending on role
    if viewer_role == "donor":
        entity_label = f"Requester: {request.get('requester_name')}"
    else:
        entity_label = f"Donor: {request.get('donor_name')}"

    # Render card
    html = f"""
    <div style="
        background-color: #1F2211;
        border: 0.5px solid rgba(167,209,41,0.08);
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 12px;
    ">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
            <span style="font-size:15px; font-weight:500; color:#E8EDE0;">{request.get('item_title')}</span>
            {status_badge(status)}
        </div>
        <div style="font-size:13px; color:#9AA582; margin-bottom:6px;">
            {entity_label}
        </div>
        {f'<div style="font-size:13px; color:#9AA582; font-style:italic; margin-top:4px; margin-bottom:4px;">"{message}"</div>' if message else ''}
    """

    # NGO note is visible to donor and NGO
    if ngo_note and (viewer_role == "donor" or viewer_role == "ngo"):
        html += f"""
        <div style="background-color:rgba(123, 175, 212, 0.08); border-left:3px solid #7BAFD4; border-radius:4px; padding:6px 10px; margin-top:6px; margin-bottom:6px; font-size:12px; color:#9AA582;">
            <strong>NGO note:</strong> {ngo_note}
        </div>
        """

    # If approved, display phone number to approved requester or donor
    donor_phone = request.get("donor_phone")
    if status == "approved" and donor_phone:
        html += f"""
        <div style="background-color:rgba(167,209,41,0.08); border-left:3px solid #BADE52; border-radius:4px; padding:6px 10px; margin-top:6px; margin-bottom:6px; font-size:12px; color:#9AA582;">
            📞 <strong>Donor phone:</strong> <span style="color:#BADE52; font-weight:500;">{donor_phone}</span>
        </div>
        """

    html += f"""
        <div style="font-size:11px; color:#616B4E; margin-top:8px;">
            Submitted on {created_at_str}
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)

    # Render action buttons
    col1, col2 = st.columns([1, 4])
    with col1:
        if viewer_role == "donor":
            if status == "pending":
                if st.button("Approve", key=f"approve_{request['id']}", type="primary"):
                    if on_approve:
                        on_approve(request["id"])
                if st.button("Reject", key=f"reject_{request['id']}", type="secondary"):
                    if on_reject:
                        on_reject(request["id"])
            elif status == "approved":
                if st.button("Mark picked up", key=f"pickup_{request['id']}", type="primary"):
                    if on_pickup:
                        on_pickup(request["id"])
        elif viewer_role in ("recipient", "ngo"):
            if status == "pending":
                if st.button("Cancel request", key=f"cancel_{request['id']}", type="secondary"):
                    if on_cancel:
                        on_cancel(request["id"])
