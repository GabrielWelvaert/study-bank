# this file fetches human-generated questions
import random
from boto3.dynamodb.conditions import Key

def get_human_questions(table, count=3):
    questions = []

    response = table.query(
        KeyConditionExpression=Key("PK").eq("QUESTION")
    )

    questions.extend(response["Items"])

    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=Key("PK").eq("QUESTION"),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )

        questions.extend(response["Items"])

    return random.sample(
        questions,
        min(count, len(questions)),
    )