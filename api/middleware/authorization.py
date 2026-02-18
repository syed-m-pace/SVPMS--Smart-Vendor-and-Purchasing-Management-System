from fastapi import Depends, HTTPException, status

from api.middleware.auth import get_current_user

ROLE_HIERARCHY = {
    "admin": 100,
    "cfo": 90,
    "finance_head": 80,
    "finance": 70,
    "procurement_lead": 60,
    "procurement": 50,
    "manager": 40,
    "vendor": 10,
}


def require_roles(*allowed_roles: str):
    """
    FastAPI dependency factory for role-based access control.

    Usage:
        @router.get("/budgets")
        async def list_budgets(
            current_user: dict = Depends(get_current_user),
            _auth: None = Depends(require_roles("finance", "admin")),
        ):
    """
    async def check_role(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "INSUFFICIENT_PERMISSIONS",
                        "message": (
                            f"Role '{current_user['role']}' cannot perform this action. "
                            f"Required: {allowed_roles}"
                        ),
                    }
                },
            )
        return None

    return check_role


def check_self_approval(approver_id: str, requester_id: str):
    """Prevent self-approval on purchase requests."""
    if str(approver_id) == str(requester_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "APPROVAL_SELF_APPROVE_001",
                    "message": "You cannot approve your own purchase request",
                }
            },
        )


def check_department_scope(current_user: dict, entity_department_id: str):
    """For 'manager' role: verify entity belongs to their department."""
    if current_user["role"] == "manager":
        if str(current_user.get("department_id")) != str(entity_department_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "INSUFFICIENT_PERMISSIONS",
                        "message": "You can only access entities within your department",
                    }
                },
            )
