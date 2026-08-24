# this file fetches AI generated questions
import random
import uuid
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timezone, timedelta

TTL_DAYS = 7
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
behavioral_topics = [
    "conflict or disagreement",
    "receiving feedback",
    "giving feedback",
    "working with ambiguity",
    "learning something quickly",
    "prioritization",
    "taking ownership",
    "making a mistake",
    "debugging a difficult problem",
    "communicating technical information",
    "collaboration",
    "handling changing requirements",
    "working under a deadline",
    "improving an existing process",
    "making a technical decision",
]

technical_topics = [
    "databases",
    "distributed systems",
    "AWS or cloud architecture",
    "networking",
    "security",
    "testing",
    "APIs",
    "concurrency",
    "caching",
    "performance",
    "reliability",
    "event-driven architecture",
    "containers",
    "Kubernetes",
    "data modeling",
]

def generate_prompts():
    behavioral_topic = random.choice(behavioral_topics)
    technical_topic = random.choice(technical_topics)

    behavioral_prompt = f"""
    Generate exactly one short behavioral or situational interview question
    for a junior-to-mid-level software engineer.

    Today's focus area: {behavioral_topic}

    Requirements:
    - The question must primarily test the focus area above
    - Ask about a specific situation, decision, challenge, or experience
    - Do not generate a question substantially similar to any recent question below
    - Do not ask multiple separate questions
    - Return only the question
    - No introduction
    - No explanation
    - No markdown
    - One or two sentences maximum
    """

    technical_prompt = f"""
    Generate exactly one short technical interview question
    for a junior-to-mid-level software engineer.

    Today's technical area: {technical_topic}

    Requirements:
    - The question must primarily test the technical area above
    - Prefer practical scenarios, tradeoffs, debugging situations, or design decisions
    - Do not generate a question substantially similar to any recent question below
    - Do not ask the candidate to write code
    - Do not ask multiple separate questions
    - Return only the question
    - No introduction
    - No explanation
    - No markdown
    - One or two sentences maximum
    """

    return behavioral_prompt, technical_prompt

def get_ai_questions(table):
    now = int(datetime.now(timezone.utc).timestamp())

    behavioral_response = table.query(
        KeyConditionExpression=Key("PK").eq("AI_QUESTION#BEHAVIORAL"),
        FilterExpression=Attr("TTL").gt(now), # only return AI questions whose TTL has not expired yet
    )

    technical_response = table.query(
        KeyConditionExpression=Key("PK").eq("AI_QUESTION#TECHNICAL"),
        FilterExpression=Attr("TTL").gt(now), # only return AI questions whose TTL has not expired yet
    )

    behavioral_history = "\n".join(
        f"- {item['question']}"
        for item in behavioral_response.get("Items", [])
    )

    technical_history = "\n".join(
        f"- {item['question']}"
        for item in technical_response.get("Items", [])
    )

    behavioral_prompt, technical_prompt = generate_prompts()

    prompts = [
        f"{behavioral_prompt}\nRecent questions:\n{behavioral_history}",
        f"{technical_prompt}\nRecent questions:\n{technical_history}",
    ]

    ai_questions = []

    for prompt in prompts:
        response = bedrock.converse(
            modelId="amazon.nova-lite-v1:0",
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            inferenceConfig={
                "maxTokens": 100,
                "temperature": 0.8,
            },
        )

        ai_questions.append(
            response["output"]["message"]["content"][0]["text"].strip()
        )

    return ai_questions

def save_ai_questions(table, ai_questions):
    ttl = int(
        (datetime.now(timezone.utc) + timedelta(days=TTL_DAYS)).timestamp()
    )

    table.put_item(
        Item={
            "PK": "AI_QUESTION#BEHAVIORAL",
            "SK": str(uuid.uuid4()),
            "question": ai_questions[0],
            "TTL": ttl,
        }
    )

    table.put_item(
        Item={
            "PK": "AI_QUESTION#TECHNICAL",
            "SK": str(uuid.uuid4()),
            "question": ai_questions[1],
            "TTL": ttl,
        }
    )