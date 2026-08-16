import boto3, uuid
import streamlit as st
from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb.types import Binary

# Authorization provided through a named local AWS credential profile
# which uses access keys for an IAM user with the required permissions.
# (created via `aws configure --profile study-bank` on local machine)
session = boto3.Session(
    profile_name="study-bank",
    region_name="us-east-1",
)

dynamodb = session.resource("dynamodb")
table = dynamodb.Table("study-bank")

# general functions:

# generate binary UUID for new database entry
def generate_uuid():
    return str(uuid.uuid4())

@st.cache_data
def get_entries(entry_type):
    items = []
    response = table.query(
        KeyConditionExpression=Key("TYPE").eq(entry_type)
    )
    items.extend(response["Items"])

    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=Key("TYPE").eq(entry_type),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response["Items"])
    print(f"Fetched & Cached {len(items)} {entry_type.lower()}{'' if len(items) == 1 else 's'}")
    return items

# question functions:

def create_question(question, reference_url, topic_id):
    question_id = generate_uuid()
    table.put_item(
        Item={
            "TYPE": "QUESTION",
            "UUID": question_id,
            "question": question,
            "reference_url": reference_url,
            "topic_id": topic_id,
        }
    )
    print(f"Created question {question_id}")

def update_question(question_id, question, reference_url, topic_id):
    table.update_item(
        Key={
            "TYPE": "QUESTION",
            "UUID": question_id,
        },
        UpdateExpression="""
            SET question = :question,
                reference_url = :reference_url,
                topic_id = :topic_id
        """,
        ExpressionAttributeValues={
            ":question": question,
            ":reference_url": reference_url,
            ":topic_id": topic_id,
        },
    )
    print(f"Updated question {question_id} with topic {topic_id}")

def delete_question(question_id):
    table.delete_item(
        Key={"TYPE": "QUESTION","UUID": question_id}
    )
    print(f"Deleted question {question_id}")

# topic functions:

# returns true if this topic name already exists (case insensitive match)
def check_duplicate_topic(name, topic_id=None):
    response = table.query(KeyConditionExpression=Key("TYPE").eq("TOPIC"))
    normalized_name = name.casefold()
    if any(
        topic["name"].casefold() == normalized_name
        and (topic_id is None or topic["UUID"] != topic_id)
        for topic in response["Items"]
    ):
        return True
    return False

def create_topic(name):
    topic_id = generate_uuid()

    table.put_item(
        Item={
            "TYPE": "TOPIC",
            "UUID": topic_id,
            "name": name,
        }
    )

    print(f"Created topic {topic_id}")

def update_topic(topic_id, name):
    table.update_item(
        Key={"TYPE": "TOPIC","UUID": topic_id},
        UpdateExpression="SET #name = :name",
        ExpressionAttributeNames={"#name": "name"},
        ExpressionAttributeValues={":name": name},
    )

    print(f"Updated topic {topic_id}")

def check_topic_has_references(topic_id):
    response = table.query(
        KeyConditionExpression=Key("TYPE").eq("QUESTION"),
        FilterExpression=Attr("topic_id").eq(topic_id),
    )

    if response["Items"]:
        return True, len(response["Items"])
    return False, 0

def delete_topic(topic_id):
    table.delete_item(Key={"TYPE": "TOPIC","UUID": topic_id})
    print(f"Deleted topic {topic_id}")