"""Streamlit interface for PawPal+'s tested, UI-independent domain model."""

import csv
from dataclasses import replace
from datetime import date, time
from io import StringIO

import streamlit as st

from main import create_demo_owner
from pawpal_system import FREQUENCIES, PRIORITIES, Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+ | Pet care, planned", page_icon="🐾", layout="wide")
st.markdown("""
<style>
.stApp {background: #f6f9f7;}
.block-container {max-width: 1160px; padding-top: 2.5rem;}
h1, h2, h3 {color: #173f35;}
[data-testid="stMetric"] {background: white; border: 1px solid #dde9e2;
    border-radius: 14px; padding: 16px 20px;}
[data-testid="stSidebar"] {background: #eaf2ed;}
[data-testid="stSidebar"] .block-container {padding-top: 1.5rem;}
.eyebrow {font-size: .78rem; letter-spacing: .16em; font-weight: 700; color: #527765;}
.hero-note {color: #5b7066; font-size: 1.08rem; margin-bottom: 1.5rem;}
</style>
""", unsafe_allow_html=True)

if "owner" not in st.session_state:
    st.session_state.owner = Owner("Jordan")
if "show_plan" not in st.session_state:
    st.session_state.show_plan = False


def notice(message: str) -> None:
    """Show a one-time confirmation after a state-changing rerun."""
    st.session_state.notice = message
    st.rerun()


with st.sidebar:
    st.title("🐾 PawPal+")
    st.caption("A little care. A better day.")
    if st.button("Load sample household", key="load_demo",
                 disabled=bool(st.session_state.owner.pets),
                 help="Try two pets, a time conflict, and recurring routines in an empty household."):
        st.session_state.owner = create_demo_owner(date.today())
        st.session_state.show_plan = True
        for key in ("owner_name", "budget", "hours_start", "hours_end"):
            st.session_state.pop(key, None)
        notice("Sample household loaded. Explore the plan, then edit a task or mark one complete.")

    owner = st.session_state.owner
    st.subheader("Your preferences")
    with st.form("owner_preferences"):
        owner_name = st.text_input("Owner name", value=owner.name, key="owner_name")
        budget = st.number_input("Remaining care budget (minutes)", 0, 1440,
                                 owner.available_minutes, step=5, key="budget")
        first, second = st.columns(2)
        hours_start = first.time_input("Available from", owner.day_start, step=60, key="hours_start")
        hours_end = second.time_input("Available until", owner.day_end, step=60, key="hours_end")
        save_preferences = st.form_submit_button("Save preferences", width="stretch")
    if save_preferences:
        try:
            st.session_state.owner = replace(owner, name=owner_name.strip(),
                                             available_minutes=int(budget),
                                             day_start=hours_start, day_end=hours_end)
        except ValueError as exc:
            st.error(str(exc))
        else:
            notice("Preferences saved.")

    st.divider()
    st.subheader("Add a pet")
    with st.form("add_pet", clear_on_submit=True):
        pet_name = st.text_input("Pet name", key="pet_name")
        species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"], key="species")
        add_pet = st.form_submit_button("Add pet", width="stretch")
    if add_pet:
        try:
            owner.add_pet(Pet(pet_name, species))
        except ValueError as exc:
            st.error(str(exc))
        else:
            notice(f"{pet_name.strip()} joined your household.")
    st.caption("Session data stays while this browser session is active. Download a plan to keep a copy.")

owner = st.session_state.owner
scheduler = Scheduler(owner)
st.markdown('<div class="eyebrow">YOUR HOUSEHOLD, IN HARMONY</div>', unsafe_allow_html=True)
st.title("Small routines. Happier pets.")
st.markdown('<div class="hero-note">Plan the essentials, spot overlaps, and make time for every pet.</div>',
            unsafe_allow_html=True)
if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))

left, right = st.columns([2, 1])
with left:
    st.write(f"**Care coordinator:** {owner.name}")
with right:
    plan_date = st.date_input("Plan date", value=date.today(), key="plan_date")

