#!/usr/bin/env python3
"""Deterministic checks on one email message (.eml or raw RFC 5322 text).

Usage:
    python check_email.py message.eml
    python check_email.py - < message.eml

Prints one JSON object: automated-mail signals for routing, security signals with
points (the table in references/inbox-inspection.md), links and attachments.
Standard library only. Reads the file; never opens links, never writes anything.
"""
import json
import re
import sys
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from html.parser import HTMLParser
from urllib.parse import urlparse

RISKY_EXT = (".exe", ".js", ".vbs", ".scr", ".iso", ".html", ".htm", ".bat", ".cmd",
             ".msi", ".jar", ".lnk", ".hta", ".docm", ".xlsm", ".pptm")
ODD_TLDS = {"xyz", "top", "click", "zip", "mov", "country", "kim", "gq", "tk", "ml", "cf",
            "ga", "work", "rest", "cam", "monster", "buzz", "ru", "su"}
URGENCY = re.compile(r"\b(final notice|within 24 ?h(ours)?|suspend(ed|sion)|immediately|"
                     r"urgent action|account (will be )?(locked|closed)|last warning)\b", re.I)
CRED_ASK = re.compile(r"\b(password|passcode|one[- ]time code|verification code|mfa code|"
                      r"card (number|details)|update (your )?(card|payment|billing)|gift ?cards?|"
                      r"bank (details|account)|wire transfer|log ?in to (verify|confirm))\b", re.I)
AI_INJECTION = re.compile(r"(ignore (all )?(previous|prior|above) instructions|you are now|"
                          r"system prompt|as an ai (assistant|model)|admin mode|"
                          r"forward (all|every) (customer )?e?mails?)", re.I)
AUTO_SUBJECT = re.compile(r"^(auto(matic)?[ -]?reply|out of (the )?office|undeliverable|"
                          r"delivery status notification|mail delivery failed|returned mail)", re.I)
SYSTEM_SENDER = re.compile(r"^(no-?reply|do-?not-?reply|mailer-daemon|postmaster|bounces?)([+.@-]|$)", re.I)
BRANDS = ("paypal", "microsoft", "apple", "google", "amazon", "netflix", "stripe", "dhl",
          "fedex", "ups", "docusign", "dropbox", "facebook", "instagram", "linkedin", "bank")
HOMOGLYPH = str.maketrans({"0": "o", "1": "l", "3": "e", "5": "s", "7": "t", "@": "a"})


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append(("".join(self._text).strip(), self._href))
            self._href = None


def domain_of(addr_or_url):
    s = (addr_or_url or "").strip().lower()
    if "@" in s and "://" not in s:
        return s.rsplit("@", 1)[1].strip(">")
    host = urlparse(s if "://" in s else "http://" + s).hostname or ""
    return host[4:] if host.startswith("www.") else host


def registrable(domain):
    parts = domain.split(".")
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in {"co", "com", "org", "net", "ac", "gov"}:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def lookalike(domain):
    """Reasons a domain looks like an imitation, or [] if none."""
    reasons = []
    if not domain:
        return reasons
    if "xn--" in domain:
        reasons.append("punycode")
    label = registrable(domain).split(".")[0]
    plain = label.translate(HOMOGLYPH)
    for b in BRANDS:
        if b in plain and b not in label:
            reasons.append(f"character swap imitating '{b}'")
        elif b in label and label != b:
            reasons.append(f"brand '{b}' inside a different domain")
    if domain.rsplit(".", 1)[-1] in ODD_TLDS:
        reasons.append("unusual top-level domain")
    if label.count("-") >= 2:
        reasons.append("many hyphens")
    if re.search(r"(verify|secure|login|account|update|billing|payment)", label):
        reasons.append("security or billing word in domain")
    # Weak hints (TLD, hyphens, words) only count together; plenty of real domains have one.
    weak = {"unusual top-level domain", "many hyphens", "security or billing word in domain"}
    strong = [r for r in reasons if r not in weak]
    return reasons if strong or len(reasons) >= 2 else []


