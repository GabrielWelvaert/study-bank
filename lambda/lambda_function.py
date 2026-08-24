import os
import boto3
from datetime import datetime
from zoneinfo import ZoneInfo
from human_question import get_human_questions
from ai_question import get_ai_questions, save_ai_questions

TABLE_NAME = os.environ["TABLE_NAME"]
EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]
dynamodb = boto3.resource("dynamodb")
ses = boto3.client("sesv2")
table = dynamodb.Table(TABLE_NAME)

def build_email(human_questions, AI_questions):
    max_len_reference_url = 35
    sections = [
        "Good morning. Here are your daily questions. Good luck!"
    ]

    for i, question in enumerate(human_questions, start=1):
        reference_urls = question.get("reference_urls", [])

        reference_links = ", ".join(
            f'<a href="{url}">{url[:max_len_reference_url] + "..." if len(url) > max_len_reference_url else url}</a>'
            for url in reference_urls
        )

        sections.append(
            f"{i}. {'<br>'.join(question['question'].splitlines())}<br>"
            f"Refer: {reference_links}"
        )

    sections.append(f"AI Behavioral Question:<br>{AI_questions[0]}")
    sections.append(f"AI Technical Question:<br>{AI_questions[1]}")

    sections.append("That's all for today. See you tomorrow!")

    return "<br><br>".join(sections)

def lambda_handler(event, context):
    today = datetime.now(ZoneInfo("America/New_York")).strftime("%m/%d/%Y")
    human_questions = get_human_questions(table)
    ai_questions = get_ai_questions(table)

    body = build_email(human_questions, ai_questions)

    response = ses.send_email(
        FromEmailAddress=EMAIL_FROM,
        Destination={
            "ToAddresses": [EMAIL_TO],
        },
        Content={
            "Simple": {
                "Subject": {
                    "Data": f"Study Bank Daily Questions - {today}",
                },
                "Body": {
                    "Html": {
                        "Data": body,
                    },
                },
            },
        },
    )

    # save recent AI questions as TTL entries otherwise the AI questions tend to be similar each day
    save_ai_questions(table, ai_questions)

    return {
        "statusCode": 200,
        "messageId": response["MessageId"],
    }