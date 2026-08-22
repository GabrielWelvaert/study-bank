import streamlit as st
import random
from dynamodb import DynamoDB

DEBUG_MODE = False
RED = "#FF4B4B"
GREEN = "#198754"
QUESTION_MAX_LEN = 1500
QUESTION_BUTTON_MAX_TEXT_LEN = 80

# temporary pop up message
def toast(message, status = None):
    if status:
        st.session_state.toast_status = status
    st.session_state.message = message

def clear_topic_field():
    st.session_state.form_topic_ids = []

# clear question data from state so form does not populate on rerun
def clear_fields():
    st.session_state.form_question = ""
    st.session_state.form_reference_urls = ""
    clear_topic_field()

# clear fields and go back to Add mode
def reset_form():
    st.session_state.form_editing_id = None # the id of the question being edited is essentially a hidden field
    clear_fields()

# place question data into session variable so it will populate form on rerun
def load_question_to_form(question, dynamodb):
    st.session_state.form_editing_id = question["SK"]
    st.session_state.form_question = question["question"]
    st.session_state.form_reference_urls = "\n".join(question.get("reference_urls", []))
    st.session_state.form_topic_ids = dynamodb.get_question_topics(question["SK"])

# save or update question from main form
def save_question(dynamodb):
    question = st.session_state.form_question.strip()[:QUESTION_MAX_LEN]
    reference_urls = [
        url.strip()
        for url in st.session_state.form_reference_urls.splitlines()
        if url.strip()
    ]
    topic_id = st.session_state.form_topic_ids

    if not question:
        toast("Question is required.", "error")
        return
    if not topic_id:
        toast("Topic is required.", "error")
        return
    if st.session_state.form_editing_id:
        dynamodb.update_question(st.session_state.form_editing_id,question,reference_urls,topic_id)
        toast("Question updated.")
    else:
        dynamodb.create_question(question,reference_urls,topic_id)
        toast("Question added.")
    dynamodb.clear_get_entries_cache("QUESTION")
    reset_form()

# pop up warning for deleting a question
@st.dialog("Delete Question")
def confirm_delete(dynamodb):
    st.warning("This will permanently delete the question! Are you sure?")

    with st.container(horizontal=True):
        if st.button("Cancel"):
            st.rerun()

        if st.button("Delete", type="primary"):
            dynamodb.delete_question(st.session_state.form_editing_id)
            toast("Question deleted.")
            reset_form()
            dynamodb.clear_get_entries_cache("QUESTION")
            st.rerun()

# case insensitive check
def check_duplicate_topic(topic_map, name, topic_id=None):
    normalized_name = name.casefold()

    return any(
        existing_id != topic_id
        and existing_name.casefold() == normalized_name
        for existing_id, existing_name in topic_map.items()
    )

# pop up for viewing a random question 
@st.dialog("Press Space or click the button for a random question", width="medium")
def random_question(dynamodb, questions, topic_map):
    print("random question dialog")
    # custom CSS to hide everything except the question
    st.html("""<style>[data-testid="stDialog"] { background: #262730 !important; }</style>""")
    selected_topics = st.multiselect(
        "Topics",
        options=list(topic_map.keys()),
        format_func=lambda id: topic_map[id],
    )
    # fetch a new question with respect to topic choices
    if st.button("Random Question", shortcut="Space"):
        current_id = st.session_state.get("random_question_id")
        matching_questions = questions
        if selected_topics:
            selected_topics = set(selected_topics)
            matching_questions = [
                q for q in questions
                if selected_topics & set(dynamodb.get_question_topics(q["SK"]))
            ]

        matching_questions = [
            q for q in matching_questions
            if q["SK"] != current_id
        ]

        if matching_questions:
            st.session_state.random_question_id = random.choice(matching_questions)["SK"]

    # dont display question until one has been selected
    if "random_question_id" not in st.session_state:
        return

    # displaying question
    question = next(
        q for q in questions
        if q["SK"] == st.session_state.random_question_id
    )

    st.subheader(question["question"], anchor=False)
    for url in question["reference_urls"]:
        st.markdown(f"### Refer: [{url}]({url})")

