import streamlit as st
import random
from dynamodb import check_topic_has_references, get_entries, create_question, update_question, delete_question, create_topic, update_topic, delete_topic

RED = "#FF4B4B"
GREEN = "#198754"

# temporary pop up message
def toast(message, status = None):
    if status:
        st.session_state.toast_status = status
    st.session_state.message = message

# result of get_entries is cached and should be cleared after CUD operations so UI has updated data
def clear_get_entries_cache(entry_type):
    get_entries.clear(entry_type)
    print(f"{entry_type.lower()} cache cleared")

# clear question data from state so form does not populate on rerun
def clear_fields():
    st.session_state.form_question = ""
    st.session_state.form_reference_url = ""
    st.session_state.form_topic_id = None

# clear fields and go back to Add mode
def reset_form():
    st.session_state.editing_id = None
    clear_fields()

def clear_topic_field():
    st.session_state.form_topic_id = None

# place question data into session variable so it will populate form on rerun
def load_question_to_form(question):
    st.session_state.editing_id = question["UUID"]
    st.session_state.form_question = question["question"]
    st.session_state.form_reference_url = question.get("reference_url", "")
    st.session_state.form_topic_id = question.get("topic_id")

def save_question():
    question = st.session_state.form_question.strip()
    reference_url = st.session_state.form_reference_url.strip()
    topic_id = st.session_state.form_topic_id

    if not question:
        toast("Question is required.", "error")
        return
    if not topic_id:
        toast("Topic is required.", "error")
        return
    if st.session_state.editing_id:
        update_question(st.session_state.editing_id,question,reference_url,topic_id)
        toast("Question updated.")
    else:
        create_question(question,reference_url,topic_id)
        toast("Question added.")
    clear_get_entries_cache("QUESTION")
    reset_form()

# pop up warning for deleting a question
@st.dialog("Delete Question")
def confirm_delete():
    st.warning("This will permanently delete the question! Are you sure?")

    with st.container(horizontal=True):
        if st.button("Cancel"):
            st.rerun()

        if st.button("Delete", type="primary"):
            delete_question(st.session_state.editing_id)
            toast("Question deleted.")
            reset_form()
            clear_get_entries_cache("QUESTION")
            st.rerun()

def check_duplicate_topic(topic_map, name, topic_id=None):
    normalized_name = name.casefold()

    return any(
        existing_id != topic_id
        and existing_name.casefold() == normalized_name
        for existing_id, existing_name in topic_map.items()
    )

# pop up for viewing a random question 
@st.dialog("Press Space or click the button for a random question", width="medium")
def random_question(questions, topic_map):
    # custom CSS to hide everything except the question
    st.html("""<style>[data-testid="stDialog"] { background: #262730 !important;}</style>""")

    selected_topic = st.selectbox("Topic",options=[None] + list(topic_map.keys()),format_func=lambda id: "Any" if id is None else topic_map[id],index=0)

    # fetch a new question with respect to topic choice
    if st.button("Random Question", shortcut="Space"):
        current_id = st.session_state.get("random_question_id")
        matching_questions = questions if selected_topic is None else [q for q in questions if q["topic_id"] == selected_topic]
        matching_questions = [q for q in matching_questions if q["UUID"] != current_id]
        if matching_questions:
            st.session_state.random_question_id = random.choice(matching_questions)["UUID"]

    # dont display question until user has specified topic selection
    if "random_question_id" not in st.session_state:
        return

    # displaying question
    question = next(q for q in questions if q["UUID"] == st.session_state.random_question_id)
    st.subheader(question['question'], anchor=False)
    st.markdown(f"### Refer: [{question['reference_url']}]({question['reference_url']})")

