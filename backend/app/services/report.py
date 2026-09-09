"""PDF case report via reportlab."""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet


def build_case_report(case: dict, features: dict, risk: dict, patterns: dict, entities_hit: list[dict], txs: list[dict], timeline: list[dict], guidance: list | None = None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=14 * mm, bottomMargin=14 * mm)
    styles = getSampleStyleSheet()
    H1, H2, P = styles["Heading1"], styles["Heading2"], styles["BodyText"]
    SMALL = styles["Normal"].__class__("Small", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.grey)
    story = []
    story.append(Paragraph("BLOCKCHAIN CYBERCRIME — INVESTIGATION CASE REPORT", H1))
    story.append(Paragraph(f"Case {case.get('case_id')} · {case.get('network','ethereum')} · Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} (prototype, system-assisted)", SMALL))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#111827")))
    story.append(Paragraph("1. Case & Suspect", H2))
    rows = [
        ["Case ID", case.get("case_id", "")],
        ["Suspect wallet", case.get("wallet_address", "")],
        ["Network", case.get("network", "")],
        ["Victim ref", case.get("victim_ref", "")],
        ["Fraud amount (INR)", str(case.get("fraud_amount_inr", ""))],
        ["Incident date", case.get("incident_date", "")],
        ["Incident time (GMT/UTC)", case.get("incident_time_gmt", "")],
        ["Suspect IP (off-chain intel)", case.get("suspect_ip", "") or "— not recorded"],
        ["12-digit ref (masked)", case.get("ref_12digit", "") or "— not recorded"],
        ["Subject name (off-chain)", case.get("suspect_name", "") or "— not recorded"],
        ["Subject alias", case.get("suspect_alias", "") or "—"],
        ["Subject phone (masked)", case.get("suspect_phone", "") or "— not recorded"],
        ["Subject email (masked)", case.get("suspect_email", "") or "— not recorded"],
        ["Subject account note", case.get("suspect_account", "") or "—"],
        ["Reference tx", case.get("tx_hash", "")],
        ["Notes", case.get("notes", "")],
    ]
    t = Table(rows, colWidths=[42 * mm, 130 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2FF")),
                           ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                           ("FONTSIZE", (0, 0), (-1, -1), 9), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t)
    story.append(Paragraph("2. Executive Summary (system-generated observations, investigator to verify)", H2))
    story.append(Paragraph(
        f"Risk score <b>{risk['score']}/100 ({risk['level']})</b>. "
        f"Analysed {len(txs)} transactions; {features.get('unique_counterparties', 0)} unique counterparties. "
        f"Key indicators: {'; '.join(risk.get('reasons', [])[:5]) or 'none'}. "
        "These are risk indicators, not proof of wrongdoing.", P))
    story.append(Paragraph(
        "Off-chain identifiers (IP address, 12-digit reference) are investigator-provided and CANNOT be "
        "derived from blockchain data, which is pseudonymous. IP attribution must be corroborated via "
        "VASP/ISP records through lawful process.", SMALL))
    story.append(Paragraph("3. Risk Breakdown (prototype weights — configurable assumptions)", H2))
    rrows = [["Indicator", "Points"]] + [[k, str(v)] for k, v in risk.get("indicators", {}).items()]
    rt = Table(rrows, colWidths=[120 * mm, 52 * mm])
    rt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(rt)
    story.append(Paragraph("Clue Study Guide — what each clue means and the next step", H2))
    for g in (guidance or risk.get("guidance", []) or []):
        story.append(Paragraph(
            f"• <b>{g.get('title','')} (+{g.get('points',0)})</b> — observed: {g.get('detail','') or 'pattern present'}. "
            f"Why it matters: {g.get('why','')} Next: {g.get('next','')}", P))
    if not (guidance or risk.get("guidance")):
        story.append(Paragraph("No high-weight clues triggered in this window.", P))
    story.append(Paragraph("4. Possible Connected Services (possible connection — verify with VASP / official records)", H2))
    if entities_hit:
        for e in entities_hit:
            story.append(Paragraph(f"• <b>{e.get('label')}</b> ({e.get('category')}) — {e.get('address','')[:20]}… · {e.get('confidence_note','')}", P))
    else:
        story.append(Paragraph("No known entity match within analysed hops.", P))
    story.append(Paragraph("5. Fund-flow Timeline", H2))
    for ev in timeline[:20]:
        story.append(Paragraph(f"• {ev.get('timestamp','')} — {ev.get('text','')}", P))
    story.append(Paragraph("6. Evidence — Transaction Hashes", H2))
    for x in txs[:30]:
        story.append(Paragraph(f"<font size=8>{x.get('tx_hash','')} · {x.get('from_address','')[:12]}… → {x.get('to_address','')[:12]}… · {x.get('amount')} {x.get('token','')}</font>", P))
    story.append(Spacer(1, 6))
    story.append(Paragraph("7. Investigator Notes & Next Steps", H2))
    story.append(Paragraph("□ Verify entity attribution with exchange/VASP via official channel &nbsp; □ Corroborate with victim statement / FIR &nbsp; □ Preserve raw API responses (hash-chained evidence store in future version)", P))
    story.append(Paragraph("Trace actions (lawful process): □ 1930 helpline / cybercrime.gov.in complaint linkage &nbsp; □ VASP KYC + login-IP request for flagged addresses &nbsp; □ ISP subscriber request for corroborated IPs &nbsp; □ Bank/UPI trail for linked accounts. Blockchain analysis alone cannot name the person behind a wallet.", P))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(Paragraph("Disclaimer: prototype for SIH 26183 demo. Scores use heuristic + mock/seed data where live APIs are unavailable. Do not treat as definitive attribution.", SMALL))
    doc.build(story)
    return buf.getvalue()
