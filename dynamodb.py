import boto3, uuid

session = boto3.Session(
    profile_name="study-bank",
    region_name="us-east-1",
)

dynamodb = session.resource("dynamodb")
table = dynamodb.Table("study-bank")

def get_questions():
    items = []
    response = table.scan()
    items.extend(response["Items"])

    while "LastEvaluatedKey" in response:
        response = table.scan(
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response["Items"])
    print(f"Fetched {len(items)} question(s)")
    return items


def create_question(question, answer_url, topic):
    table.put_item(
        Item={
            "question_id": str(uuid.uuid4()),
            "question": question,
            "answer_url": answer_url,
            "topic": topic,
        }
    )

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

def delete_question(question_id):
    table.delete_item(
        Key={
            "question_id": question_id
        }
    )