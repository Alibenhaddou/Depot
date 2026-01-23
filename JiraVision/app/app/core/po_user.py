from typing import Any, Dict, Optional

from app.core import po_project_store


def upsert_user_from_jira(me: Dict[str, Any], *, now: Optional[int] = None) -> Dict[str, Any]:
    account_id = me.get("accountId")
    if not account_id:
        raise ValueError("accountId manquant")

    display_name = me.get("displayName")
    email = me.get("emailAddress")

    return po_project_store.upsert_user(
        account_id,
        display_name=display_name,
        email=email,
        now=now,
    )
