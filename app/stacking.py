"""Scholarship stacking rules and highest-value preference order for ScholarSetu.

MahaDBT pays only one tuition/fee scholarship per student according to the applicant's
preference order, and NSP/AICTE schemes cannot be double-claimed alongside MahaDBT fee
scholarships. Hostel subsistence allowance (Dr. Panjabrao Deshmukh) is a separate
add-on that can be combined with an eligible domestic MahaDBT fee scholarship.
"""

from __future__ import annotations

from app.records import load_records

# Known DTE Maharashtra / NSP scheme rules keyed by a stable substring of source_url.
SCHEME_RULES = {
    "rajarshi-chhatrapati-shahu-maharaj": {
        "short_name": "Rajarshi Chhatrapati Shahu Maharaj Fee Scholarship",
        "portal": "MahaDBT",
        "slot": "primary_scholarship",
        "categories": {"EBC", "EWS", "SEBC"},
        "gender": "any",
        "requires_disability": False,
        "is_abroad": False,
        "aliases": ("rajarshi", "shahu maharaj", "ebc fee", "maharashtra fee scholarship"),
    },
    "dr-panjabrao-deshmukh-vastigruh-nirvah-bhatta-yojna": {
        "short_name": "Dr. Panjabrao Deshmukh Hostel Allowance",
        "portal": "MahaDBT",
        "slot": "hostel_allowance",
        "categories": {"EBC", "EWS", "SEBC"},
        "gender": "any",
        "requires_disability": False,
        "is_abroad": False,
        "aliases": ("panjabrao", "punjabrao", "vastigruh", "nirvah bhatta", "hostel subsistence"),
    },
    "merit-cum-means": {
        "short_name": "Merit-Cum-Means Scholarship (Minority)",
        "portal": "MahaDBT / NSP",
        "slot": "primary_scholarship",
        "categories": {"Minority"},
        "gender": "any",
        "requires_disability": False,
        "is_abroad": False,
        "aliases": ("merit-cum-means", "merit cum means"),
    },
    "foreign-scholarship": {
        "short_name": "Foreign Higher Education Scholarship (EWS)",
        "portal": "DTE Maharashtra (Abroad)",
        "slot": "abroad_scholarship",
        "categories": {"EWS", "Open"},
        "gender": "any",
        "requires_disability": False,
        "is_abroad": True,
        "aliases": ("foreign scholarship", "higher education abroad"),
    },
    "scholarship-for-students-of-minority-communities": {
        "short_name": "State Minority Higher Professional Scholarship (Part-1)",
        "portal": "MahaDBT",
        "slot": "primary_scholarship",
        "categories": {"Minority"},
        "gender": "any",
        "requires_disability": False,
        "is_abroad": False,
        "aliases": ("minority students of the state", "part - 1", "state minority scholarship"),
    },
    "scholarship-for-top-class-education-for-students-with-disabilities": {
        "short_name": "Top Class Education for Students with Disabilities",
        "portal": "NSP (Central)",
        "slot": "primary_scholarship",
        "categories": {"EBC", "EWS", "SEBC", "OBC", "SC", "ST", "Minority", "Open"},
        "gender": "any",
        "requires_disability": True,
        "is_abroad": False,
        "aliases": ("top class education for students with disabilities", "students with disabilities"),
    },
    "pragati-scholarship-scheme": {
        "short_name": "AICTE Pragati Scholarship for Girls",
        "portal": "NSP (AICTE)",
        "slot": "primary_scholarship",
        "categories": {"EBC", "EWS", "SEBC", "OBC", "SC", "ST", "Minority", "Open"},
        "gender": "Female",
        "requires_disability": False,
        "is_abroad": False,
        "aliases": ("pragati",),
    },
}

ALL_CATEGORIES = ("EBC", "EWS", "SEBC", "Minority", "OBC", "SC", "ST", "Open")
VALID_GENDERS = ("Female", "Male")
VALID_CITY_TIERS = ("metro", "non_metro")


