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
        "name": "User",
        "description": (
            "User management endpoints for creating, retrieving, updating, "
            "and deleting users persisted in Postgres. Responses never expose "
            "password data and timestamps are returned in normalized UTC format."
        ),
    },
]