# pop up for managing topics
@st.dialog("Manage Topics")
def manage_topics(topic_map):
    st.subheader("Add Topic", anchor=False)
    new_topic_name = st.text_input("New Topic", autocomplete="off").strip()
    if st.button("Add", type="primary"):
        if not new_topic_name:
            toast("Topic name is required.", "error")
        elif check_duplicate_topic(topic_map, new_topic_name):
            toast(f"Topic '{new_topic_name}' already exists.", "error")
        else:
            create_topic(new_topic_name)
            clear_get_entries_cache("TOPIC")
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
                toast(f"Topic {name} already exists.", "error")
            else:
                update_topic(topic_id, name.strip())
                toast(f"Updated Topic {name}")
                clear_get_entries_cache("TOPIC")
                reset_form() # user may be editing a question that used this topic, so just reset everything for simplicity
            st.rerun()

        if st.button("Delete"):
            has_refences, reference_count = check_topic_has_references(topic_id)
            if(has_refences):
                toast(f"Topic {name} cannot be deleted because it is referenced by {reference_count} questions.", "error")
            else:
                delete_topic(topic_id)
                toast(f"Deleted topic {name}")
                clear_get_entries_cache("TOPIC")
                clear_topic_field() # if topic was populated before valid deltion, it could linger, so clear this input
            st.rerun()

def main():
    # fetch data from dynamoDB, returned as list which is cached by st
    questions = get_entries("QUESTION") 
    topics = get_entries("TOPIC")
    # map of topic ids to names
    topic_map = {topic["UUID"]: topic["name"] for topic in topics}

    # we're either in edit mode or add mode. if we have an editing_id, we know we're in edit mode
    st.session_state.setdefault("editing_id", None)

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

    # Add / Edit Header
    with st.container(horizontal=True, vertical_alignment="center", height=72, border=False):
        # edit mode
        if st.session_state.editing_id:
            st.subheader("Edit Question", width="content", anchor=False)
            st.button("Switch to Add Question", on_click=reset_form, type="primary")
        # add mode
        else:
            st.subheader("Add Question", width="content", anchor=False)
        st.button("Manage Topics", on_click=manage_topics, args=(topic_map,)) # trailing comma forces tuple for *args pass
        
    # the actual form
    with st.form("question_form", enter_to_submit=False):
        # question label will display UUID of question in edit mode
        question_label = f'({st.session_state.editing_id})' if st.session_state.editing_id is not None else ''

        st.text_area(f"Question {question_label}", key="form_question", height=70)
        st.text_input("Reference URL", key="form_reference_url", autocomplete="off")
        topic_id = st.selectbox(
            "Topic",
            options=list(topic_map.keys()),
            format_func=lambda id: topic_map[id],
            key="form_topic_id", index=None,
            help="Create a topic with the Manage Topics button" if not topics else None
        )

        with st.container(horizontal=True):
            st.form_submit_button("Save", on_click=save_question, type="primary", width="content",disabled=not topics,help="Create a topic first. Questions require a topic." if not topics else None)
            st.form_submit_button("Clear Fields", on_click=clear_fields, width="content")

            if st.session_state.editing_id:
                st.form_submit_button("Delete", on_click=confirm_delete, width="content")

    # Questions section
    with st.container(horizontal=True, vertical_alignment="center", height=48, border=False):
        st.subheader(f"Questions ({len(questions)} total)", anchor=False, width="content")
        st.button("View Random Question", on_click=random_question,args=(questions, topic_map),disabled=(len(questions)==0),help="No questions found." if (len(questions)==0) else None) 
    search = st.text_input("Search",placeholder="Search questions or topics...", autocomplete="off")

    if search:
        search = search.lower()
        questions = [
            question
            for question in questions
            if search in question["question"].lower()
            or search in topic_map.get(question.get("topic_id"), "").lower()
        ]

    questions.sort(key=lambda question: question["question"].lower())

    # useful for debugging, shows each question and its topic name
    # for question in questions:
    #     topic_name = topic_map.get(question.get("topic_id"), "Unknown Topic")
    #     print(f'{question["question"]} | {topic_name}')
    # print()

    # question button for each question
    for question in questions:
        st.button(
            question["question"],
            key=f"select_{question['UUID']}",
            on_click=load_question_to_form,
            args=(question,),
            use_container_width=True,
        )

# python -m streamlit run app.py
if __name__ == "__main__":
    main()