from dataclasses import dataclass


@dataclass
class Record:
    id: int
    name: str
    level: str
    category: str
    income_limit: int
    benefit: str
    deadline: str
    apply_at: str
    source_url: str
    verified: bool = False

    @classmethod
    def from_dict(cls, data):
        """Build a Record from a dict (e.g. one row of records.json)."""
        return cls(
            id=int(data["id"]),
            name=data["name"],
            level=data["level"],
            category=data["category"],
            income_limit=int(data["income_limit"]),
            benefit=data["benefit"],
            deadline=data["deadline"],
            apply_at=data["apply_at"],
            source_url=data["source_url"],
            verified=bool(data.get("verified", False)),
        )