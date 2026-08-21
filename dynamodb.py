import boto3, uuid, sys
import streamlit as st
from boto3.dynamodb.conditions import Key, Attr

class DynamoDB:
    def __init__(self):
        print("construction")
        # Authorization provided through a named local AWS credential profile which uses access keys for an IAM user with the required permissions. (created via `aws configure --profile study-bank` on local machine)
        self.table_name = "study-bank"
        self.session = boto3.Session(profile_name=self.table_name,region_name="us-east-1") # high level resource API
        self.client = self.session.client("dynamodb") # lower level dynamoDB client, for things like transactions
        self.dynamodb = self.session.resource("dynamodb")
        self.table = self.dynamodb.Table(self.table_name)       

    @st.cache_resource # caches an object
    def get_dynamodb():
        return DynamoDB()

    def generate_uuid(self):
        return str(uuid.uuid4())

    def clear_get_entries_cache(self, entry_type):
        self.get_entries.clear(entry_type)
        print(f"{entry_type.lower()} cache cleared")

    @st.cache_data # caches return value. returns a list of dicts
    def get_entries(_self, entry_type): # _self tells Streamlit to exclude the DynamoDB object from the cache key, because we only need to distinguish "QUESTION" or "TOPIC"
        items = []
        response = _self.table.query(
            KeyConditionExpression=Key("PK").eq(entry_type)
        )
        items.extend(response["Items"])

        while "LastEvaluatedKey" in response: # pagination if > 1kb returned
            response = _self.table.query(
                KeyConditionExpression=Key("PK").eq(entry_type),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response["Items"])
        print(f"Fetched & Cached {len(items)} {entry_type.lower()}{'' if len(items) == 1 else 's'}")
        return items

    # returns a list of topic ids. not cached
    def get_question_topics(self, question_id):
        response = self.table.query(
            IndexName="QuestionTopicsIndex",
            KeyConditionExpression=Key("QuestionTopicsIndex_PK").eq(f"QUESTION#{question_id}")
        )
        return [item["PK"].removeprefix("TOPIC#") for item in response["Items"]]

    # create a question and its one relationship entry per topic
    def create_question(self, question, reference_urls, topic_ids):
        question_id = self.generate_uuid()

        transact_items = [ # atomic transaction
            {
                "Put": { # creating the question
                    "TableName": self.table_name,
                    "Item": {
                        "PK": {"S": "QUESTION"},
                        "SK": {"S": question_id},
                        "question": {"S": question},
                        "reference_urls": {
                            "L": [{"S": url} for url in reference_urls]
                        },
                    }
                }
            }
        ]

        for topic_id in topic_ids:
            transact_items.append({ # relationship entry for each topic
                "Put": {
                    "TableName": self.table_name,
                    "Item": {
                        "PK": {"S": f"TOPIC#{topic_id}"},
                        "SK": {"S": f"QUESTION#{question_id}"},
                        "QuestionTopicsIndex_PK": {
                            "S": f"QUESTION#{question_id}"
                        },
                    }
                }
            })

        self.client.transact_write_items(
            TransactItems=transact_items
        )
        print(f"Created question {question_id}")

    # update a question and all of its associate relationship entries
    def update_question(self, question_id, question, reference_urls, topic_ids):
        current_topic_ids = set(self.get_question_topics(question_id))
        new_topic_ids = set(topic_ids)

        topics_to_delete = current_topic_ids - new_topic_ids
        topics_to_add = new_topic_ids - current_topic_ids

        transact_items = [
            {
                "Update": {
                    "TableName": self.table_name,
                    "Key": {
                        "PK": {"S": "QUESTION"},
                        "SK": {"S": question_id},
                    },
                    "UpdateExpression": """
                        SET question = :question,
                            reference_urls = :reference_urls
                    """,
                    "ExpressionAttributeValues": {
                        ":question": {"S": question},
                        ":reference_urls": {
                            "L": [{"S": url} for url in reference_urls]
                        },
                    },
                }
            }
        ]

        for topic_id in topics_to_delete:
            transact_items.append({
                "Delete": {
                    "TableName": self.table_name,
                    "Key": {
                        "PK": {"S": f"TOPIC#{topic_id}"},
                        "SK": {"S": f"QUESTION#{question_id}"},
                    },
                }
            })

        for topic_id in topics_to_add:
            transact_items.append({
                "Put": {
                    "TableName": self.table_name,
                    "Item": {
                        "PK": {"S": f"TOPIC#{topic_id}"},
                        "SK": {"S": f"QUESTION#{question_id}"},
                        "QuestionTopicsIndex_PK": {
                            "S": f"QUESTION#{question_id}"
                        },
                    },
                }
            })

        self.client.transact_write_items(TransactItems=transact_items)
        print(f"Updated question {question_id}")

    def delete_question(self, question_id):
        topic_ids = self.get_question_topics(question_id)

        transact_items = [
            {
                "Delete": {
                    "TableName": self.table_name,
                    "Key": {
                        "PK": {"S": "QUESTION"},
                        "SK": {"S": question_id},
                    },
                }
            }
        ]

        for topic_id in topic_ids:
            transact_items.append({ # delete all relationship entries for this question
                "Delete": {
                    "TableName": self.table_name,
                    "Key": {
                        "PK": {"S": f"TOPIC#{topic_id}"},
                        "SK": {"S": f"QUESTION#{question_id}"},
                    },
                }
            })

        self.client.transact_write_items(
            TransactItems=transact_items
        )

        print(f"Deleted question {question_id} and {len(topic_ids)} topic relationship(s)")

    def create_topic(self, name):
        topic_id = self.generate_uuid()
        self.table.put_item(Item={"PK": "TOPIC","SK": topic_id,"name": name})
        print(f"Created topic {topic_id}")

    def update_topic(self, topic_id, name):
        self.table.update_item(
            Key={"PK": "TOPIC","SK": topic_id},
            UpdateExpression="SET #name = :name",
            ExpressionAttributeNames={"#name": "name"},
            ExpressionAttributeValues={":name": name},
        )

        print(f"Updated topic {topic_id}")

    def check_topic_has_references(self, topic_id):
        response = self.table.query(KeyConditionExpression=Key("PK").eq(f"TOPIC#{topic_id}"),Limit=1)
        return len(response["Items"]) > 0

    def delete_topic(self, topic_id):
        if self.check_topic_has_references(topic_id):
            print(f"\nERROR: ATTEMPTED TO DELETE TOPIC {topic_id} WHICH IS USED BY AT LEAST ONE QUESTION\n")
            sys.exit(1)
        self.table.delete_item(Key={"PK": "TOPIC","SK": topic_id})
        print(f"Deleted topic {topic_id}")

    # used during development
    # def delete_everything(self):
    #     response = self.table.scan(ProjectionExpression="PK, SK")
    #     with self.table.batch_writer() as batch:
    #         while True:
    #             for item in response["Items"]:
    #                 batch.delete_item(Key={"PK": item["PK"],"SK": item["SK"]})

    #             if "LastEvaluatedKey" not in response:
    #                 break

    #             response = self.table.scan(
    #                 ProjectionExpression="PK, SK",
    #                 ExclusiveStartKey=response["LastEvaluatedKey"],
    #             )
    #     print(f"{self.table_name} has been fully cleared!")
    #     self.clear_get_entries_cache("QUESTION")
    #     self.clear_get_entries_cache("TOPIC")