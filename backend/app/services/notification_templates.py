"""Reusable notification templates.

Each event defines the website notification (title/message), the email subject
and body, and the SMS text. Placeholders use str.format(**context).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Template:
    title: str
    message: str
    sms: str | None
    email_subject: str | None = None  # defaults to title
    email_body: str | None = None  # defaults to message


T = Template
TEMPLATES: dict[str, Template] = {
    # --- Account -----------------------------------------------------------
    "account_registered": T(
        "Welcome to AVTBVS Membership",
        "Dear {name}, your account has been created. Please verify your email address and mobile number, "
        "then complete the Life Membership Application form.",
        "AVTBVS: Welcome {name}. Your account is created. Verify your mobile & email, then apply for membership.",
    ),
    "otp_email": T(
        "Email verification code",
        "Your AVTBVS email verification code is {code}. It expires in {minutes} minutes. "
        "Do not share this code with anyone.",
        None,
    ),
    "otp_phone": T(
        "Mobile verification code", "", "AVTBVS: Your mobile verification code is {code}. Valid for {minutes} "
        "minutes. Do not share it with anyone.",
    ),
    "password_reset": T(
        "Reset your password",
        "We received a request to reset your AVTBVS Membership password. Use this link within {minutes} minutes: "
        "{link}\n\nIf you did not request this, you can ignore this email; your password will not change.",
        None,
    ),
    "admin_invite": T(
        "You have been given administrator access",
        "Dear {name}, a Super Admin has created an {role} account for you on AVTBVS Membership. "
        "Set your password using this link within {hours} hours: {link}",
        None,
    ),
    "role_changed": T(
        "Your access level has changed",
        "Dear {name}, your AVTBVS Membership access level is now {role}.",
        None,
    ),
    # --- Application (applicant) --------------------------------------------
    "application_submitted": T(
        "Application submitted",
        "Your Life Membership application {application_number} has been submitted and is pending verification "
        "by the Membership Enrollment Committee.",
        "AVTBVS: Application {application_number} submitted successfully. We will notify you after verification.",
    ),
    "application_correction_required": T(
        "Corrections required in your application",
        "Your application {application_number} needs corrections before it can be approved.\n\n"
        "Requested corrections:\n{notes}\n\nPlease log in, correct the details and resubmit.",
        "AVTBVS: Corrections are required in application {application_number}. Please log in to view and resubmit.",
    ),
    "application_resubmitted": T(
        "Application resubmitted",
        "Your corrected application {application_number} has been resubmitted for verification.",
        "AVTBVS: Application {application_number} resubmitted for verification.",
    ),
    "application_approved": T(
        "Membership approved – Welcome!",
        "Congratulations {name}! Your application {application_number} has been approved. "
        "Your official membership registration number is {membership_number}.",
        "AVTBVS: Congratulations! Your membership is approved. Regd. Mem. No: {membership_number}.",
    ),
    "membership_number_assigned": T(
        "Membership number assigned",
        "Your official AVTBVS membership registration number is {membership_number}. "
        "Please quote it in all communication with the Sabha.",
        None,
    ),
    "application_rejected": T(
        "Application not approved",
        "We regret to inform you that your application {application_number} was not approved.\n\nReason: {reason}",
        "AVTBVS: Application {application_number} was not approved. Please log in to view the reason.",
    ),
    # --- Profile editing (member) ------------------------------------------
    "edit_request_submitted": T(
        "Profile edit request received",
        "Your request to edit your membership details has been sent to the administrators.",
        None,
    ),
    "edit_request_approved": T(
        "Profile editing permitted",
        "Your request to edit your membership details was approved. You may edit your profile until "
        "{expires_at} (24 hours). After that, editing access expires automatically.",
        "AVTBVS: Profile edit approved. You can edit your details until {expires_at}.",
    ),
    "edit_request_rejected": T(
        "Profile edit request not approved",
        "Your request to edit your membership details was not approved.\n\nNote: {note}",
        "AVTBVS: Your profile edit request was not approved. Log in for details.",
    ),
    "edit_permission_expired": T(
        "Profile editing access expired",
        "Your 24-hour profile editing access has expired. Submit a new request if further changes are needed.",
        "AVTBVS: Your 24-hour profile editing access has expired.",
    ),
    "membership_status_changed": T(
        "Membership status updated",
        "Your membership {membership_number} status is now {status}. {reason}",
        "AVTBVS: Your membership {membership_number} is now {status}.",
    ),
    "account_linked": T(
        "Membership linked to your account",
        "Your existing membership {membership_number} has been linked to this account. "
        "You now have access to the member directory.",
        "AVTBVS: Membership {membership_number} is now linked to your online account.",
    ),
    # --- Admin notifications -------------------------------------------------
    "admin_new_application": T(
        "New membership application",
        "{name} submitted application {application_number}. It is waiting for verification.",
        None,
    ),
    "admin_application_resubmitted": T(
        "Application resubmitted",
        "{name} resubmitted application {application_number} after corrections.",
        None,
    ),
    "admin_edit_request": T(
        "Member requests editing access",
        "{name} ({membership_number}) requested permission to edit their details.\n\nReason: {reason}",
        None,
    ),
    "admin_member_edited": T(
        "Member updated their details",
        "{name} ({membership_number}) changed: {fields}.",
        None,
    ),
}


def render(event: str, context: dict) -> Template:
    t = TEMPLATES[event]
    safe = _SafeDict(context)
    return Template(
        title=t.title.format_map(safe),
        message=t.message.format_map(safe),
        sms=t.sms.format_map(safe) if t.sms else None,
        email_subject=(t.email_subject or t.title).format_map(safe),
        email_body=(t.email_body or t.message).format_map(safe),
    )


class _SafeDict(dict):
    def __missing__(self, key):
        return ""