due = scheduler.filter_tasks(on_date=plan_date)
pending = [(pet, task) for pet, task in due if not task.completed]
done = len(due) - len(pending)
cards = st.columns(4)
cards[0].metric("Pets", len(owner.pets))
cards[1].metric("Due on this date", len(due))
cards[2].metric("Completed", done)
cards[3].metric("Care budget", f"{owner.available_minutes} min")

plan_tab, tasks_tab, about_tab = st.tabs(["Daily plan", "Pets & tasks", "How it works"])

with plan_tab:
    st.subheader(f"A plan for {plan_date:%A, %B %d}")
    st.caption("High priority first when choosing tasks. Your finished plan is displayed in time order.")
    if not owner.pets:
        st.info("Add your first pet in the sidebar, or load the sample household to explore a complete example.")
    elif not due:
        st.info("No tasks are due on this date. Add a task in Pets & tasks, or choose another date.")
    elif not pending:
        st.success("All tasks due on this date are complete. Check the next date for recurring care.")

    conflicts = scheduler.detect_conflicts(plan_date)
    pet_by_task = {task.id: pet.name for pet, task in owner.get_all_tasks()}
    if conflicts:
        st.warning(f"{len(conflicts)} overlapping task pair(s) need attention. Edit their times in Pets & tasks.")
        with st.expander("See conflict details"):
            for first, second in conflicts:
                st.write(f"• {pet_by_task[first.id]}: {first.description} ({first.scheduled_time:%H:%M}) "
                         f"overlaps {pet_by_task[second.id]}: {second.description} ({second.scheduled_time:%H:%M}).")

    if st.button("Generate schedule", type="primary", disabled=not pending, key="generate"):
        st.session_state.show_plan = True
    if st.session_state.show_plan and pending:
        # Recompute from current objects so editing/completion never leaves a stale plan.
        plan = scheduler.generate_schedule(plan_date)
        st.write(f"**{len(plan.scheduled)} tasks planned · {plan.total_minutes} / "
                 f"{owner.available_minutes} minutes used**")
        if plan.scheduled:
            st.dataframe(plan.to_rows(), hide_index=True, width="stretch")
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=list(plan.to_rows()[0]))
            writer.writeheader()
            writer.writerows(plan.to_rows())
            st.download_button("Download plan as CSV", output.getvalue(),
                               file_name=f"pawpal-plan-{plan_date}.csv", mime="text/csv", key="download_plan")
        else:
            st.info("No pending tasks fit these constraints. Review your available hours, care budget, and task times.")
        if plan.skipped:
            st.subheader("Needs your attention")
            st.caption("These tasks remain pending. Adjust their times or your budget, then generate again.")
            st.dataframe([{"Pet": pet.name, "Task": task.description, "Priority": task.priority,
                           "Reason": reason} for pet, task, reason in plan.skipped],
                         hide_index=True, width="stretch")
        st.caption("Fixed task times are preserved. Conflicting tasks are flagged for you to review.")

