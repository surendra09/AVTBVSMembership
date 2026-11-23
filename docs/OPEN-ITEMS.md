# Organisation-specific information still needed

Everything below is configurable. Nothing here was invented: where the PDFs did not provide the information, a neutral default is used and flagged.

## 1. Membership number format (required before go-live)

The brief says real membership-number examples would be supplied, but none were attached. Until they are:

* `MEMBERSHIP_NUMBER_TEMPLATE={seq}` produces plain sequential numbers (`1007`, `1008`, …).
* The template supports `{seq}`, `{year}`, `{yy}`, `{prefix}` and Python format specs, so most real formats can be set without code changes, e.g. `{seq:05d}` gives `01007`, `{prefix}{seq}` with `MEMBERSHIP_NUMBER_PREFIX=AVT/` gives `AVT/1007`, and `{seq}/{year}` gives `1007/2026`.
* Set `MEMBERSHIP_SEQUENCE_PER_YEAR=true` if numbering restarts each year.
* After paper members are entered, a Super Admin sets the next sequence value in **System settings**. Numbers already used by paper members are skipped automatically.

If the real format has rules a template can't express (check digits, branch codes chosen per member), `format_membership_number()` in `backend/app/services/numbering.py` is the single place to change.

## 2. Logo quality

The tree emblem was extracted from the photograph of the 2025-2026 annual report cover (`docs/reference-cover.jpg`) and cut out from its background. It is faithful but it comes from a photographed print, so edges are soft at large sizes. For crisp print and email use, supply the original artwork (vector or a scan of at least 1500 px) and replace:

* `frontend/public/brand/emblem.png`, `emblem-400.png`, `emblem-192.png`, `emblem-64.png`, `emblem-32.png`
* `backend/app/templates/email/emblem.png`

Neither PDF contains a stand-alone "AVTBVS" wordmark. The abbreviation is set in the site's display typeface beside the emblem; the official form itself uses "AVTBV Sabha" in its office section.

## 3. Contact details differ between the two PDFs

| | Registration form | Annual report cover |
|---|---|---|
| Address | 28, (Old No. 4), Kalappachari Street, Park Town, Chennai - 600 003 | No. 4, Kalappachari Street, Park Town, Chennai - 600 003 |
| Phone | 044-25330821 | 044-43515921 |
| Email | avtbvsabha.1955@gmail.com | avtbvsabhaacc@gmail.com |

The form's details are used by default. Change `ORG_ADDRESS`, `ORG_PHONE` and `ORG_EMAIL` in `.env` if the cover's are current.

## 4. Decisions to confirm with the committee

* **Aadhaar** is optional, but validated (12 digits + checksum) when entered, because the paper form doesn't mark any field as mandatory. Admins see duplicate-Aadhaar warnings.
* **Introducer signature** upload is optional (`REQUIRE_INTRODUCER_SIGNATURE=false`) because the form's "Sig." box is signed in person. Set it to `true` to require an image.
* **Introducer must already be in the online register**: off by default (`INTRODUCER_MUST_BE_REGISTERED=false`), because many introducers are paper members not yet entered. Admins always see whether the number matches a member.
* **"S/o" in the declaration** is reproduced exactly as printed. If women may apply, the committee may want "S/o / D/o / W/o"; that is a one-line change in `DeclarationText` (frontend) and `PrintableRecord`.
* **What members see in the directory**: name, father's name, photo, membership no., city/state, blood group, family surname, gothram, natchathiram, occupation and native place. Contact details and address are shown only where the member consented. Date of birth, Aadhaar, documents, signatures, introducer and office data are never shown.
* **SMS provider**: MSG91 and Twilio are implemented. Indian SMS needs a DLT-registered sender and templates; the texts are in `backend/app/services/notification_templates.py`.
