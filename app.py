import streamlit as st
from dynamodb import get_questions, create_question, update_question, delete_question

# clear question data from state so form does not populate on rerun
def clear_fields():
    st.session_state.form_question = ""
    st.session_state.form_answer_url = ""
    st.session_state.form_topic = ""

# clear fields and go back to Add mode
def reset_form():
    st.session_state.editing_id = None
    clear_fields()

# place question data into session variable so it will populate form on rerun
def load_question(question):
    st.session_state.editing_id = question["question_id"]
    st.session_state.form_question = question["question"]
    st.session_state.form_answer_url = question.get("answer_url", "")
    st.session_state.form_topic = question.get("topic", "")

def save_question():
    question = st.session_state.form_question.strip()
    answer_url = st.session_state.form_answer_url.strip()
    topic = st.session_state.form_topic.strip()

    if not question:
        st.session_state.toast_status = "error"
        st.session_state.message = "Question is required."
        return

    if st.session_state.editing_id:
        update_question(st.session_state.editing_id,question,answer_url,topic)
        st.session_state.message = "Question updated."
    else:
        create_question(question,answer_url,topic)
        st.session_state.message = "Question added."

    reset_form()

@st.dialog("Delete Question")
def confirm_delete():
    st.warning("This will permanently delete the question! Are you sure?")

    with st.container(horizontal=True):
        if st.button("Cancel"):
            st.rerun()

        if st.button("Delete", type="primary"):
            delete_question(st.session_state.editing_id)
            st.session_state.message = "Question deleted."
            reset_form()
            st.rerun()

def main():
    # we're either in edit mode or add mode. if we have an editing_id, we know we're in edit mode
    st.session_state.setdefault("editing_id", None)

    # toast doesn't accept color argument, so we need a custom css override
    toast_color = "#198754"
    if st.session_state.get("toast_status") == "error":
        toast_color = "#dc3545"
    st.html(f"""
    <style>
    [data-testid="stToast"] {{
        background-color: {toast_color} !important;
        color: white !important;
    }}
    </style>
    """)

    st.set_page_config(page_title="Study Bank",page_icon="📚")
    st.title("Study Bank Question Modifier", anchor=False)

    if message := st.session_state.pop("message", None):
        st.toast(message)

    if error := st.session_state.pop("error", None):
        st.error(error)


    # Add / Edit Header
    with st.container(horizontal=True, vertical_alignment="center", height=72, border=False):
        # edit mode
        if st.session_state.editing_id:
            st.subheader("Edit Question", width="content", anchor=False)
            st.button("Switch to Add Question", on_click=reset_form, type="primary")
        # add mode
        else:
            st.subheader("Add Question", width="content", anchor=False)

    # the actual form
    with st.form("question_form", enter_to_submit=False):
        st.text_area("Question", key="form_question", height=70)
        st.text_input("Reference URL", key="form_answer_url", autocomplete="off")
        st.text_input("Topic", key="form_topic", autocomplete="off")

        save_col, delete_col = st.columns(2)
        with st.container(horizontal=True):
            st.form_submit_button("Save", on_click=save_question, type="primary", width="content")
            st.form_submit_button("Clear Fields", on_click=clear_fields, width="content")

            if st.session_state.editing_id:
                st.form_submit_button("Delete", on_click=confirm_delete, width="content")

    # Questions section
    with st.container(gap="xxsmall"):
        st.subheader("Questions", anchor=False)
        search = st.text_input("Search",placeholder="Search questions or topics...", autocomplete="off")

    # todo only fetch questions on initialization otherwise it will full table scan on every button press
    questions = get_questions()

    if search:
        search = search.lower()

        questions = [
            question
            for question in questions
            if search in question["question"].lower()
            or search in question.get("topic", "").lower()
        ]

    questions.sort(key=lambda question: question["question"].lower())

    for question in questions:
        st.button(
            question["question"],
            key=f"select_{question['question_id']}",
            on_click=load_question,
            args=(question,),
            use_container_width=True,
        )

if __name__ == "__main__":
    main()