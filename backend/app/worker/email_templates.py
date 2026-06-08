# Email templates for GiveCircle transactional emails

REQUEST_RECEIVED_SUBJECT = "New donation request for {item_title}"
REQUEST_RECEIVED_TEMPLATE = """
<html>
<body>
    <h2>Hello {donor_name},</h2>
    <p>A new request has been submitted for your item <strong>{item_title}</strong> by <strong>{requester_name}</strong>.</p>
    <p>Message: <em>"{message}"</em></p>
    <p>Please log in to the platform to approve or reject this request.</p>
    <p>Best regards,<br>The GiveCircle Team</p>
</body>
</html>
"""

REQUEST_APPROVED_SUBJECT = "Your request for {item_title} has been approved!"
REQUEST_APPROVED_TEMPLATE = """
<html>
<body>
    <h2>Hello {requester_name},</h2>
    <p>Great news! Your request for the item <strong>{item_title}</strong> has been approved by the donor.</p>
    <p><strong>Donor Contact Phone:</strong> {donor_phone}</p>
    <p><strong>Pickup Instructions:</strong> {pickup_instructions}</p>
    <p>Please contact the donor to coordinate pickup.</p>
    <p>Best regards,<br>The GiveCircle Team</p>
</body>
</html>
"""

REQUEST_REJECTED_SUBJECT = "Update on your request for {item_title}"
REQUEST_REJECTED_TEMPLATE = """
<html>
<body>
    <h2>Hello {requester_name},</h2>
    <p>We wanted to let you know that your request for the item <strong>{item_title}</strong> was not approved at this time.</p>
    <p>Feel free to browse other available items on the platform.</p>
    <p>Best regards,<br>The GiveCircle Team</p>
</body>
</html>
"""

PICKUP_CONFIRMED_SUBJECT = "Pickup confirmed: {item_title}"
PICKUP_CONFIRMED_TEMPLATE = """
<html>
<body>
    <h2>Hello {user_name},</h2>
    <p>This email confirms that the item <strong>{item_title}</strong> has been successfully picked up.</p>
    <p>Thank you for participating in GiveCircle and supporting the community!</p>
    <p>Best regards,<br>The GiveCircle Team</p>
</body>
</html>
"""
