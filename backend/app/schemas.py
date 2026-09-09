import ipaddress
import re
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional

# ---- Verhoeff checksum tables (Aadhaar-style 12-digit validation) ----
_VD = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_VP = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 7, 2, 5],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def verhoeff_ok(num: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(num)):
        c = _VD[c][_VP[i % 8][int(ch)]]
    return c == 0


def mask12(s: str) -> str:
    """Mask a 12-digit reference for display: XXXX-XXXX-1234."""
    s = (s or "").strip()
    return ("XXXX-XXXX-" + s[-4:]) if len(s) == 12 and s.isdigit() else s


def mask_phone(s: str) -> str:
    s = re.sub(r"\D", "", s or "")
    return (s[:2] + "XXXXXX" + s[-2:]) if len(s) >= 10 else s


def mask_email(s: str) -> str:
    s = (s or "").strip()
    if "@" not in s:
        return s
    local, dom = s.split("@", 1)
    return (local[:1] + "***@" + dom) if local else s


def derive_gmt(incident_date: str, incident_time_gmt: str) -> str:
    """Fall back to incident_date at 00:00 UTC when no exact GMT time given."""
    if incident_time_gmt:
        return incident_time_gmt
    try:
        d = datetime.strptime((incident_date or "").strip()[:10], "%Y-%m-%d")
        return d.replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
    except ValueError:
        return ""


class CaseIntel(BaseModel):
    """Off-chain + time intel. IP / 12-digit ref CANNOT come from the blockchain
    (chain data is pseudonymous) — the investigator records them here from
    complaint records, VASP responses, or other lawful sources."""
    incident_time_gmt: str = Field("", examples=["2026-09-05T10:31:00+00:00"])
    suspect_ip: str = Field("", examples=["103.21.244.10"])
    ref_12digit: str = Field("", examples=["999999990017"])
    # Subject profile — OFF-CHAIN, lawful sources only (FIR, VASP reply, bank).
    # Never derived from the blockchain, which cannot identify persons.
    suspect_name: str = ""
    suspect_alias: str = ""
    suspect_phone: str = ""
    suspect_email: str = ""
    suspect_account: str = ""  # bank / UPI / other account note

    @field_validator("incident_time_gmt", mode="before")
    @classmethod
    def _gmt(cls, v):
        if v in (None, ""):
            return ""
        s = str(v).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            raise ValueError("Use ISO GMT, e.g. 2026-09-05T10:31:00+00:00")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)  # naive input is treated as GMT
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat(timespec="seconds")

    @field_validator("suspect_ip", mode="before")
    @classmethod
    def _ip(cls, v):
        if v in (None, ""):
            return ""
        try:
            return str(ipaddress.ip_address(str(v).strip()))
        except ValueError:
            raise ValueError("Invalid IPv4/IPv6 address")

    @field_validator("ref_12digit", mode="before")
    @classmethod
    def _ref(cls, v):
        if v in (None, ""):
            return ""
        s = re.sub(r"\D", "", str(v))
        if len(s) != 12:
            raise ValueError("Reference must be exactly 12 digits")
        if not verhoeff_ok(s):
            raise ValueError("12-digit checksum failed — please check the number")
        return s

    @field_validator("suspect_phone", mode="before")
    @classmethod
    def _phone(cls, v):
        if v in (None, ""):
            return ""
        s = re.sub(r"\D", "", str(v))
        if not (10 <= len(s) <= 15):
            raise ValueError("Phone must hold 10–15 digits")
        return s

    @field_validator("suspect_email", mode="before")
    @classmethod
    def _email(cls, v):
        if v in (None, ""):
            return ""
        s = str(v).strip()
        if "@" not in s or "." not in s.split("@")[-1]:
            raise ValueError("Invalid email address")
        return s


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class CaseCreate(CaseIntel):
    case_id: str = Field(..., examples=["CYB-2026-001"])
    wallet_address: str
    network: str = "ethereum"
    victim_ref: str = ""
    fraud_amount_inr: float = 0
    incident_date: str = ""
    tx_hash: str = ""
    notes: str = ""


class CaseOut(CaseIntel):
    case_id: str
    wallet_address: str
    network: str
    victim_ref: str = ""
    fraud_amount_inr: float = 0
    incident_date: str = ""
    tx_hash: str = ""
    notes: str = ""
    status: str = "open"
    created_by: str = ""
    created_at: str = ""

    model_config = ConfigDict(from_attributes=True)


class AnalyzeIn(CaseIntel):
    wallet_address: str
    network: str = "ethereum"
    case_id: Optional[str] = None
    victim_ref: str = ""
    fraud_amount_inr: float = 0
    incident_date: str = ""
    tx_hash: str = ""
    notes: str = ""
