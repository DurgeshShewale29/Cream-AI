from dataclasses import dataclass


@dataclass
class Record:
    id: int
    scheme_name: str
    department: str
    eligible_category: str
    income_limit: int | None
    benefit: str
    source_url: str
    verified: bool = False

    @classmethod
    def from_dict(cls, data):
        """Build a Record from a dict (e.g. one entry of records.json)."""
        limit = data.get("income_limit")
        return cls(
            id=int(data["id"]),
            scheme_name=data["scheme_name"],
            department=data["department"],
            eligible_category=data["eligible_category"],
            income_limit=int(limit) if limit is not None else None,
            benefit=data["benefit"],
            source_url=data["source_url"],
            verified=bool(data.get("verified", False)),
        )