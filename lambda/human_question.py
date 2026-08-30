# this file fetches human-generated questions
import random, os
from boto3.dynamodb.conditions import Key
HUMAN_QUESTIONS_AMOUNT = int(os.environ["HUMAN_QUESTIONS_AMOUNT"])

def get_human_questions(table):
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
        min(HUMAN_QUESTIONS_AMOUNT, len(questions)),
    )