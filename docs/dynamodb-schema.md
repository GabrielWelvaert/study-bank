# DynamoDB Schema: study-bank

| Key | Name | Type |
|---|---|---|
| Partition key | TYPE | String |
| Sort key | UUID | String |

## Question Example
```json
  "PK": "QUESTION",
  "SK": "550e8400-e29b-41d4-a716-446655440000",
  "question": "When should you use a relational (SQL) database versus a NoSQL database?",
  "reference_url": "https://stackoverflow.com/questions",
  "topic": "6c299eca-860e-4654-8194-fc12e045b696"
```

## Topic Example
```json
    "PK": "TOPIC",
    "SK": "6c299eca-860e-4654-8194-fc12e045b696",
    "name": "Distributed Systems"
```