
# this file fetches AI generated questions
import random
import uuid
import boto3
from pathlib import Path
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timezone, timedelta

TTL_DAYS = 30
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
    "programming fundamentals",
    "object-oriented programming",
    "design patterns",
    "code design and maintainability",
    "asynchronous programming",
    "error handling",
    "dependency injection",
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

BAD_QUESTIONS = """
Examples of BAD questions. Never reproduce or paraphrase these:

- Tell me about a time you overcame a challenge.
- Describe a situation where you demonstrated leadership.
- Tell me about a time you worked with a difficult teammate.
- How do you ensure your code is scalable and maintainable?
- What are the best practices for writing clean code?
- How would you design a robust and efficient system?
- How do you handle errors in your applications?
- What strategies do you use to optimize performance?
- Walk me through your resume.
- Tell me about a project you're proud of.
- What was the biggest challenge you faced in your project?

These questions are bad because they are generic, repetitive,
overly broad, predictable, or encourage rehearsed answers.
Simply changing their wording does not make them better.
"""

GOOD_QUESTIONS = """
Examples of GOOD questions. Match their specificity, not their wording:

Behavioral:
- A teammate disagrees with your proposed fix shortly before a release. How would you handle that disagreement?
- Tell me about a decision you made with incomplete information that you later had to revise.

Technical:
- Why can adding an index to a database table make some operations slower?
- Two requests read the same database value before either updates it. What problem can this cause?
- An API request times out, but the server still completes the operation. What problem can occur if the client retries?

Resume:
- Your resume mentions migrating an application to AWS. What was the most important technical decision in that migration?
- You mention implementing a caching layer. How did you determine what data should be cached?

Resume examples are illustrative. Only reference details that
actually appear in the provided resume.
"""

def generate_prompt(question_type):
    question_type = "RESUME"
    common_requirements = f"""
    Generate exactly one interview question for a junior-to-mid-level
    software engineer.

    {BAD_QUESTIONS}

    {GOOD_QUESTIONS}

    Requirements:
    - Ask exactly one question testing one main idea.
    - Make it specific, substantive, and useful for interview preparation.
    - Prefer questions requiring genuine understanding or judgment.
    - Avoid generic questions that anyone could answer with buzzwords.
    - Avoid repeating common interview questions with minor changes.
    - Use plain, direct, natural language.
    - Avoid filler, unnecessary setup, and excessive complexity.
    - Do not combine multiple questions.
    - Do not ask the candidate to write code.
    - Do not repeat or paraphrase any recent question below.
    - Return only the question.
    - No explanation, introduction, or markdown.
    - The question must be one sentence.
    """

    if question_type == "BEHAVIORAL":
        topic = random.choice(behavioral_topics)

        specific_requirements = f"""
        Category: Behavioral
        Focus area: {topic}

        Ask about one concrete workplace situation, decision, or experience.

        The question should reveal how the candidate thinks, communicates,
        or makes decisions in a realistic software engineering environment.

        Do not default to "Tell me about a time..." or ask for a generic
        example of demonstrating a positive personality trait.

        Vary between realistic situational questions and specific
        past-experience questions.
        """

    elif question_type == "TECHNICAL":
        topic = random.choice(technical_topics)

        angle = random.choice([
            "a specific failure and its cause",
            "a concrete technical tradeoff",
            "diagnosing an observable problem",
            "understanding why a particular behavior occurs",
            "choosing between two technical approaches",
        ])

        specific_requirements = f"""
        Category: Technical
        Focus area: {topic}
        Question approach: {angle}

        Select one narrow technical concept within the focus area.

        Test actual technical understanding, not memorization of buzzwords.

        Prefer a question with a reasonably clear expected answer.
        Do not invent unnecessary project requirements or hypothetical
        business scenarios to make the question seem sophisticated.
        """

    else:
        resume = Path(__file__).with_name("resume.txt").read_text(
            encoding="utf-8"
        ).strip()

        if not resume:
            raise ValueError("resume.txt is empty")

        specific_requirements = f"""
        Category: Resume

        Ask one meaningful technical or experience-based question
        grounded in the candidate's actual resume.

        Select one specific project, implementation, accomplishment,
        technology, or responsibility explicitly mentioned in the resume.

        Ask about a decision, tradeoff, implementation detail, challenge,
        or technical rationale that would reveal depth of understanding.

        The question must explicitly reference the selected resume detail.

        Do not ask the candidate to summarize their resume.
        Do not ask generic questions that could apply to any resume.
        Do not invent projects, responsibilities, or technologies.

        Candidate resume:
        {resume}
        """

    return f"{common_requirements}\n{specific_requirements}"


def get_ai_questions(table):
    now = int(datetime.now(timezone.utc).timestamp())

    # Rotate question types daily to guarantee variety
    question_types = ["BEHAVIORAL", "TECHNICAL", "RESUME"]
    question_type = question_types[
        datetime.now(timezone.utc).date().toordinal() % len(question_types)
    ]

    # Retrieve recent questions from all three categories
    history = []

    for category in question_types:
        query_args = {
            "KeyConditionExpression": Key("PK").eq(f"AI_QUESTION#{category}"),
            "FilterExpression": Attr("TTL").gt(now),
        }

        while True:
            response = table.query(**query_args)

            history.extend(
                item["question"]
                for item in response.get("Items", [])
            )

            if "LastEvaluatedKey" not in response:
                break

            query_args["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    question_history = "\n".join(f"- {q}" for q in history)

    prompt = generate_prompt(question_type)
    prompt += f"\nRecent questions to avoid:\n{question_history}"

    response = bedrock.converse(
        modelId="amazon.nova-pro-v1:0",
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}],
            }
        ],
        inferenceConfig={
            "maxTokens": 200,
            "temperature": 0.7,
        },
    )

    question = response["output"]["message"]["content"][0]["text"].strip()

    return {
        "type": question_type,
        "question": question,
    }


def save_ai_questions(table, ai_question):
    ttl = int(
        (datetime.now(timezone.utc) + timedelta(days=TTL_DAYS)).timestamp()
    )

    table.put_item(
        Item={
            "PK": f"AI_QUESTION#{ai_question['type']}",
            "SK": str(uuid.uuid4()),
            "question": ai_question["question"],
            "TTL": ttl,
        }
    )
