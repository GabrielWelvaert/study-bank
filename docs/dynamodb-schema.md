# DynamoDB Schema: study-bank

| Key | Purpose | Type |
|---|---|---|
| Partition key | Type | String |
| Sort key | UUID | String |

## Question
```json
  "PK": "QUESTION",
  "SK": "550e8400-e29b-41d4-a716-446655440000",
  "question": "What is linearizability?",
  "reference_url": "...",
  "topic": "6c299eca-860e-4654-8194-fc12e045b696"
```

## Topic
```json
    "PK": "TOPIC",
    "SK": "6c299eca-860e-4654-8194-fc12e045b696",
    "name": "Distributed Systems"
```