def text_of(msg):
    plain, html = [], []
    for part in msg.walk():
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        ctype = part.get_content_type()
        try:
            content = part.get_content()
        except Exception:
            payload = part.get_payload(decode=True) or b""
            content = payload.decode("utf-8", "replace")
        if ctype == "text/plain":
            plain.append(content)
        elif ctype == "text/html":
            html.append(content)
    return "\n".join(plain), "\n".join(html)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "-"
    raw = sys.stdin.buffer.read() if src == "-" else open(src, "rb").read()
    msg = BytesParser(policy=policy.default).parsebytes(raw)

    from_name, from_addr = parseaddr(str(msg.get("From", "")))
    reply_to = parseaddr(str(msg.get("Reply-To", "")))[1]
    from_dom = domain_of(from_addr)
    subject = str(msg.get("Subject", ""))
    plain, html = text_of(msg)
    body = plain or re.sub(r"<[^>]+>", " ", html)

    # Automated mail (routing: "no reply")
    auto = []
    if str(msg.get("Auto-Submitted", "no")).lower() not in ("", "no"):
        auto.append(f"Auto-Submitted: {msg.get('Auto-Submitted')}")
    if msg.get("X-Autoreply") or msg.get("X-Autorespond"):
        auto.append("auto-reply header")
    prec = str(msg.get("Precedence", "")).lower()
    if prec in ("bulk", "list", "junk", "auto_reply"):
        auto.append(f"Precedence: {prec}")
    if msg.get("List-Unsubscribe"):
        auto.append("List-Unsubscribe (newsletter or notification)")
    if SYSTEM_SENDER.match(from_addr.split("@")[0] + "@"):
        auto.append(f"system sender {from_addr}")
    if AUTO_SUBJECT.match(subject.strip()):
        auto.append("auto-reply or bounce subject")

    signals = []

    def add(name, points, evidence):
        signals.append({"signal": name, "points": points, "evidence": evidence})

    auth = " ".join(str(v) for v in msg.get_all("Authentication-Results", []))
    for mech in ("spf", "dkim", "dmarc"):
        m = re.search(rf"\b{mech}=(\w+)", auth, re.I)
        if m and m.group(1).lower() in ("fail", "softfail", "permerror"):
            add(f"{mech.upper()} {m.group(1).lower()}", 20, f"Authentication-Results: {mech}={m.group(1)}")

    if from_name:
        name_l = from_name.lower()
        claimed = [b for b in BRANDS if b in name_l]
        name_words = [w for w in re.findall(r"[a-z]{4,}", name_l)]
        if claimed and not any(b in from_dom for b in claimed):
            add("Display name claims a brand the domain doesn't match", 25, f'"{from_name}" <{from_addr}>')
        elif name_words and any(w in registrable(from_dom) for w in name_words) and lookalike(from_dom):
            add("Display name claims a brand the domain doesn't match", 25, f'"{from_name}" <{from_addr}>')

    if reply_to and registrable(domain_of(reply_to)) != registrable(from_dom):
        add("Reply-To domain differs from From domain", 15, f"Reply-To: {reply_to}")

    links = []
    lp = LinkParser()
    try:
        lp.feed(html)
    except Exception:
        pass
    links += [{"text": t, "url": u} for t, u in lp.links if u]
    for t, u in re.findall(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", plain):
        links.append({"text": t, "url": u})
    for u in re.findall(r"https?://[^\s<>\")\]]+", plain):
        if not any(l["url"] == u for l in links):
            links.append({"text": "", "url": u})

    mismatched, lookalikes = [], set()
    for l in links:
        real = domain_of(l["url"])
        shown = re.search(r"([a-z0-9-]+\.)+[a-z]{2,}", l["text"].lower())
        if shown and registrable(domain_of(shown.group(0))) != registrable(real):
            mismatched.append(f'shows {shown.group(0)}, opens {real}')
        for r in lookalike(real):
            lookalikes.add(f"{real}: {r}")
    for r in lookalike(from_dom):
        lookalikes.add(f"{from_dom}: {r}")
    if mismatched:
        add("Link text shows one domain but opens another", 25, "; ".join(mismatched))
    if lookalikes:
        add("Lookalike or suspicious domain", 25, "; ".join(sorted(lookalikes)))

    if CRED_ASK.search(subject + " " + body):
        add("Asks for credentials, payment or bank details", 25, CRED_ASK.search(subject + " " + body).group(0))
    if URGENCY.search(subject + " " + body):
        add("Urgency or threat", 10, URGENCY.search(subject + " " + body).group(0))

    attachments = []
    for part in msg.iter_attachments():
        name = part.get_filename() or "(unnamed)"
        attachments.append({"name": name, "type": part.get_content_type()})
    risky = [a["name"] for a in attachments if a["name"].lower().endswith(RISKY_EXT)]
    if risky:
        add("Risky attachment", 25, ", ".join(risky))

    # Searches the raw HTML too, so text hidden with CSS is still caught.
    inj = AI_INJECTION.search(subject + " " + body + " " + html)
    if inj:
        add("Text aimed at an AI assistant", 25, inj.group(0))

    score = min(100, sum(s["points"] for s in signals))
    verdict = "clean" if score < 30 else "suspicious" if score < 60 else "likely malicious"
    if inj and verdict == "clean":
        verdict = "suspicious"  # instructions aimed at an AI are never clean
    print(json.dumps({
        "from": {"name": from_name, "address": from_addr},
        "reply_to": reply_to or None,
        "subject": subject,
        "message_id": str(msg.get("Message-ID", "")) or None,
        "automated": bool(auto),
        "automated_signals": auto,
        "security": {"score": score, "verdict": verdict, "suspicious": verdict != "clean", "signals": signals},
        "links": links,
        "attachments": attachments,
        "note": "Deterministic floor only. Add judgment for what the script can't see (context, tone, intent).",
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
