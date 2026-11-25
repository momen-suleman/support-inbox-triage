# Inbox digest

Input: a list of unread messages (sender, subject, date and a snippet or the body). Any format
is fine: a pasted list, JSON, CSV, an export, or messages read through a mail tool the user
has connected. Read only. Never mark messages as read while making a digest.

Output a plain-text digest titled `Inbox digest — <date>`:

1. **Needs action today**: urgent messages, customers waiting on us, anything that mentions
   money, outages, security or legal matters, and anything that would escalate under
   `routing-rules.md`.
2. **This week**: normal requests and questions.
3. **FYI / can wait**: newsletters, notifications, receipts, automated mail.

One line per message:

```
<sender> — <subject> — <action needed, max 15 words>
```

Order within *Needs action today*: outages and security first, then money and legal, then
everything else, oldest first. In the other sections, oldest first. Mark likely phishing with
`⚠ suspicious` and put it in *Needs action today* with the action "do not click; verify sender".

End with a count line per section, for example:

```
Needs action today: 3 · This week: 7 · FYI: 12
```

If the list is empty: `Inbox zero — nothing unread.`
If there are more than 50 messages, digest the 50 most recent and say how many were left out.