# pop up for managing topics
@st.dialog("Manage Topics")
def manage_topics(dynamodb, topic_map, questions):
    st.subheader("Add Topic", anchor=False)
    new_topic_name = st.text_input("New Topic", autocomplete="off").strip()
    if st.button("Add", type="primary"):
        if not new_topic_name:
            toast("Topic name is required.", "error")
        elif check_duplicate_topic(topic_map, new_topic_name):
            toast(f"Topic '{new_topic_name}' already exists.", "error")
        else:
            dynamodb.create_topic(new_topic_name)
            dynamodb.clear_get_entries_cache("TOPIC")
            toast(f"Topic '{new_topic_name}' created")
        st.rerun()

    if len(topic_map) == 0 or topic_map is None:
        return

    st.divider()
    st.subheader(f"Existing Topics ({len(topic_map)} total)", anchor=False)

    # topic selected in the dropdown of the manage topics window
    topic_id = st.selectbox(
        "Topic",
        options=list(topic_map.keys()),
        format_func=lambda id: topic_map[id],
    )

    name = st.text_input("Name",value=topic_map[topic_id],  autocomplete="off")

    with st.container(horizontal=True):
        if st.button("Update"):
            name = name.strip()
            if check_duplicate_topic(topic_map, name, topic_id):
                toast(f"Topic '{name}' already exists.", "error")
            else:
                dynamodb.update_topic(topic_id, name.strip())
                toast(f"Updated Topic '{name}'")
                dynamodb.clear_get_entries_cache("TOPIC")
                reset_form() # user may be editing a question that used this topic, so just reset everything for simplicity
            st.rerun()

        if st.button("Delete"):
            topic_has_references = dynamodb.check_topic_has_references(topic_id)
            if(topic_has_references > 0):
                toast(f"Topic '{name}' cannot be deleted because it is referenced by at least one question.", "error")
            else:
                dynamodb.delete_topic(topic_id)
                toast(f"Deleted topic '{name}'")
                dynamodb.clear_get_entries_cache("TOPIC")
                clear_topic_field() # if topic was populated before valid deltion, it could linger, so clear this input
            st.rerun()

@st.dialog("DEBUG MODE FULL DELETE")
def confirm_delete_everything(dynamodb):
    st.warning("This will permanently delete everything!!!")
    if st.button("DELETE EVERYTHING", type="primary"):
        dynamodb.delete_everything()
        st.rerun()

