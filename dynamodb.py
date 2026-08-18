import boto3, uuid
import streamlit as st
from boto3.dynamodb.conditions import Key, Attr

class DynamoDB:
    def __init__(self):
        print("construction")
        # Authorization provided through a named local AWS credential profile which uses access keys for an IAM user with the required permissions. (created via `aws configure --profile study-bank` on local machine)
        self.session = boto3.Session(profile_name="study-bank",region_name="us-east-1")
        self.dynamodb = self.session.resource("dynamodb")
        self.table = self.dynamodb.Table("study-bank")       

    @st.cache_resource # caches an object
    def get_dynamodb():
        return DynamoDB()

    def generate_uuid(self):
        return str(uuid.uuid4())

    def clear_get_entries_cache(self, entry_type):
        self.get_entries.clear(entry_type)
        print(f"{entry_type.lower()} cache cleared")

    @st.cache_data # caches return value
    def get_entries(_self, entry_type): # _self tells Streamlit to exclude the DynamoDB object from the cache key, because we only need to distinguish "QUESTION" or "TOPIC"
        items = []
        response = _self.table.query(
            KeyConditionExpression=Key("TYPE").eq(entry_type)
        )
        items.extend(response["Items"])

        while "LastEvaluatedKey" in response: # pagination if > 1kb returned
            response = _self.table.query(
                KeyConditionExpression=Key("TYPE").eq(entry_type),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response["Items"])
        print(f"Fetched & Cached {len(items)} {entry_type.lower()}{'' if len(items) == 1 else 's'}")
        return items

    def create_question(self, question, reference_url, topic_id):
        question_id = self.generate_uuid()
        self.table.put_item(
            Item={
                "TYPE": "QUESTION",
                "UUID": question_id,
                "question": question,
                "reference_url": reference_url,
                "topic_id": topic_id,
            }
        )
        print(f"Created question {question_id}")

    def update_question(self, question_id, question, reference_url, topic_id):
        self.table.update_item(
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

    def delete_question(self, question_id):
        self.table.delete_item(
            Key={"TYPE": "QUESTION","UUID": question_id}
        )
        print(f"Deleted question {question_id}")

    def create_topic(self, name):
        topic_id = self.generate_uuid()

        self.table.put_item(
            Item={
                "TYPE": "TOPIC",
                "UUID": topic_id,
                "name": name,
            }
        )

        print(f"Created topic {topic_id}")

    def update_topic(self, topic_id, name):
        self.table.update_item(
            Key={"TYPE": "TOPIC","UUID": topic_id},
            UpdateExpression="SET #name = :name",
            ExpressionAttributeNames={"#name": "name"},
            ExpressionAttributeValues={":name": name},
        )

        print(f"Updated topic {topic_id}")

    def topic_has_references(self, topic_id):
        count = 0

        response = self.table.query(
            KeyConditionExpression=Key("TYPE").eq("QUESTION"),
            FilterExpression=Attr("topic_id").eq(topic_id),
        )

        count += len(response["Items"])

        while "LastEvaluatedKey" in response: # pagination if > 1kb returned
            response = self.table.query(
                KeyConditionExpression=Key("TYPE").eq("QUESTION"),
                FilterExpression=Attr("topic_id").eq(topic_id),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            count += len(response["Items"])

        return count > 0, count

    def delete_topic(self, topic_id):
        self.table.delete_item(Key={"TYPE": "TOPIC","UUID": topic_id})
        print(f"Deleted topic {topic_id}")