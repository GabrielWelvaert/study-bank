# Study Bank

Study Bank is a personal study tool for organizing technical questions by topic and emailing a randomized daily set for interview-style practice. It uses a local Streamlit application for question management and AWS serverless services for storage, scheduling, delivery, and monitoring.

## Architecture

<p align="center">
  <img src="./study-bank-architecture.png" width="100%" />
</p>

## Admin App

<p align="center">
  <img src="./study-bank-admin-portal.png" width="80%" />
</p>

# DynamoDB Schema

## Question
- Query on **PK** to retrieve all questions.
- GetItem on **(PK+SK)** to retrieve a specific question.
```json
  "PK": "QUESTION",
  "SK": "550e8400-e29b-41d4-a716-446655440000",
  "question": "When should you use a relational (SQL) database versus a NoSQL database?",
  "reference_urls": [
    "https://stackoverflow.com/questions"
  ],
```

## Topic
- Query on **PK** to retrieve all topics.
- GetItem on **(PK+SK)** to retrieve a specific topic.
```json
    "PK": "TOPIC",
    "SK": "6c299eca-860e-4654-8194-fc12e045b696",
    "name": "Databases"
```

## Relationship (Adjacency List)
- Query on **PK** to retrieve all relationship items for a topic (shows all questions for a topic).
- Query **QuestionTopicsIndex (keys-only GSI)** with **QuestionTopicsIndex_PK** to retrieve all relationship items for a question (shows all topics for a question).
```json
    "PK": "TOPIC#6c299eca-860e-4654-8194-fc12e045b696",
    "SK": "QUESTION#550e8400-e29b-41d4-a716-446655440000"
    "QuestionTopicsIndex_PK": "QUESTION#550e8400-e29b-41d4-a716-446655440000"
```

## AI Question History
- Recently generated AI questions are stored with TTL and referenced by Bedrock to help generate novel questions each day.
```json
  "PK": "AI_QUESTION#BEHAVIORAL", # or "AI_QUESTION#TECHNICAL"
  "SK": "3d886e6d-b599-4b68-b71f-d74c9d16c50c",
  "question": "Tell me about a time you had to prioritize multiple competing tasks.",
  "ttl": 1788174000
```