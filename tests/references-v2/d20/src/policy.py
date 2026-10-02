import re


def check_password(pw: str, username: str, common: set) -> list:
    out = []
    if len(pw) < 12:
        out.append("too_short")
    if len(pw) > 128:
        out.append("too_long")
    if pw.lower() in common:
        out.append("common")
    if len(username) >= 3 and username.lower() in pw.lower():
        out.append("has_username")
    if re.search(r"(.)\1{3,}", pw):
        out.append("repeated")
    return out
