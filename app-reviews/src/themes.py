"""Transparent keyword rules that tag a review with problem themes (version 2). A review can have several themes.

Version 1 was scored on validation sample A; version 2 was rewritten after error analysis on A and is scored once on a
fresh sample B (see the notebook). 'Praise' requires a 4 or 5 star rating, because positive words inside a 1 or 2 star
review ("great app, but...") are not praise.
"""
import re

import pandas as pd

THEMES = {
    "Login & authentication": [
        r"\blog ?(in|on|ging|ged)\b", r"\bsign ?(in|on)\b", r"\bpassword", r"\bpasskey", r"verif(y|ication|ied)", r"\bface ?id\b", r"biometric",
        r"authenticat", r"\b(2fa|two[- ]factor|otp)\b", r"\bpin\b", r"locked out", r"\bget(ting)? into my account", r"\bcredentials\b",
        r"\blog(ged)? ?out\b", r"\bcode\b.{0,30}\b(text|email|sms|send|sent|receive)", r"\bbirthday\b", r"fingerprint", r"blocks? my access"],
    "Bugs, crashes & slowness": [
        r"\bbugg?y\b", r"\bbugs?\b", r"\bglitch", r"\bcrash", r"\bslow\b", r"\bloading\b", r"won'?t load", r"doesn'?t load", r"not loading",
        r"\bwhite screen\b", r"\bblank (screen|page)\b", r"completely blank", r"technical (issue|problem|difficult)", r"server (issue|error|problem)",
        r"\berror\b", r"something went wrong", r"\b(app|it|this|site|website|page|screen|button|feature|deposit|check|login|scan)\b.{0,25}"
        r"(doesn'?t|does not|isn'?t|is not|won'?t|will not|not|no longer|stopped|never) (work|function|scan|load|show|display|open)", r"\bnot working\b",
        r"\bbroken\b", r"\bbloated\b", r"\blag(gy|s|ging)?\b", r"\bunresponsive\b", r"\b(app|site|server|system)s? (is |was |has been |keeps? |always |constantly )?(going )?down\b",
        r"\balways down\b", r"under maintenance", r"doing maintenance", r"\bfreez(es|ing|e)\b.{0,20}\b(app|screen|check|deposit)|\b(app|screen)\b.{0,20}\bfroze", r"\bfrozen screen",
        r"\bspins?( and spins?)?\b", r"\bspinning\b", r"\bstuck\b", r"\bfail(s|ed|ing|ure)\b", r"\bcan'?t (see|view|find|send|use|open|load|access|check|scan|pay)\b",
        r"takes? (forever|too long|so long)", r"taking a long time", r"\boptimi[sz]e", r"exceeds the screen", r"app (is )?breaking", r"\bserious issues?\b", r"\bso many issues\b",
        r"\bissues? (with|using) (the )?(app|deposit|login|log in)"],
    "Fraud, scams & security": [
        r"\bscammed\b", r"\bscammers? (got|took|stole|contact|call|text|use)", r"\bhack(ed|ers?|ing)\b", r"unauthori[sz]ed", r"phish", r"identity theft",
        r"\bstol(e|en)\b", r"\bsteal(s|ing)?\b", r"\btheft\b", r"\bfraud(ulent)? (alert|protection|department|claim|dispute|transactions?|charges?|activity|purchases?|team)",
        r"\breport(ed|ing)? (the )?fraud", r"\bobvious fraud\b", r"\bduring fraud\b", r"\bsecurity (feature|protection|breach|risk|alert)", r"\bprivacy\b",
        r"\bselling (your|my) (data|purchase)", r"\bspoof", r"\bimperson", r"\bprotect(ion|ed|s)? (my|your|our) (funds|money|account)",
        r"\bunknown (transactions?|charges?)", r"\bsomeone (broke|got|hacked|used|opened|stole)"],
    "Frozen, closed or restricted accounts": [
        r"\bfroz(e|en)\b.{0,12}\b(my|the|our|his|her|their)?\s?(account|accounts|funds|money|card|balance)", r"\b(account|acct|funds|money|card|balance)\b.{0,15}\b(is|was|got|been|were) (frozen|locked|suspended|restricted|limited|closed|flagged|banned|disabled)",
        r"\bunfreez", r"\bfroze (my|the|our)", r"\bfreez(e|ing|es) (my|the|our) (account|funds|money|card)", r"\bthey (closed|shut|locked|froze|suspended|banned|flagged|cancell?ed|terminated|limited|restricted)\b",
        r"\b(closed|shut (off|down)|banned|suspended|locked|restricted|flagged|terminated|deactivated) (my|the|our|your) (\w+ )?(account|card|acct)", r"\bflagged (my|the|our) account",
        r"\b(randomly|permanently|suddenly) (banned|suspended|locked|closed|shut)", r"\bbanned\b", r"\bsuspen(d|ded|sion)\b", r"\bbonk", r"\bviolat(ed|ion) (of )?(the |our )?(terms|policy|policies)",
        r"\bterms of (service|use)\b", r"\bon hold\b", r"\bholds? (up )?(your|my|the|our) (cash|money|funds|check|deposit)", r"\bhold onto your money\b",
        r"\b(\d+|two|six|several) holds?\b", r"\bheld (my|the) (money|funds|deposit)", r"\bwithh(e|o)ld", r"\bcancell?ed (my|our) (card|account)",
        r"\b(reduced|lowered|cut) (my )?(credit )?limit", r"\bunable to send money\b", r"\bkicked (me )?out\b", r"\bdeactivat"],
    "Customer service & support": [
        r"customer (service|support|care|cx)", r"\bsupport (team|staff|agent|rep|line|ticket|chat|center)", r"\bcontact(ed)? support\b", r"\bno support\b",
        r"\brepresentative", r"\bagents?\b", r"\breps?\b", r"\bchat ?bot\b", r"\bchat (assistance|system|support|window)", r"\b(ai|ia)\b.{0,25}(thing|chat|bot|loop|assistant|response|agent)",
        r"\b(cut|hung|hang|hand) ?(up|me off)\b", r"\bon hold for\b", r"\bwait(ed|ing)? (for )?(hours?|days?|weeks?|\d+ min)", r"\bphone (call|service|number|line)",
        r"\bcall(ed|ing)? (them|the|customer|support|in)", r"\bno (one|body) (to|can|will|would|answer|respond|help|call|listen)", r"\bunhelpful\b", r"\bno (available )?help\b",
        r"\bassist(ance|ant)?\b", r"\bnothing (they|we|that they) can do", r"\bresolv(e|ed|ing|ution)", r"\bcomplaint\b", r"\bdisputes?\b", r"\bsupervisor\b", r"\bstaff\b",
        r"\bhuman\b", r"\brude\b", r"\bdisrespect", r"\b(talked|spoke|speaking|speak) (to|with)\b", r"\bget (a hold|ahold) of\b", r"\bcare about\b", r"\bresponsib"],
    "Fees & charges": [
        r"\b(monthly|maintenance|overdraft|atm|wire|late|foreign|annual|service|transfer|nsf|hidden|extra|\$\d+)\s+fees?\b", r"\bfees?\b(?<!\bno fee)(?<!\bno fees)(?<!\bno extra fees)(?<!\bno hidden fees)(?<!\bwithout fees)", r"\boverdraft", r"\bnsf\b",
        r"\binterest rate", r"\bovercharg", r"\bcharged (me|us|a|an|\$|for|twice|again)", r"\bsurcharge", r"\bpenalt", r"\bapr\b", r"\bapy\b", r"\btook \$?\d", r"\$\d+(\.\d+)? (a|per) month",
        r"\$\d+(\.\d+)? to (transfer|send|withdraw|deposit)", r"\bpromo(tion)?\b", r"\bbonus\b", r"\bmatch(ing|ed)? \$?\d", r"\bnickle", r"\bcosts? (me )?\$?\d",
        r"\bnot truthful\b", r"\bsubscription\b", r"\bcredit builder\b"],
    "Payments, transfers & deposits": [
        r"\btransfers?\b(?! to (truist|chase|wells|citi))", r"\btransferr?(ed|ing)\b", r"\bdeposit(s|ed|ing)?\b", r"\bzelle\b", r"\bwire\b", r"\bpending\b", r"\bwithdraw",
        r"\b(make|made|making|send|sending|sent|pay|paying|schedule[d]?|process(ing|ed)?|submit(ted)?) (a |my |the |another )?(bill )?payments?\b", r"\bpayments? (didn'?t|did not|failed|pending|processing|declin|not|went|was|were|taking|has)",
        r"\bbill ?pay", r"\b(my|the|your|our) money\b", r"\bmoney\b.{0,25}(missing|gone|disappear|haven'?t|didn'?t|never|not (received|show|arrive))",
        r"\b(send|sending|sent|move|moving|get|getting) (money|funds|\$\d+)", r"\bgive me my\b", r"\bowe me\b", r"\brefund", r"\bon the way\b", r"\bdisbursement", r"\bcash ?out\b",
        r"\bcheck cashing\b", r"\bpay(ing)? (vendors|my bill|the bill|a bill)", r"\bhaven'?t (received|got)", r"\bprocess(ed|ing)\b", r"\b(unable|can'?t) to? (pay|send)"],
    "Updates, design & features": [
        r"\b(new|latest|recent|last|this|the|every|constant|constantly|forced|forcing|mandatory|too many|so many)\s+(app\s+)?updates?\b", r"\bupdates?\s+(broke|ruined|removed|erase|made|changed)", r"\bafter (the |a |this )?(recent |latest |last )?update",
        r"\bsince (the |a |this )?(recent |last |latest )?update", r"\bforc(e|ed|ing) (to |me to |us to )?(update|upgrade|download)", r"\bupdate (the |this )?app\b", r"\bredesign", r"\boverhaul",
        r"\blayout\b", r"\bhard to (find|navigate|read|see|use)", r"\bdifficult to (find|navigate|use|read)", r"\bcan'?t find\b", r"\bnot (very )?(intuitive|user[- ]friendly)", r"\bcluttered", r"\bads?\b", r"\badvertis",
        r"\bold (app|version|layout|design)", r"\bbring back\b", r"\bnew (version|look|app|design|format|ui|interface|build|online banking)\b", r"\bwidget", r"\bdark mode\b", r"\bsearch (function|bar|option)",
        r"\b(add|adding) (a|an|the|more|support for)\b", r"\bwould be nice\b", r"\boption (to|for)\b", r"\bremove (the|all|this)\b", r"\bget rid of\b", r"\bnotifications?\b", r"\balerts?\b",
        r"\bsounds?\b", r"\bpop ?ups?\b", r"\binterface\b", r"\b(ui|ux)\b", r"\bnavigat", r"\bgive me the option\b", r"\bwish\b", r"\bfeature requests?\b", r"\bpaperless\b", r"\bautofill"],
}
PRAISE = [r"\blove[sd]?\b", r"\bgreat(est)?\b", r"\beasy\b", r"\beasiest\b", r"\bawesome\b", r"\bexcellent", r"\bexcelente\b", r"\bconvenient", r"\bbest\b", r"\bfantastic\b", r"\bsmooth\b",
          r"\bhelpful\b", r"\bperfect\b", r"\bamazing\b", r"\bworks? (great|well|perfect|fine)", r"\buser[- ]friendly\b", r"\bgood\b", r"\bquality\b", r"\bencanta\b", r"\bgracias\b",
          r"\bthank", r"\bliked?\b", r"\brecommend", r"\btrust", r"\bquick", r"\bsimple\b", r"\bphenomenal\b", r"\bwonderful\b", r"\bfavorite\b|\bpreferido\b", r"\bnice\b", r"\bhappy\b",
          r"\bfriendly\b", r"\breliable\b", r"\bprofessional", r"\bfun\b", r"\bpleasure\b"]

_COMPILED = {k: [re.compile(p, re.I | re.S) for p in v] for k, v in {**THEMES, "Praise & ease of use": PRAISE}.items()}
THEME_NAMES = list(_COMPILED)


def tag(text, rating=None):
    """Set of theme names whose rules match the review text ('Praise' also needs rating >= 4 when a rating is given)."""
    found = {k for k, pats in _COMPILED.items() if any(p.search(text) for p in pats)}
    if rating is not None and rating <= 3:
        found.discard("Praise & ease of use")
    return found


def tag_frame(df, title_col="title", text_col="text", rating_col="rating"):
    """One boolean column per theme, from title + text (and rating for Praise)."""
    combined = (df[title_col].fillna("") + ". " + df[text_col].fillna("")).tolist()
    ratings = df[rating_col].tolist() if rating_col in df else [None] * len(df)
    tags = [tag(t, r) for t, r in zip(combined, ratings)]
    return pd.DataFrame({k: [k in s for s in tags] for k in THEME_NAMES}, index=df.index)