def _rule_for(record: dict) -> tuple[str, dict]:
    url = (record.get("source_url") or "").lower()
    for key, rule in SCHEME_RULES.items():
        if key in url:
            return key, rule
    return "unknown", {
        "short_name": record.get("scheme_name", "Unknown Scheme"),
        "portal": "MahaDBT / NSP",
        "slot": "primary_scholarship",
        "categories": set(ALL_CATEGORIES),
        "gender": "any",
        "requires_disability": False,
        "is_abroad": False,
        "aliases": (),
    }


def estimate_annual_value(
    record: dict,
    annual_fee: int = 100_000,
    gender: str = "Female",
    is_hosteller: bool = True,
    city_tier: str = "metro",
) -> tuple[int, str]:
    """Estimate annual rupee benefit for a scheme given student parameters."""
    key, _ = _rule_for(record)
    if key == "rajarshi-chhatrapati-shahu-maharaj":
        if gender == "Female":
            return int(annual_fee), "100% of tuition & exam fees (Female)"
        return round(annual_fee * 0.5), "50% of tuition & exam fees (Male)"
    if key == "dr-panjabrao-deshmukh-vastigruh-nirvah-bhatta-yojna":
        if city_tier == "metro":
            return 60_000, "Rs 60,000/yr metro city (Mumbai/Pune/Thane/Nagpur); Rs 38,000-51,000 elsewhere"
        return 38_000, "Rs 38,000/yr non-metro base (up to Rs 60,000 in metro cities)"
    if key == "merit-cum-means":
        if is_hosteller:
            return 30_000, "Rs 30,000/yr (hosteller); Rs 25,000/yr (day scholar)"
        return 25_000, "Rs 25,000/yr (day scholar); Rs 30,000/yr (hosteller)"
    if key == "foreign-scholarship":
        return int(annual_fee), "Full overseas university tuition + health insurance (foreign study only)"
    if key == "scholarship-for-students-of-minority-communities":
        value = min(int(annual_fee), 50_000)
        return value, "Actual annual tuition & exam fee or Rs 50,000, whichever is less"
    if key == "scholarship-for-top-class-education-for-students-with-disabilities":
        value = min(int(annual_fee), 190_000)
        return value, "Actual admission & academic fees up to Rs 1,90,000/yr"
    if key == "pragati-scholarship-scheme":
        return 50_000, "Rs 50,000/yr lump sum (AICTE)"
    return 0, str(record.get("benefit") or "Check official portal")


def filter_eligible_records(
    records: list[dict],
    category: str = "EWS",
    gender: str = "Female",
    family_income: int | None = 400_000,
    has_disability: bool = False,
    is_hosteller: bool = True,
    include_abroad: bool = False,
) -> list[dict]:
    """Return records from records.json matching a student's profile."""
    eligible = []
    for record in records:
        _, rule = _rule_for(record)
        if rule["is_abroad"] and not include_abroad:
            continue
        if rule["slot"] == "hostel_allowance" and not is_hosteller:
            continue
        if rule["gender"] != "any" and rule["gender"] != gender:
            continue
        if rule["requires_disability"] and not has_disability:
            continue
        if category not in rule["categories"]:
            continue
        limit = record.get("income_limit")
        if family_income is not None and limit is not None and family_income > limit:
            continue
        eligible.append(record)
    return eligible


def detect_mentioned_records(
    answer: str = "",
    citations: list[dict] | None = None,
    steps: list[dict] | None = None,
    records: list[dict] | None = None,
) -> list[dict]:
    """Identify schemes from records.json referenced in a /ask or /agent response."""
    records = records if records is not None else load_records()
    citations = citations or []
    steps = steps or []

    cited_urls = {(c.get("source") or "").strip().lower() for c in citations}
    combined_chunks = [answer or ""]
    for c in citations:
        combined_chunks.append(str(c.get("title") or ""))
        combined_chunks.append(str(c.get("source") or ""))
    for step in steps:
        combined_chunks.append(str(step.get("input") or ""))
        combined_chunks.append(str(step.get("observation") or ""))
    haystack = " ".join(combined_chunks).lower()

    matched = []
    seen_ids = set()
    for record in records:
        rec_url = (record.get("source_url") or "").strip().lower()
        rec_name = (record.get("scheme_name") or "").strip().lower()
        key, rule = _rule_for(record)
        hit = (
            (rec_url and rec_url in cited_urls)
            or (rec_url and rec_url in haystack)
            or (rec_name and rec_name in haystack)
            or any(alias in haystack for alias in rule["aliases"])
            or (key != "unknown" and key in haystack)
        )
        if hit and record["id"] not in seen_ids:
            seen_ids.add(record["id"])
            matched.append(record)
    return matched


