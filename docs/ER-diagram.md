# Database ER diagram

MySQL 8, `utf8mb4`. All timestamps are stored as UTC `DATETIME` and returned by the API as ISO-8601 with a `Z` offset.
Schema source of truth: `backend/app/models/entities.py`; migration: `backend/alembic/versions/0001_initial_schema.py`.

```mermaid
erDiagram
    users ||--o| member_profiles : "may own (user_id, unique, nullable)"
    users ||--o{ member_applications : submits
    users ||--o{ notifications : receives
    users ||--o{ notification_deliveries : "email/SMS to"
    users ||--o{ audit_logs : performs
    users ||--o{ otp_codes : has
    users ||--o{ refresh_tokens : has
    member_applications ||--o{ application_documents : has
    member_applications ||--o{ application_history : has
    member_applications ||--o| members : "approved into (application_id unique)"
    member_profiles ||--|| members : "one membership per profile"
    member_profiles ||--o{ application_documents : has
    members ||--o{ edit_requests : requests
    edit_requests ||--o| edit_permissions : grants
    members ||--o{ edit_permissions : has
    members ||--o{ member_change_history : logs
    edit_permissions ||--o{ member_change_history : "changes made under"
    notifications ||--o{ notification_deliveries : "sent as"

    users {
        bigint id PK
        varchar email UK
        varchar phone UK
        varchar password_hash "Argon2id"
        varchar role "USER|ADMIN|SUPER_ADMIN"
        bool is_active
        datetime email_verified_at
        datetime phone_verified_at
        datetime password_changed_at
        bigint created_by_id FK
    }
    member_applications {
        bigint id PK
        varchar application_number UK "APP-2026-000001"
        bigint user_id FK
        varchar status "DRAFT|PENDING|CORRECTION_REQUIRED|RESUBMITTED|APPROVED|REJECTED"
        varchar full_name
        varchar father_name
        text aadhaar_number "Fernet-encrypted"
        varchar aadhaar_hash "HMAC, duplicate detection"
        varchar introducer_name
        varchar introducer_phone
        varchar introducer_reg_no
        bool declaration_accepted
        text correction_notes
        text rejection_reason
        bigint reviewed_by_id FK
    }
    member_profiles {
        bigint id PK
        bigint user_id FK,UK "NULL for manually-added members"
        varchar full_name
        varchar father_name
        text aadhaar_number "encrypted"
        bool show_contact_in_directory
        bool show_address_in_directory
    }
    members {
        bigint id PK
        bigint member_profile_id FK,UK
        varchar membership_number UK "VARCHAR(50)"
        varchar status "ACTIVE|INACTIVE"
        varchar source "ONLINE_APPLICATION|MANUAL_ENTRY"
        bigint application_id FK,UK
        varchar verified_by "office use"
        varchar receipt_number "office use"
        varchar committee_chairman "office use"
    }
    membership_sequences {
        bigint id PK
        varchar name UK "default | year | application-YYYY"
        bigint next_value "row-locked during approval"
    }
    application_documents {
        bigint id PK
        bigint application_id FK
        bigint member_profile_id FK
        varchar doc_type "PHOTO|ID_PROOF|ADDITIONAL_PHOTO_1|ADDITIONAL_PHOTO_2|APPLICANT_SIGNATURE|INTRODUCER_SIGNATURE"
        varchar storage_key UK "private storage path"
        varchar sha256
        bool is_current
    }
    application_history {
        bigint id PK
        bigint application_id FK
        varchar action
        varchar from_status
        varchar to_status
        text note
        bigint actor_id FK
    }
    notifications {
        bigint id PK
        bigint user_id FK
        varchar event
        varchar title
        text message
        bool is_read
    }
    notification_deliveries {
        bigint id PK
        bigint notification_id FK
        varchar channel "EMAIL|SMS"
        varchar status "PENDING|SENDING|SENT|FAILED"
        int attempts
        text last_error
        datetime next_attempt_at
        bool is_sensitive "OTP/reset – body hidden"
    }
    edit_requests {
        bigint id PK
        bigint member_id FK
        text reason
        varchar status "PENDING|APPROVED|REJECTED"
        bigint reviewed_by_id FK
    }
    edit_permissions {
        bigint id PK
        bigint edit_request_id FK,UK
        bigint member_id FK
        datetime starts_at
        datetime expires_at "starts_at + 24h"
        datetime revoked_at
        datetime expiry_notified_at
    }
    member_change_history {
        bigint id PK
        bigint member_id FK
        bigint edit_permission_id FK
        varchar source "MEMBER_EDIT|ADMIN_EDIT"
        varchar field_name
        text old_value "sensitive values masked"
        text new_value
    }
    audit_logs {
        bigint id PK
        bigint actor_id FK
        varchar actor_role
        varchar action
        varchar entity_type
        varchar entity_id
        json details
        varchar ip_address
    }
    otp_codes {
        bigint id PK
        bigint user_id FK
        varchar purpose "EMAIL_VERIFY|PHONE_VERIFY|PASSWORD_RESET"
        varchar code_hash "SHA-256"
        datetime expires_at
        int attempts
    }
    refresh_tokens {
        bigint id PK
        bigint user_id FK
        varchar jti UK
        datetime revoked_at
        varchar replaced_by_jti "rotation chain"
    }
```

## Key integrity rules

| Rule | How it is enforced |
|---|---|
| Unique email / phone / application no. / membership no. | `UNIQUE` constraints |
| One official membership per profile | `members.member_profile_id UNIQUE` |
| One membership per login account | `member_profiles.user_id UNIQUE` |
| Every approved application has a member record | Created in the same transaction; `members.application_id UNIQUE` |
| Manually added members need no account | `member_profiles.user_id` nullable |
| No duplicate membership numbers under concurrency | Sequence row `SELECT … FOR UPDATE` + unique constraint; tested with 8 parallel approvals |
| Membership number only on approval | Generated inside `approve_application`; pending applications have no member row |