with tasks_tab:
    st.subheader("Care starts with a routine")
    if not owner.pets:
        st.info("Add a pet in the sidebar to create your first care task.")
    else:
        pet_lookup = {pet.id: pet for pet in owner.pets}
        pet_id = st.selectbox("Pet to manage", list(pet_lookup),
                             format_func=lambda key: f"{pet_lookup[key].name} · {pet_lookup[key].species}",
                             key="manage_pet")
        pet = pet_lookup[pet_id]
        editable = {task.id: task for task in pet.tasks if not task.completed}
        task_id = st.selectbox("Create or edit", ["new", *editable],
                              format_func=lambda key: "New task" if key == "new" else
                              f"{editable[key].description} · {editable[key].due_date} {editable[key].scheduled_time:%H:%M}",
                              key=f"editor_{pet.id}")
        editing = editable.get(task_id)
        with st.form(f"task_form_{pet.id}_{task_id}", clear_on_submit=editing is None):
            title = st.text_input("Task description", value=editing.description if editing else "",
                                 key=f"title_{pet.id}_{task_id}")
            columns = st.columns(3)
            at = columns[0].time_input("Start time", editing.scheduled_time if editing else time(8), step=60)
            duration = columns[1].number_input("Duration (minutes)", 1, 1440,
                                              editing.duration_minutes if editing else 15)
            priority = columns[2].selectbox("Priority", PRIORITIES,
                                            index=PRIORITIES.index(editing.priority) if editing else 1)
            a, b = st.columns(2)
            frequency = a.selectbox("Repeat", FREQUENCIES,
                                    index=FREQUENCIES.index(editing.frequency) if editing else 0)
            due_date = b.date_input("Due date", editing.due_date if editing else plan_date)
            save_task = st.form_submit_button("Save changes" if editing else "Add task",
                                             type="primary", width="stretch")
        if save_task:
            changes = dict(description=title, scheduled_time=at, duration_minutes=int(duration),
                           priority=priority, frequency=frequency, due_date=due_date)
            try:
                if editing:
                    pet.update_task(editing.id, **changes)
                else:
                    pet.add_task(Task(**changes))
            except ValueError as exc:
                st.error(str(exc))
            else:
                notice("Task updated." if editing else "Task added.")
        st.caption("Repeating tasks create one new dated instance when completed. Edits apply to this occurrence.")

        st.divider()
        st.subheader("Your care list")
        filters = st.columns(3)
        view_pet = filters[0].selectbox("Filter by pet", ["all", *pet_lookup],
                                       format_func=lambda key: "All pets" if key == "all" else pet_lookup[key].name,
                                       key="filter_pet")
        status = filters[1].selectbox("Status", ["All", "Pending", "Completed"], key="filter_status")
        scope = filters[2].selectbox("Dates", ["Selected date", "All dates"], key="filter_dates")
        visible = scheduler.sort_by_time(scheduler.filter_tasks(
            pet_id=None if view_pet == "all" else view_pet,
            completed={"All": None, "Pending": False, "Completed": True}[status],
            on_date=plan_date if scope == "Selected date" else None))
        if not visible:
            st.info("No tasks match these filters.")
        for task_pet, task in visible:
            status_icon = "✅" if task.completed else "○"
            with st.expander(f"{status_icon} {task.scheduled_time:%H:%M} · {task_pet.name} · {task.description}"):
                st.write(f"**{task.due_date}** · {task.duration_minutes} min · "
                         f"{task.priority.title()} priority · Repeats: {task.frequency}")
                a, b = st.columns([3, 1])
                if task.completed:
                    if a.button("Undo completion", key=f"undo_{task.id}"):
                        task_pet.mark_task_incomplete(task.id)
                        notice("Task marked pending. Its future occurrence is preserved.")
                elif a.button("Mark complete", key=f"complete_{task.id}"):
                    following = task_pet.mark_task_complete(task.id)
                    message = f"Completed {task.description}."
                    if following:
                        message += f" Next occurrence: {following.due_date} at {following.scheduled_time:%H:%M}."
                    notice(message)
                if b.button("Delete task", key=f"delete_{task.id}"):
                    task_pet.remove_task(task.id)
                    notice("Task occurrence removed.")

with about_tab:
    st.subheader("A clear plan, with clear reasons")
    st.markdown("""
1. **Build your household.** Add an owner and one or more pets.
2. **Set your limits.** Choose your available hours and remaining minutes for care.
3. **Add tasks.** Choose a date, start time, duration, priority, and repeat frequency.
4. **Generate a plan.** High-priority tasks are considered first; ties use time, then duration.
5. **Review and complete.** Adjust conflicts or skipped tasks. Completion creates the next daily or weekly instance.

The scheduler considers every pet through the owner's shared task collection. It detects full
interval overlaps, including across pets. Back-to-back tasks are allowed.

The care budget covers **pending work**. Completed tasks stay in your history and do not use
the remaining budget. A repeating task advances from its due date when completed; missed tasks
remain on their original dates and are visible using **All dates**.

Your session holds the household while you use the app. CSV exports preserve the selected plan;
closing or refreshing the connection can reset the household. No account or API key is required.
""")

