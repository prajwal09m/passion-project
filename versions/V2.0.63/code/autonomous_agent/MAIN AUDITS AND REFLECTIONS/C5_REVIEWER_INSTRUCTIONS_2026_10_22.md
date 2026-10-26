# C5 Reviewer Instructions - Key Generation and Authorization

**Date**: 2026-10-22
**Purpose**: Instructions for the Campaign 5 reviewer to generate their HMAC key and sign the authorization record

## Your Role

You have been engaged as the **Campaign 5 reviewer** for authorization purposes. Your role is:

1. **Hold a distinct HMAC key** - Separate from the owner's key
2. **Sign the authorization record** - When the final authorization is created
3. **Verify the authorization content** - Before signing

**Note**: Statistical review has already been completed via AI review (accepted by the owner with risk acknowledgment). You do not need to perform a statistical review.

## Step 1: Generate Your HMAC Key

Generate a cryptographically random 32-byte hex key using one of these methods:

### Method A: Python (Recommended)
```python
import secrets
key = secrets.token_hex(32)  # 32 bytes = 64 hex characters
print(key)
```

### Method B: OpenSSL (if available)
```bash
openssl rand -hex 32
```

### Method C: Password Manager
Use your password manager's "random password" or "random token" feature:
- Length: 64 characters
- Character set: Hexadecimal (0-9, a-f)
- Copy the result

## Step 2: Choose Your Actor ID

Choose a simple identifier for yourself, such as:
- Your initials
- Your name
- A short handle

**Example**: `JSMITH` or `REVIEWER1`

**Important**: Your actor ID must be **different** from the owner's actor ID (`PMED`).

## Step 3: Provide Your Information to the Owner

Send the following to the project owner (PMED):

1. **Your Actor ID** - e.g., `JSMITH`
2. **Your HMAC Key** - e.g., `a1b2c3d4e5f6...` (64 hex characters)

**Important Security Notes**:
- Send the key securely (in person, encrypted message, or secure channel)
- Do not share the key publicly or commit it to git
- Keep the key secret - only the owner needs it for environment variable setup
- If the key is lost or compromised, it must be regenerated

## Step 4: Sign the Authorization Record

When the owner creates the final Campaign 5 authorization record:

1. **Review the record** - Verify it contains:
   - Correct protocol digest
   - Correct scope and parameters
   - Your actor ID listed as reviewer
   - All digests match your understanding

2. **Sign the record** - The owner will provide instructions for signing with your HMAC key

3. **Return the signature** - Provide your signature to the owner

## Step 5: Set Environment Variables (Owner's Responsibility)

The owner will set these environment variables before Campaign 5 launch:

```bash
C5_OWNER_ACTOR_ID=PMED
C5_OWNER_HMAC_KEY=<owner's 64-char hex key>
C5_REVIEWER_ACTOR_ID=<your actor ID>
C5_REVIEWER_HMAC_KEY=<your 64-char hex key>
```

## Summary

Your responsibilities:
1. ✅ Generate a 32-byte hex HMAC key
2. ✅ Choose a distinct actor ID
3. ✅ Provide both to the owner securely
4. ⏳ Review and sign the authorization record when created
5. ⏳ Keep your key secret

**Statistical review**: Already completed via AI review - no action needed from you on that front.

## Questions?

If you have questions about:
- Key generation methods
- Security best practices
- Authorization record content
- Signing process

Contact the project owner (PMED).

**Date**: 2026-10-22
**Evidence path**: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/C5_REVIEWER_INSTRUCTIONS_2026_10_22.md`
