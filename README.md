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

## TODOs

- Fazer teste end-to-end (no diretório tests/e2e/)

## Notes

### Collection `Users`

```jsonc
{
    "_id": "ObjectId",
    "email": "String",
    "password_hash": "String",
    "created_at": "Date",
    "preferences": {
        "default_currency": "String",
        "language": "String",
        "theme": "String"
    }
}
```

### Collection `Banks`

```jsonc
{
    "_id": "ObjectId",
    "user_id": "ObjectId",
    "name": "String",
    "type": "String", // e.g. "digital", "traditional"
    "branch": "String",
    "account_number": "String",
    "created_at": "Date"
}
```

### Collection `Cards`

```jsonc
{
    "_id": "ObjectId",
    "bank_id": "ObjectId",
    "user_id": "ObjectId",
    "name": "String",
    "type": "String", // e.g. "credit", "debit", "prepaid"
    "limit": "Number",
    "closing_day": "Number", // 1 to 31
    "due_day": "Number", // 1 to 31
    "created_at": "Date"
}
```

### Collection `Transactions`

```jsonc
{
    "_id": "ObjectId",
    "user_id": "ObjectId",
    "bank_id": "ObjectId",
    "card_id": "ObjectId",
    "type": "String", // e.g. "expense", "income", "transfer"
    "category": "String",
    "description": "String",
    "amount": "Number",
    "currency": "String",
    "transaction_date": "Date",
    "created_at": "Date",
    "notes": "String"
}
```

### Collection `Categories`

```jsonc
{
    "_id": "ObjectId",
    "user_id": "ObjectId",
    "name": "String",
    "icon": "String",
    "color": "String" // HEX format, e.g. "#ff6600"
}
```