def main():
    # fetch a cachable dynamoDB object so it isn't constantly reconstructed
    dynamodb = DynamoDB.get_dynamodb() 
    # all questions and topics are stored in memory and each has its own cache which is invalidated on CUD operations (assumes one user and no external writes to database)
    # relationships are not pre-fetched or cached, they are obtained as needed for the UI
    questions = dynamodb.get_entries("QUESTION") # ie each element is {'PK': 'QUESTION', 'SK': '', 'question': '', 'reference_urls': []}
    topic_map = {topic["SK"]: topic["name"] for topic in dynamodb.get_entries("TOPIC")} # map of topic ids to names
    num_questions = len(questions)
    num_topics = len(topic_map) 

    # we're either in edit mode or add mode. if we have an form_editing_id, we know we're in edit mode
    st.session_state.setdefault("form_editing_id", None)

    # toast doesn't accept color argument, so we need a custom css override
    toast_color = GREEN
    if (toast_status := st.session_state.pop("toast_status", None)) == "error":
        toast_color = RED
    st.html(f"""<style>[data-testid="stToast"] {{background-color: {toast_color} !important;color: white !important;}}</style>""")

    # getting rid of "press enter to apply" for text inputs since they're all in forms
    st.html("""<style>[data-testid="InputInstructions"] small { display: none !important;}</style>""")

    st.set_page_config(page_title="Study Bank",page_icon="📚")
    st.title("Study Bank Question Modifier", anchor=False)

    # session_state.message is displayed as toast message
    if message := st.session_state.pop("message", None):
        st.toast(message) # color for this defined in toast_color

    if(DEBUG_MODE):
        st.button("DELETE EVERYTHING", on_click=confirm_delete_everything, args=(dynamodb,),type="primary")

    # Add / Edit Header
    with st.container(horizontal=True, vertical_alignment="center", height=72, border=False):
        # edit mode
        if st.session_state.form_editing_id:
            st.subheader("Edit Question", width="content", anchor=False)
            st.button("Switch to Add Question", on_click=reset_form, type="primary")
        # add mode
        else:
            st.subheader("Add Question", width="content", anchor=False)
        st.button("Manage Topics", on_click=manage_topics, args=(dynamodb,topic_map,questions))
        
    # the actual form
    with st.form("question_form", enter_to_submit=False):
        # question label will display UUID of question in edit mode
        question_label = f'({st.session_state.form_editing_id})' if st.session_state.form_editing_id is not None else ''

        st.text_area(f"Question {question_label}", key="form_question", height=70)
        st.text_area(
            "Reference URLs",
            key="form_reference_urls",
            placeholder="https://example.com/1\nhttps://example.com/2",
            height=70
        )
        topic_id = st.multiselect(
            "Topic",
            options=list(topic_map.keys()),
            format_func=lambda id: topic_map[id],
            key="form_topic_ids",
            help="Create a topic with the Manage Topics button" if num_topics==0 else None
        )

        with st.container(horizontal=True):
            st.form_submit_button("Save", on_click=save_question,args=(dynamodb,), type="primary", width="content",disabled=num_topics==0,help="Create a topic first. Questions require a topic." if (num_topics==0) else None)
            st.form_submit_button("Clear Fields", on_click=clear_fields, width="content")

            if st.session_state.form_editing_id:
                st.form_submit_button("Delete", on_click=confirm_delete, width="content",args=(dynamodb,))

    # Questions section
    with st.container(horizontal=True, vertical_alignment="center", height=48, border=False):
        st.subheader(f"Questions ({num_questions} total)", anchor=False, width="content")
        st.button("View Random Question", on_click=random_question,args=(dynamodb,questions, topic_map),disabled=(num_questions==0),help="No questions found." if (num_questions==0) else None) 
    search = st.text_input("Search",placeholder="Search questions or topics...", autocomplete="off")

    if search:
        search = search.lower()
        questions = [
            question
            for question in questions
            if search in question["question"].lower()
            or any(
                search in topic_map.get(topic_id, "").lower()
                for topic_id in dynamodb.get_question_topics(question["SK"])
            )
        ]

    questions.sort(key=lambda question: question["question"].lower())

    # useful for debugging, shows first 5 questions and its topics
    if(DEBUG_MODE and not(num_questions == 0 and num_topics == 0)):
        print(f"questions: {questions}")
        print(f"topics: {topic_map}")
        for i, question in enumerate(questions):
            topic_ids = dynamodb.get_question_topics(question["SK"])
            topic_names = [
                topic_map.get(topic_id, f"Unknown Topic {topic_id}")
                for topic_id in topic_ids
            ]
            print(f'{question["question"]} | {", ".join(topic_names)}')
            if i == 9: # limit to 10 questions
                break
        print()

    # question button for each question
    for question in questions:
        current_question = question["question"]
        current_question_len = len(current_question)
        st.button(
            label = current_question if current_question_len < QUESTION_BUTTON_MAX_TEXT_LEN else current_question[:QUESTION_BUTTON_MAX_TEXT_LEN] + "...",
            key=f"select_{question['SK']}",
            on_click=load_question_to_form,
            args=(question,dynamodb),
            use_container_width=True,
        )

# python -m streamlit run app.py
if __name__ == "__main__":
    main()