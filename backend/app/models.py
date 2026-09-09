from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(32), default="investigator")  # investigator | admin
    created_at = Column(DateTime, default=datetime.utcnow)


class Case(Base):
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(64), unique=True, index=True, nullable=False)
    wallet_address = Column(String(128), index=True, nullable=False)
    network = Column(String(32), default="ethereum")
    victim_ref = Column(String(128), default="")
    fraud_amount_inr = Column(Float, default=0)
    incident_date = Column(String(32), default="")
    incident_time_gmt = Column(String(40), default="")  # ISO-8601 UTC, e.g. 2026-09-05T10:31:00+00:00
    suspect_ip = Column(String(64), default="")  # investigator-provided OFF-CHAIN intel (not chain-derived)
    ref_12digit = Column(String(16), default="")  # 12-digit reference, checksum-validated
    suspect_name = Column(String(128), default="")  # off-chain subject profile (lawful sources only)
    suspect_alias = Column(String(128), default="")
    suspect_phone = Column(String(32), default="")
    suspect_email = Column(String(128), default="")
    suspect_account = Column(String(128), default="")  # bank / UPI / other account note
    tx_hash = Column(String(128), default="")
    notes = Column(Text, default="")
    status = Column(String(32), default="open")
    created_by = Column(String(64), default="investigator")
    created_at = Column(DateTime, default=datetime.utcnow)
    risks = relationship("RiskScore", back_populates="case", cascade="all, delete-orphan")


class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(128), unique=True, index=True, nullable=False)
    network = Column(String(32), default="ethereum")
    first_seen = Column(String(32), default="")
    last_seen = Column(String(32), default="")
    tx_count = Column(Integer, default=0)
    extra = Column(JSON, default=dict)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    case_ref = Column(String(64), index=True, default="")
    tx_hash = Column(String(128), index=True, nullable=False)
    from_address = Column(String(128), index=True, nullable=False)
    to_address = Column(String(128), index=True, nullable=False)
    amount = Column(Float, default=0)
    token = Column(String(32), default="ETH")
    timestamp = Column(String(32), default="")
    network = Column(String(32), default="ethereum")
    ts_epoch = Column(Float, default=0)


class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(128), unique=True, index=True, nullable=False)
    label = Column(String(128), nullable=False)
    category = Column(String(64), default="exchange")  # exchange | mixer | flagged | service
    confidence_note = Column(String(256), default="")
    source = Column(String(64), default="seed")


class RiskScore(Base):
    __tablename__ = "risk_scores"
    id = Column(Integer, primary_key=True, index=True)
    case_ref = Column(String(64), ForeignKey("cases.case_id"), index=True, nullable=False)
    wallet = Column(String(128), index=True, nullable=False)
    score = Column(Integer, default=0)
    risk_level = Column(String(16), default="LOW")
    reasons = Column(JSON, default=list)
    indicators = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    case = relationship("Case", back_populates="risks")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String(64), default="")
    action = Column(String(128), default="")
    detail = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
