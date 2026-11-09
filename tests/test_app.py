"""Exercise real Streamlit forms and session state through AppTest."""

from datetime import date, time, timedelta
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def start_demo():
    app = AppTest.from_file(str(APP), default_timeout=15).run()
    app.button(key="load_demo").click().run()
    assert not app.exception
    return app


def field(elements, label):
    return next(element for element in elements if element.label == label)


def click(app, label):
    field(app.button, label).click().run()
    assert not app.exception


def test_empty_state_and_add_two_pets_survive_reruns():
    app = AppTest.from_file(str(APP), default_timeout=15).run()
    assert not app.exception and app.metric[0].value == "0"
    for name in ["Mochi", "Luna"]:
        app.text_input(key="pet_name").input(name)
        click(app, "Add pet")
    app.run()
    assert [pet.name for pet in app.session_state.owner.pets] == ["Mochi", "Luna"]
    assert app.metric[0].value == "2"


def test_blank_pet_validation_does_not_create_pet():
    app = AppTest.from_file(str(APP), default_timeout=15).run()
    app.text_input(key="pet_name").input(" ")
    click(app, "Add pet")
    assert app.error and app.session_state.owner.pets == []


def test_demo_generates_explained_plan_and_conflict_warning():
    app = start_demo()
    assert app.metric[0].value == "2"
    assert "overlapping" in app.warning[0].value
    selected = app.dataframe[0].value
    assert list(selected["Task"]) == ["Morning walk", "Medication reminder", "Playtime"]
    assert sum(selected["Minutes"]) == 60
    assert "Conflicts" in app.dataframe[1].value.iloc[0]["Reason"]
    assert "Why" in selected.columns


def test_add_and_edit_task_through_ui_reaches_backend():
    app = start_demo()
    field(app.text_input, "Task description").input("Training")
    field(app.time_input, "Start time").set_value(time(12))
    field(app.number_input, "Duration (minutes)").set_value(10)
    click(app, "Add task")
    pet = app.session_state.owner.pets[0]
    task = next(task for task in pet.tasks if task.description == "Training")
    assert task.duration_minutes == 10 and task.scheduled_time == time(12)
    app.selectbox(key=f"editor_{pet.id}").select(task.id).run()
    field(app.text_input, "Task description").input("Gentle training")
    field(app.number_input, "Duration (minutes)").set_value(5)
    click(app, "Save changes")
    edited = app.session_state.owner.pets[0].get_task(task.id)
    assert edited.description == "Gentle training" and edited.duration_minutes == 5
    assert not app.exception


def test_completion_creates_next_task_and_updates_plan_and_filters():
    app = start_demo()
    pet = app.session_state.owner.pets[0]
    walk = next(task for task in pet.tasks if task.description == "Morning walk")
    app.button(key=f"complete_{walk.id}").click().run()
    assert not app.exception
    assert walk.completed and len(pet.tasks) == 3
    following = next(task for task in pet.tasks if task.series_id == walk.series_id and task.id != walk.id)
    assert following.due_date == date.today() + timedelta(days=1) and not following.completed
    assert not app.warning  # Completing the walk removes its pending conflict.
    assert "Morning walk" not in list(app.dataframe[0].value["Task"])
    app.selectbox(key="filter_status").select("Completed").run()
    complete_buttons = [button for button in app.button if button.key and button.key.startswith("complete_")]
    assert not complete_buttons
    assert app.button(key=f"undo_{walk.id}")
    app.date_input(key="plan_date").set_value(following.due_date).run()
    assert app.metric[1].value == "1"


def test_delete_removes_task_and_refreshes_plan():
    app = start_demo()
    pet = app.session_state.owner.pets[0]
    walk = next(task for task in pet.tasks if task.description == "Morning walk")
    app.button(key=f"delete_{walk.id}").click().run()
    assert not app.exception
    assert all(task.id != walk.id for task in pet.tasks)
    assert "Morning walk" not in list(app.dataframe[0].value["Task"])


def test_owner_budget_saved_and_invalid_hours_preserve_previous_preferences():
    app = start_demo()
    app.number_input(key="budget").set_value(10)
    click(app, "Save preferences")
    assert app.session_state.owner.available_minutes == 10
    assert sum(app.dataframe[0].value["Minutes"]) == 10
    app.time_input(key="hours_start").set_value(time(21))
    app.time_input(key="hours_end").set_value(time(7))
    click(app, "Save preferences")
    assert app.error
    assert app.session_state.owner.day_start == time(7)
    assert app.session_state.owner.day_end == time(21)


def test_filter_pet_and_all_dates_uses_stable_pet_ids():
    app = start_demo()
    cat = app.session_state.owner.pets[1]
    app.selectbox(key="filter_pet").select(cat.id).run()
    app.selectbox(key="filter_dates").select("All dates").run()
    visible_task_keys = [button.key for button in app.button if button.key and button.key.startswith("complete_")]
    assert set(visible_task_keys) == {f"complete_{task.id}" for task in cat.tasks}
