"""End-to-end UI walkthrough of the complete membership workflow, with screenshots."""
import json
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = "http://127.0.0.1:5173"
OUTBOX = Path(__file__).resolve().parents[1] / "backend" / "storage" / "outbox.log"
SHOTS = Path(__file__).resolve().parent / "shots"
SHOTS.mkdir(exist_ok=True)
EMAIL = f"ramesh.{int(time.time())}@example.org"
PHONE = "98" + str(int(time.time()))[-8:]
errors: list[str] = []


def otp_for(to: str, channel: str) -> str:
    for _ in range(40):
        if OUTBOX.exists():
            for line in reversed(OUTBOX.read_text().splitlines()):
                m = json.loads(line)
                if m["to"] == to and m["channel"] == channel and "verification code" in m["body"]:
                    return re.search(r"\b(\d{6})\b", m["body"]).group(1)
        time.sleep(0.5)
    raise RuntimeError(f"no OTP for {to}")


def shot(page, name, full=True):
    page.wait_for_timeout(400)
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=full)
    print("shot", name)


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1366, "height": 900})
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "401" not in m.text and errors.append(f"console: {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    # Public home + directory
    page.goto(BASE + "/")
    expect(page.get_by_text("Sri Subramanyam Chetty")).to_be_visible()
    shot(page, "01-home")
    page.goto(BASE + "/directory")
    shot(page, "02-public-directory", full=False)

    # Register
    page.goto(BASE + "/register")
    page.get_by_label("Full name").fill("Ramesh Kumar Kottapalli")
    page.get_by_label("Email address").fill(EMAIL)
    page.get_by_label("Mobile number").fill(PHONE)
    page.locator('input[autocomplete="new-password"]').nth(0).fill("Ramesh-pass-2026")
    page.locator('input[autocomplete="new-password"]').nth(1).fill("Ramesh-pass-2026")
    shot(page, "03-register", full=False)
    page.get_by_role("button", name="Create account").click()
    expect(page.get_by_text("Confirm your contact details")).to_be_visible()
    shot(page, "04-user-dashboard-verify")

    # Verify OTPs (read from the development outbox)
    page.get_by_placeholder("6-digit code").first.fill(otp_for(EMAIL, "EMAIL"))
    page.get_by_role("button", name="Verify").first.click()
    expect(page.get_by_text("Verify your email address")).to_have_count(0)
    page.get_by_placeholder("6-digit code").first.fill(otp_for(PHONE, "SMS"))
    page.get_by_role("button", name="Verify").first.click()
    try:
        expect(page.get_by_text("Email address and mobile number verified")).to_be_visible()
    except AssertionError:
        page.screenshot(path=str(SHOTS / "fail.png")); print(errors); raise

    # Application
    page.get_by_role("link", name="Start the application").click()
    page.get_by_role("button", name="Start the application").click()
    expect(page.get_by_text("Personal details").first).to_be_visible()
    # Try submitting with nothing filled in beyond the prefill -> errors incl. introducer
    page.get_by_role("button", name="Submit application").click()
    expect(page.get_by_text("Introduced by Sri is mandatory")).to_be_visible()
    shot(page, "05-application-validation", full=False)

    f = page.get_by_label
    f("Father's name").fill("Sri Venkata Rao Kottapalli")
    f(re.compile(r"^Address\*?$")).fill("12, Mint Street")
    f("Address (line 2)").fill("Sowcarpet")
    f("City/Town/Village").fill("Chennai")
    f("State").fill("Tamil Nadu")
    f("Pincode").fill("600079")
    f("Date of birth").fill("1986-08-21")
    f("Blood group").select_option("B+")
    f("Aadhaar card no.").fill("")
    f(re.compile(r"^Phone\*?$")).fill("04425330821")
    f("Centre X No.").fill("25")
    f("WhatsApp/Facebook").fill(PHONE)
    f("Family surname").fill("Kottapalli")
    f("Gothram").fill("Kasyapa")
    f("Natchathiram").fill("Rohini")
    f(re.compile(r"^Occupation\*?$")).fill("Textile merchant")
    f("Occupation address", exact=True).fill("45, Godown Street, Chennai 600001")
    f("Native place address").fill("Kavali, Nellore District, Andhra Pradesh")
    f("Introduced by Sri").fill("Sri Subramanyam Chetty")
    f("Introducer phone no.").fill("9840012345")
    f("Introducer reg. no.").fill("1001")
    page.get_by_role("button", name="Save draft").click()
    expect(page.get_by_text("Draft saved")).to_be_visible()

    uploads = {"Recent passport-size photograph": "photo.jpg", "Additional passport-size photograph (1)": "photo.jpg",
               "Additional passport-size photograph (2)": "photo.jpg", "Identity proof": "id.pdf", "Signature of applicant": "sign.png"}
    for label, fname in uploads.items():
        page.get_by_label(f"Upload {label}").set_input_files(f"{Path(__file__).resolve().parent}/{fname}")
        page.wait_for_timeout(700)
    f(re.compile(r"^Place\*?$")).fill("Chennai")
    page.get_by_label("I confirm the declaration").check()
    shot(page, "06-application-filled")
    page.get_by_role("button", name="Submit application").click()
    expect(page.get_by_role("dialog")).to_be_visible()
    page.get_by_role("dialog").get_by_role("button", name="Submit").click()
    expect(page.get_by_text("Waiting for verification")).to_be_visible()
    shot(page, "07-application-submitted", full=False)

    # Non-member cannot see the full directory
    page.goto(BASE + "/dashboard/directory")
    expect(page.get_by_text("Full member details become visible")).to_be_visible()

    # Admin: request corrections
    admin = browser.new_context(viewport={"width": 1366, "height": 900}).new_page()
    admin.on("pageerror", lambda e: errors.append(f"admin pageerror: {e}"))
    admin.goto(BASE + "/login")
    admin.get_by_label("Email address or mobile number").fill("office.admin@example.org")
    admin.get_by_label("Password").fill("Office-admin-2026")
    admin.get_by_role("button", name="Log in").click()
    expect(admin.get_by_text("Membership administration")).to_be_visible()
    shot(admin, "08-admin-dashboard")
    admin.get_by_role("link", name="Pending", exact=True).first.click()
    admin.get_by_text("Ramesh Kumar Kottapalli").first.click()
    expect(admin.get_by_text("belongs to Sri Subramanyam Chetty")).to_be_visible()
    shot(admin, "09-admin-review")
    admin.get_by_role("button", name="Request corrections").click()
    admin.get_by_label("Corrections needed").fill("Please add your Aadhaar card number; it is missing from the form.")
    admin.get_by_role("button", name="Send correction request").click()
    expect(admin.get_by_text("Waiting for the applicant's corrections")).to_be_visible()

    # User corrects and resubmits
    page.goto(BASE + "/dashboard/application")
    expect(page.get_by_text("The office has asked for these corrections")).to_be_visible()
    page.get_by_label("Aadhaar card no.").fill("2345 6789 0124")
    shot(page, "10-correction", full=False)
    page.get_by_role("button", name="Resubmit application").click()
    if page.get_by_text("Enter a valid 12-digit Aadhaar number").count():
        # pick a checksum-valid number
        page.get_by_label("Aadhaar card no.").fill("499118665246")
        page.get_by_role("button", name="Resubmit application").click()
    page.get_by_role("dialog").get_by_role("button", name="Resubmit").click()
    expect(page.get_by_text("Waiting for verification")).to_be_visible()

    # Admin approves
    admin.reload()
    admin.get_by_role("button", name="Approve").first.click()
    admin.get_by_label("Verified by").fill("P. Lakshmi Narayana")
    admin.get_by_label("Rec. No.").fill("R-2026-118")
    admin.get_by_label("Chairman").fill("V. Ramakrishna")
    admin.get_by_label("Secretary").fill("S. Balaji")
    admin.get_by_label("President").fill("N. Sathyanarayana")
    shot(admin, "11-approve-dialog", full=False)
    admin.get_by_role("button", name="Approve and assign number").click()
    expect(admin.get_by_text("Approved. Membership no. 1007")).to_be_visible()

    # Member sees number, directory and requests edit
    page.goto(BASE + "/dashboard")
    expect(page.get_by_text("1007").first).to_be_visible()
    shot(page, "12-member-dashboard")
    page.goto(BASE + "/dashboard/directory")
    expect(page.get_by_text("Sri Subramanyam Chetty")).to_be_visible()
    shot(page, "13-member-directory")
    page.goto(BASE + "/dashboard/membership")
    page.get_by_label("What needs to change, and why?").fill("I have moved my shop; the occupation address needs updating.")
    page.get_by_role("button", name="Request permission to edit").click()
    expect(page.get_by_text("Request sent").first).to_be_visible()
    shot(page, "14-my-membership")

    # Admin approves edit request
    admin.goto(BASE + "/admin/edit-requests")
    admin.get_by_role("button", name=re.compile("Approve for")).click()
    admin.get_by_role("dialog").get_by_role("button", name="Approve").click()
    admin.wait_for_timeout(600)

    # Member edits within window
    page.goto(BASE + "/dashboard/membership/edit")
    page.get_by_label("Occupation address", exact=True).fill("8, Narayana Mudali Street, Chennai 600079")
    page.get_by_role("button", name="Save changes").click()
    page.get_by_role("dialog").get_by_role("button", name="Save changes").click()
    expect(page.get_by_text("Your changes are saved")).to_be_visible()
    shot(page, "15-member-edit", full=False)
    page.goto(BASE + "/dashboard/membership/print")
    expect(page.get_by_text("Life Membership Record")).to_be_visible()
    shot(page, "16-print-record")

    # Admin pages
    admin.goto(BASE + "/admin/members")
    shot(admin, "17-admin-members")
    admin.goto(BASE + "/admin/members/new")
    shot(admin, "18-add-existing-member", full=False)
    admin.goto(BASE + "/admin/reports")
    shot(admin, "19-reports")
    admin.goto(BASE + "/admin/notifications?tab=deliveries")
    shot(admin, "20-deliveries", full=False)
    admin.goto(BASE + "/super-admin")
    expect(admin.get_by_text("Membership administration")).to_be_visible()  # admin is redirected away

    # Super admin
    sa = browser.new_context(viewport={"width": 1366, "height": 900}).new_page()
    sa.on("pageerror", lambda e: errors.append(f"super pageerror: {e}"))
    sa.goto(BASE + "/login")
    sa.get_by_label("Email address or mobile number").fill("super@example.org")
    sa.get_by_label("Password").fill("Sabha-admin-2026")
    sa.get_by_role("button", name="Log in").click()
    expect(sa.get_by_text("Recent admin activity")).to_be_visible()
    shot(sa, "21-super-dashboard")
    sa.goto(BASE + "/super-admin/admins")
    shot(sa, "22-admin-management", full=False)
    sa.goto(BASE + "/super-admin/activity")
    shot(sa, "23-audit", full=False)
    sa.goto(BASE + "/super-admin/settings")
    shot(sa, "24-settings")

    # Mobile
    m = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2).new_page()
    m.goto(BASE + "/")
    shot(m, "25-mobile-home", full=False)

    browser.close()

print("ERRORS:", errors if errors else "none")
sys.exit(1 if errors else 0)
