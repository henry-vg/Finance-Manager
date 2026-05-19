openapi_tags = [
    {
        "name": "HealthZ",
        "description": (
            "Health check endpoints that verify the application process is running, "
            "responsive, and ready to receive traffic. Includes liveness checks "
            "for process "
            "verification and readiness checks for dependency validation."
        ),
    },
    {
        "name": "Currency",
        "description": (
            "Currency catalog endpoints for configuring supported currencies "
            "and their stable metadata such as code, symbol, and decimal "
            "precision."
        ),
    },
    {
        "name": "LedgerAccount",
        "description": (
            "Ledger account management endpoints for creating, retrieving, "
            "listing, updating, and deleting financial containers such as bank "
            "accounts, wallets, and credit cards. Responses include normalized "
            "UTC audit timestamps."
        ),
    },
    {
        "name": "Tag",
        "description": (
            "Tag management endpoints for creating, retrieving, listing, "
            "updating, and deleting tags persisted in Postgres. Responses "
            "include normalized UTC audit timestamps."
        ),
    },
    {
        "name": "User",
        "description": (
            "User management endpoints for creating, retrieving, updating, "
            "and deleting users persisted in Postgres. Responses never expose "
            "password data and timestamps are returned in normalized UTC format."
        ),
    },
]
