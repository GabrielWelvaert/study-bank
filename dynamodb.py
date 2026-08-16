import boto3, uuid
import streamlit as st

# Authorization provided through a named local AWS credential profile
# which uses access keys for an IAM user with the required permissions.
# (created via `aws configure --profile study-bank`)
session = boto3.Session(
    profile_name="study-bank",
    region_name="us-east-1",
)

dynamodb = session.resource("dynamodb")
table = dynamodb.Table("study-bank")

@st.cache_data
def get_questions():
    items = []
    response = table.scan()
    items.extend(response["Items"])

    while "LastEvaluatedKey" in response:
        response = table.scan(
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response["Items"])
    print(f"Fetched & Cached {len(items)} question{'s' if len(items) != 1 else ''}")
    return items

def create_question(question, answer_url, topic):
    question_id = str(uuid.uuid4())
    table.put_item(
        Item={
            "question_id": question_id,
            "question": question,
            "answer_url": answer_url,
            "topic": topic,
        }
    )
    print(f"Created question {question_id}")

def update_question(question_id, question, answer_url, topic):
    table.update_item(
        Key={
            "question_id": question_id
        },
        UpdateExpression="""
            SET question = :question,
                answer_url = :answer_url,
                topic = :topic
        """,
        ExpressionAttributeValues={
            ":question": question,
            ":answer_url": answer_url,
            ":topic": topic,
        },
    )
    print(f"updated question {question_id}")

def delete_question(question_id):
    table.delete_item(Key={"question_id": question_id})
    print(f"Deleted question {question_id}")