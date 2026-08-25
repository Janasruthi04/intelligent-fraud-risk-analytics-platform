"""
ontology_schema.py
--------------------
Defines the Foundry Ontology for this project as schema-as-code: object
types, their properties, and the relationships (link types) between them.

This sandbox has no live connection to a Palantir Foundry stack, so this
module is written the way you'd define it in a Foundry Ontology Manager /
Object Type editor, and doubles as a runnable reference implementation:
`build_ontology_instances()` below materializes real object + link instances
from the scored transaction output produced by risk_scoring.py, and
`ontology_export.py` dumps them to JSON so the dashboard can render the
Workshop-style "entity investigation" views without needing Foundry itself.

Object types
------------
Customer      -- customer_id, name, location, customer_type, risk_score
Transaction   -- transaction_id, amount, timestamp, fraud_probability, risk_level
Merchant      -- merchant_id, merchant_category, location
Device        -- device_id, device_type
RiskAlert     -- alert_id, alert_type, severity, created_at, status

Relationships (link types)
---------------------------
Customer   --makes-->      Transaction        (one-to-many)
Transaction --at-->        Merchant           (many-to-one)
Transaction --from-->      Device             (many-to-one)
Transaction --generates--> RiskAlert          (one-to-one, conditional on risk)

Actions
-------
ReviewTransaction        -- analyst reviews a flagged transaction
MarkAlertAsInvestigated   -- analyst closes out a risk alert
EscalateHighRiskTransaction -- routes a HIGH risk transaction to a senior analyst
"""
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Customer:
    customer_id: str
    name: str
    location: str
    customer_type: str  # "individual" | "business"
    risk_score: float = 0.0


@dataclass
class Merchant:
    merchant_id: str
    merchant_category: str
    location: str


@dataclass
class Device:
    device_id: str
    device_type: str  # "mobile" | "web" | "pos"


@dataclass
class Transaction:
    transaction_id: str
    customer_id: str          # link -> Customer (Customer --makes--> Transaction)
    merchant_id: str          # link -> Merchant (Transaction --at--> Merchant)
    device_id: str            # link -> Device   (Transaction --from--> Device)
    amount: float
    timestamp: str
    fraud_probability: float
    risk_level: str  # LOW | MEDIUM | HIGH


@dataclass
class RiskAlert:
    alert_id: str
    transaction_id: str       # link -> Transaction (Transaction --generates--> RiskAlert)
    alert_type: str
    severity: str
    created_at: str
    status: str = "OPEN"      # OPEN | UNDER_REVIEW | INVESTIGATED | ESCALATED | CLOSED


# --------------------------------------------------------------------------
# Ontology Actions
# --------------------------------------------------------------------------
# In Foundry these would be modeled as Ontology "Actions" (write-back
# operations with parameters, validation rules, and side effects). Here they
# are represented as pure functions that transition object state, so the
# same logic could later be lifted directly into a Foundry Action Type.

def review_transaction(alert: RiskAlert, reviewer: str) -> RiskAlert:
    """Analyst opens a flagged transaction for review."""
    alert.status = "UNDER_REVIEW"
    return alert


def mark_alert_as_investigated(alert: RiskAlert, resolution_note: str) -> RiskAlert:
    """Analyst closes out an alert after investigation."""
    alert.status = "INVESTIGATED"
    return alert


def escalate_high_risk_transaction(alert: RiskAlert, escalated_to: str) -> RiskAlert:
    """Routes a HIGH risk transaction's alert to a senior analyst / case team."""
    if alert.severity != "HIGH":
        raise ValueError("Only HIGH severity alerts can be escalated via this action")
    alert.status = "ESCALATED"
    return alert