def analyze_stacking(
    selected_records: list[dict],
    annual_fee: int = 100_000,
    gender: str = "Female",
    is_hosteller: bool = True,
    city_tier: str = "metro",
) -> dict:
    """Mark schemes that cannot be taken together and rank them by highest annual value.

    Rules enforced:
    1. Primary tuition/fee scholarships (MahaDBT & NSP/AICTE) are mutually exclusive:
       MahaDBT pays only one scheme by applicant preference, and NSP/AICTE schemes
       cannot be double-claimed with MahaDBT fee scholarships.
    2. Hostel subsistence allowance (Dr. Panjabrao Deshmukh) can stack as an add-on
       alongside a domestic MahaDBT tuition/fee scholarship (not with abroad study).
    3. Foreign study scholarship cannot stack with domestic schemes.
    """
    if annual_fee < 0:
        raise ValueError("annual_fee must be 0 or greater.")
    if gender not in VALID_GENDERS:
        raise ValueError(f"gender must be one of {VALID_GENDERS}.")
    if city_tier not in VALID_CITY_TIERS:
        raise ValueError(f"city_tier must be one of {VALID_CITY_TIERS}.")

    if not selected_records:
        return {
            "has_conflict": False,
            "conflict_count": 0,
            "warning": None,
            "rows": [],
            "preference_order": [],
            "stackable_addons": [],
            "max_combined_value": 0,
            "recommendation": "Select or match at least one scheme to inspect stacking rules.",
        }

    enriched = []
    for record in selected_records:
        key, rule = _rule_for(record)
        est_value, value_note = estimate_annual_value(
            record,
            annual_fee=annual_fee,
            gender=gender,
            is_hosteller=is_hosteller,
            city_tier=city_tier,
        )
        enriched.append({
            "id": record["id"],
            "scheme_name": record["scheme_name"],
            "short_name": rule["short_name"],
            "portal": rule["portal"],
            "slot": rule["slot"],
            "eligible_category": record["eligible_category"],
            "income_limit": record.get("income_limit"),
            "benefit": record["benefit"],
            "estimated_value": est_value,
            "value_note": value_note,
            "source_url": record["source_url"],
            "rule_key": key,
        })

    # Mutually exclusive tuition/fee pool (domestic primary + abroad scholarships).
    exclusive_pool = [item for item in enriched if item["slot"] in ("primary_scholarship", "abroad_scholarship")]
    hostel_pool = [item for item in enriched if item["slot"] == "hostel_allowance"]

    # Sort exclusive pool highest estimated annual value first; prefer MahaDBT on exact ties, then name.
    exclusive_pool.sort(
        key=lambda x: (-x["estimated_value"], 0 if "MahaDBT" in x["portal"] else 1, x["scheme_name"])
    )
    hostel_pool.sort(key=lambda x: (-x["estimated_value"], x["scheme_name"]))

    has_conflict = len(exclusive_pool) >= 2
    has_domestic_primary = any(item["slot"] == "primary_scholarship" for item in exclusive_pool)
    has_abroad_only = bool(exclusive_pool) and not has_domestic_primary

    rows = []
    preference_order = []

    for rank, item in enumerate(exclusive_pool, start=1):
        others = [o["short_name"] for o in exclusive_pool if o["id"] != item["id"]]
        if has_conflict:
            mahadbt_involved = any("MahaDBT" in o["portal"] for o in exclusive_pool)
            if mahadbt_involved:
                if rank == 1:
                    status = "Cannot stack — MahaDBT pays 1 by preference (Recommended Pref #1)"
                else:
                    status = f"Cannot stack — MahaDBT pays 1 by preference (Backup Pref #{rank})"
            else:
                if rank == 1:
                    status = "Cannot stack — single-scholarship rule (Recommended Pref #1)"
                else:
                    status = f"Cannot stack — single-scholarship rule (Backup Pref #{rank})"
            can_stack = False
        else:
            status = "Primary scholarship (no competing fee scheme selected)"
            can_stack = True

        row = {
            "preference_rank": rank if has_conflict else 1,
            "preference_label": f"Pref #{rank}" if has_conflict else "Primary #1",
            "id": item["id"],
            "scheme_name": item["scheme_name"],
            "short_name": item["short_name"],
            "portal": item["portal"],
            "eligible_category": item["eligible_category"],
            "income_limit": item["income_limit"],
            "estimated_value": item["estimated_value"],
            "value_note": item["value_note"],
            "benefit": item["benefit"],
            "can_stack": can_stack,
            "stacking_status": status,
            "conflicts_with": others,
            "source_url": item["source_url"],
        }
        rows.append(row)
        preference_order.append({
            "rank": rank,
            "id": item["id"],
            "scheme_name": item["scheme_name"],
            "short_name": item["short_name"],
            "portal": item["portal"],
            "estimated_value": item["estimated_value"],
            "value_note": item["value_note"],
        })

    stackable_addons = []
    for item in hostel_pool:
        if has_abroad_only:
            conflicts = [o["short_name"] for o in exclusive_pool]
            can_stack = False
            status = "Cannot stack — domestic hostel allowance does not apply to foreign study"
            has_conflict = True
        else:
            conflicts = []
            can_stack = True
            status = "Can stack — Hostel add-on (separate from MahaDBT tuition fee scheme)"
            stackable_addons.append({
                "id": item["id"],
                "scheme_name": item["scheme_name"],
                "short_name": item["short_name"],
                "portal": item["portal"],
                "estimated_value": item["estimated_value"],
                "value_note": item["value_note"],
            })

        rows.append({
            "preference_rank": None,
            "preference_label": "Add-on (Stackable)" if can_stack else "Incompatible",
            "id": item["id"],
            "scheme_name": item["scheme_name"],
            "short_name": item["short_name"],
            "portal": item["portal"],
            "eligible_category": item["eligible_category"],
            "income_limit": item["income_limit"],
            "estimated_value": item["estimated_value"],
            "value_note": item["value_note"],
            "benefit": item["benefit"],
            "can_stack": can_stack,
            "stacking_status": status,
            "conflicts_with": conflicts,
            "source_url": item["source_url"],
        })

    top_primary_value = exclusive_pool[0]["estimated_value"] if exclusive_pool else 0
    addon_value = sum(a["estimated_value"] for a in stackable_addons)
    max_combined_value = top_primary_value + addon_value

    warning = None
    if has_conflict:
        conflict_names = ", ".join(item["short_name"] for item in exclusive_pool)
        warning = (
            "Stacking Warning: these fee/tuition schemes cannot be taken together "
            f"({conflict_names}). MahaDBT pays only ONE scheme based on applicant preference, "
            "and NSP/AICTE scholarships cannot be double-claimed with MahaDBT tuition schemes."
        )

    if preference_order:
        order_str = " -> ".join(
            f"#{p['rank']} {p['short_name']} (est. Rs {p['estimated_value']:,}/yr)"
            for p in preference_order
        )
        recommendation = f"Suggested highest-value preference order: {order_str}."
        if stackable_addons:
            addons_str = ", ".join(
                f"{a['short_name']} (+Rs {a['estimated_value']:,}/yr)" for a in stackable_addons
            )
            recommendation += f" Can also stack with: {addons_str} (total est. Rs {max_combined_value:,}/yr)."
    elif stackable_addons:
        addons_str = ", ".join(
            f"{a['short_name']} (est. Rs {a['estimated_value']:,}/yr)" for a in stackable_addons
        )
        recommendation = f"Hostel allowance available: {addons_str}."
    else:
        recommendation = "Check eligibility rules on the official portals."

    return {
        "has_conflict": has_conflict,
        "conflict_count": len(exclusive_pool) if len(exclusive_pool) >= 2 else 0,
        "warning": warning,
        "rows": rows,
        "preference_order": preference_order,
        "stackable_addons": stackable_addons,
        "max_combined_value": max_combined_value,
        "recommendation": recommendation,
    }
