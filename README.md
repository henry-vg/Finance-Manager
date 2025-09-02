# Finance Manager

The backend system of a financial manager.


## How To Run It Locally

```bash
git clone git@github.com:henry-vg/Finance-Manager.git
cd Finance-Manager/
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Insert .env content here" > .env
python3 main.py
```


## Folder Structure

```
Finance-Manager
├── logs                             # Application logs and rotated log files
├── src                              # Main source code of the application
│   ├── adapters                     # Implementations of ports (input/output)
│   │   ├── input                    # Driving adapters (entry points, e.g. HTTP, CLI, schedulers)
│   │   └── output                   # Driven adapters (exit points, e.g. DB, external APIs, queues)
│   ├── core                         # Business core (framework-agnostic)
│   │   ├── domain                   # Domain models, entities, value objects, domain logic
│   │   ├── ports                    # Abstract interfaces (contracts) the core depends on
│   │   │   ├── input                # Input ports (use case interfaces, driven by outside)
│   │   │   └── output               # Output ports (interfaces for external systems)
│   │   └── usecases                 # Application services / orchestration of domain logic
│   └── infra                        # Infrastructure & composition root (config, server startup, DI)
├── tests                            # Automated tests
│   ├── integration                  # Integration tests (real components working together)
│   ├── unit                         # Unit tests (isolated functions/classes)
├── main.py                          # Thin entrypoint (delegates to infra.server.create_app())
└── settings.json                    # Application settings and configuration (JSON)

```