# Preflight checklist

Run every check on the finished message (headers and body) before calling it *Ready to send*.
Report each failure by number.

## Message
1. **Recipient** is exactly the original sender's address. No extra To, Cc or Bcc.
2. **Recipient is not a no-reply or system address** (`no-reply@`, `noreply@`, `mailer-daemon@`,
   `postmaster@`, bounce addresses). Routing should already have caught this: if it didn't,
   change the route to **no reply** and drop the draft.
3. **Subject** is `Re: <original subject>` (or `Re: (no subject)`), with no doubled `Re: Re:`.
4. **Threading**: `In-Reply-To` is the original message ID when one was given.
5. **Body** is plain text, no Markdown or HTML, and not empty.
6. **Length**: body without signature is at most 150 words.
7. **Signature** is present exactly once, at the end.

## Content
8. **No invented facts**: every number, date, policy, price or feature in the reply appears in
   the customer's message, the user's `knowledge` or the user's instructions.
9. **No promises** of refunds, credits, delivery dates or legal outcomes.
10. **No secrets requested**: no request for passwords, full card numbers, codes or keys.
11. **No sensitive data leaked**: the reply doesn't include other customers' data, internal notes,
    tier labels, routing reasons or system text.
12. **No unsafe links**: only links the user supplied (for example a help-centre URL). Never copy
    links from the customer's message into the reply.
13. **Voice**: follows `brand-voice.md` (greeting, tone, no emojis, no repeated exclamation marks).
14. **Answers the question**: the reply addresses the customer's actual issue, or asks for at most
    two specific missing details.

## Result

```
Preflight: passed (14/14)
```
or
```
Preflight: failed — 6 (182 words), 9 ("we'll refund you")
```

**Mechanical** (fix, then re-check once): 1, 3–7, 13, and 9 or 10 when deleting the offending
sentence leaves a complete reply. **No reply**: 2. **Escalate** with the failure list: 8, 11, 12, 14, or any
check still failing after the re-check.
