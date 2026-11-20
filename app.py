"""
SkillPath AI – AI-Powered Corporate Employee Upskilling Platform
Main Streamlit Application with Modern Bright Pastel UI, Coursera-Inspired Navigation,
Fixed Non-Interactive Plotly Visualizations, and Explainable AI Engine.
"""
import re
from typing import Dict, Any, Optional
import streamlit as st
import pandas as pd
import numpy as np

from config import PROFICIENCY_LEVELS, SKILL_CATEGORIES, STANDARD_ROLES, DEPARTMENTS
from database import (
    init_db,
    get_all_employees,
    get_employee_by_id,
    get_all_skills,
    get_skills_by_category,
    get_employee_skills,
    get_employee_enrollments,
    get_all_courses,
    get_preference,
    set_preference,
    clear_preference,
    is_employee_code_taken,
    save_employee_profile_details,
)
from modules.assessment import (
    validate_employee_input,
    save_or_update_employee,
    save_employee_skill_assessment,
    score_diagnostic_quiz,
    apply_diagnostic_results,
    DIAGNOSTIC_QUESTIONS
)
from modules.skill_gap import (
    analyze_skill_gap,
    create_radar_chart,
    create_gap_bar_chart
)
from modules.recommender import recommend_courses
from modules.roadmap import (
    generate_learning_roadmap,
    create_roadmap_timeline_chart
)
from modules.tracker import (
    enroll_employee_in_course,
    update_course_progress,
    log_learning_activity,
    get_employee_tracker_summary
)
from modules.analytics import (
    get_workforce_overview,
    create_department_readiness_chart,
    create_org_gaps_chart,
    create_talent_mobility_donut,
    create_skill_distribution_heatmap
)
from modules.ui_theme import (
    apply_custom_theme,
    render_top_hero_banner,
    render_section_header,
    render_roadmap_step_card,
    render_course_card,
    render_skill_progress_item,
    render_static_chart,
    load_lottie_file,
    render_lottie,
    polish_fig
)

# Page configuration
st.set_page_config(
    page_title="SkillPath AI | Corporate Upskilling Platform",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
init_db()

# Apply Bright Pastel Theme & Custom CSS
apply_custom_theme()

# -------------------------------------------------------------
# PERSISTENT NAVIGATION CONSTANTS & HELPERS
# -------------------------------------------------------------
PAGE_EMPLOYEE_INFO = "👤 Employee Information"
PAGE_DASHBOARD = "🏠 Dashboard"
PAGE_SKILL_ASSESSMENT = "📝 Skill Assessment"
PAGE_SKILL_GAP = "🎯 Skill Gap Analyzer"
PAGE_PERSONALIZED_LEARNING = "💡 Personalized Learning"
PAGE_PROGRESS_TRACKING = "📈 Progress Tracking"
PAGE_HR_DASHBOARD = "📊 HR Dashboard"

NAV_PAGES = [
    PAGE_EMPLOYEE_INFO,
    PAGE_DASHBOARD,
    PAGE_SKILL_ASSESSMENT,
    PAGE_SKILL_GAP,
    PAGE_PERSONALIZED_LEARNING,
    PAGE_PROGRESS_TRACKING,
    PAGE_HR_DASHBOARD
]


def navigate_to(page_name: str) -> None:
    """Directly switches page and safely triggers a clean rerun."""
    st.session_state["nav_page"] = page_name
    st.rerun()


# Determine Active Employee Context
employees_df = get_all_employees()

# Initial page routing on first launch
if "nav_page" not in st.session_state:
    saved_pref = get_preference("active_employee_id")
    if saved_pref:
        st.session_state["nav_page"] = PAGE_DASHBOARD
        try:
            st.session_state["active_employee_id"] = int(saved_pref)
        except (ValueError, TypeError):
            st.session_state["active_employee_id"] = int(employees_df.iloc[0]["id"]) if not employees_df.empty else None
    else:
        # First time opening SkillPath AI -> start with Employee Information
        st.session_state["nav_page"] = PAGE_EMPLOYEE_INFO
        st.session_state["active_employee_id"] = None
        st.session_state["is_onboarding_new"] = True

# Handle Active Employee State
active_emp_id = st.session_state.get("active_employee_id")
if active_emp_id is None and not st.session_state.get("is_onboarding_new", False) and not employees_df.empty:
    active_emp_id = int(employees_df.iloc[0]["id"])
    st.session_state["active_employee_id"] = active_emp_id

active_emp: Optional[Dict[str, Any]] = None
if active_emp_id:
    active_emp = get_employee_by_id(active_emp_id)
    if not active_emp and not employees_df.empty:
        active_emp_id = int(employees_df.iloc[0]["id"])
        st.session_state["active_employee_id"] = active_emp_id
        active_emp = get_employee_by_id(active_emp_id)

current_emp_id = active_emp["id"] if active_emp else None


# -------------------------------------------------------------
# -------------------------------------------------------------
# TOP NAVIGATION BAR (Horizontal) & CONTEXT
# -------------------------------------------------------------
col_nav_left, col_nav_center, col_nav_right = st.columns([1, 3, 2])

# Left: Logo and App Name
with col_nav_left:
    st.image("https://img.icons8.com/isometric/100/compass--v1.png", width=40)
    st.title("SkillPath AI")

# Center: Page Navigation
with col_nav_center:
    # Determine default selected index based on session state or fallback to Dashboard
    default_idx = 0
    try:
        default_idx = NAV_PAGES.index(st.session_state.get("nav_page", PAGE_DASHBOARD))
    except ValueError:
        default_idx = 0
    selected_page = st.radio(
        "",
        NAV_PAGES,
        index=default_idx,
        key="nav_page",
        horizontal=True,
    )

# Right: Employee selector and profile summary
with col_nav_right:
    # Employee selector dropdown
    emp_options = {}
    for _, row in employees_df.iterrows():
        code = row.get("employee_code") or f"EMP-{row['id']:04d}"
        emp_options[f"👤 {row['name']} ({code} · {row['current_role']})"] = int(row["id"])
    emp_options["➕ Onboard New Employee"] = "new"
    # Determine default employee selection index
    default_selection_idx = 0
    if st.session_state.get("is_onboarding_new"):
        default_selection_idx = len(emp_options) - 1
    elif current_emp_id:
        for idx, (label, eid) in enumerate(emp_options.items()):
            if eid == current_emp_id:
                default_selection_idx = idx
                break
    selected_emp_label = st.selectbox(
        "👤 Active Employee",
        list(emp_options.keys()),
        index=default_selection_idx,
        key="active_emp_selectbox",
    )
    selected_val = emp_options[selected_emp_label]
    if selected_val == "new":
        if not st.session_state.get("is_onboarding_new"):
            st.session_state["is_onboarding_new"] = True
            st.session_state["active_employee_id"] = None
            navigate_to(PAGE_EMPLOYEE_INFO)
    else:
        if st.session_state.get("is_onboarding_new") or st.session_state["active_employee_id"] != selected_val:
            st.session_state["is_onboarding_new"] = False
            st.session_state["active_employee_id"] = selected_val
            set_preference("active_employee_id", str(selected_val))
            st.rerun()
    # Profile summary expander (collapsed)
    if active_emp:
        emp_code = active_emp.get("employee_code") or f"EMP-{active_emp['id']:04d}"
        with st.expander(f"👤 {active_emp['name']} ({emp_code})", expanded=False):
            st.write(f"🏢 **Department:** {active_emp['department']}")
            st.write(f"💼 **Designation:** {active_emp['current_role']}")
            st.write(f"🎯 **Target Role:** {active_emp['target_role']}")
            st.write(f"💼 **Experience:** {active_emp['experience_years']} yrs")
            st.write(f"⏱️ **Weekly Commitment:** {active_emp['weekly_learning_hours']} hrs/wk")
            if active_emp.get("career_interests"):
                st.write(f"🌟 **Interests:** {active_emp['career_interests']}")
    # Admin & Demo controls (compact row)
    if st.button("🔄 Reset Demo Seed Data", use_container_width=True):
        init_db(force_reseed=True)
        clear_preference("active_employee_id")
        st.session_state.clear()
        st.success("✅ Database re-seeded with realistic enterprise data!")
        st.rerun()

# -------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/isometric/100/compass--v1.png", width=68)
st.sidebar.title("🎯 SkillPath AI")
st.sidebar.caption("✨ Enterprise Talent Intelligence & Upskilling")

# Clean, Persistent Left Sidebar Navigation Radio
selected_page = st.sidebar.radio(
    "🧭 Navigation Menu",
    NAV_PAGES,
    key="nav_page"
)

st.sidebar.markdown("---")

# Employee Context & Switching Dropdown
emp_options = {}
for _, row in employees_df.iterrows():
    code = row.get("employee_code") or f"EMP-{row['id']:04d}"
    emp_options[f"👤 {row['name']} ({code} · {row['current_role']})"] = int(row["id"])
emp_options["➕ Onboard New Employee"] = "new"

# Match current selection index
default_selection_idx = 0
if st.session_state.get("is_onboarding_new"):
    default_selection_idx = len(emp_options) - 1
elif current_emp_id:
    for idx, (label, eid) in enumerate(emp_options.items()):
        if eid == current_emp_id:
            default_selection_idx = idx
            break

selected_emp_label = st.sidebar.selectbox(
    "👤 Active Employee View",
    list(emp_options.keys()),
    index=default_selection_idx,
    key="active_emp_selectbox"
)

selected_val = emp_options[selected_emp_label]
if selected_val == "new":
    if not st.session_state.get("is_onboarding_new"):
        st.session_state["is_onboarding_new"] = True
        st.session_state["active_employee_id"] = None
        navigate_to(PAGE_EMPLOYEE_INFO)
else:
    if st.session_state.get("is_onboarding_new") or st.session_state.get("active_employee_id") != selected_val:
        st.session_state["is_onboarding_new"] = False
        st.session_state["active_employee_id"] = selected_val
        set_preference("active_employee_id", str(selected_val))
        st.rerun()

# Sidebar Employee Profile Summary Card
if active_emp:
    emp_code = active_emp.get("employee_code") or f"EMP-{active_emp['id']:04d}"
    with st.sidebar.expander(f"👤 {active_emp['name']} ({emp_code})", expanded=True):
        st.write(f"🏢 **Department:** {active_emp['department']}")
        st.write(f"💼 **Designation:** {active_emp['current_role']}")
        st.write(f"🎯 **Target Role:** {active_emp['target_role']}")
        st.write(f"💼 **Experience:** {active_emp['experience_years']} yrs")
        st.write(f"⏱️ **Weekly Commitment:** {active_emp['weekly_learning_hours']} hrs/wk")
        if active_emp.get("career_interests"):
            st.write(f"🌟 **Interests:** {active_emp['career_interests']}")

st.sidebar.markdown("---")

# Admin & Demo Seed Controls
with st.sidebar.expander("⚙️ System & Demo Controls"):
    if st.button("🔄 Reset Demo Seed Data", use_container_width=True):
        init_db(force_reseed=True)
        clear_preference("active_employee_id")
        st.session_state.clear()
        st.success("✅ Database re-seeded with realistic enterprise data!")
        st.rerun()

# Top Hero Banner (Always visible for maximum brand engagement)
render_top_hero_banner(
    employee_name=active_emp["name"] if active_emp else None,
    target_role=active_emp["target_role"] if active_emp else None
)


# =============================================================
# PAGE 1: EMPLOYEE INFORMATION – ONBOARDING & PROFILE SETUP
# =============================================================
if selected_page == PAGE_EMPLOYEE_INFO:
    render_section_header(
        title="👤 Employee Information & Learning Setup",
        subtitle="Establish your professional profile, aspirational target role, current skillset, and personalized learning commitment.",
        badge="🎓 COURSERA-INSPIRED PROFILE & SETUP",
        lottie_filename="growth.json",
        image_url="https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=600&q=80",
        anim_height=160,
        key_prefix="onboarding_header"
    )

    is_editing_existing = (active_emp is not None and not st.session_state.get("is_onboarding_new", False))

    if is_editing_existing:
        col_hdr1, col_hdr2 = st.columns([3, 1])
        emp_display_code = active_emp.get("employee_code") or f"EMP-{active_emp['id']:04d}"
        with col_hdr1:
            st.info(f"👤 **Viewing & Editing Profile for:** **{active_emp['name']}** ({emp_display_code}). Your saved information is loaded below and preserved across sessions.")
        with col_hdr2:
            if st.button("🏠 Return to Dashboard", key="btn_return_dash", use_container_width=True):
                navigate_to(PAGE_DASHBOARD)
    else:
        st.markdown("""
        <div class="white-card" style="border-left: 5px solid #6366F1; background: #F8FAFC;">
            <h4 style="margin: 0 0 6px 0; color: #1E293B;">🚀 Welcome to SkillPath AI Onboarding!</h4>
            <p style="margin: 0; color: #64748B; font-size: 0.92rem; line-height: 1.5;">
                Complete your employee profile to unlock personalized skill gap analytics, AI-curated course recommendations, 
                and a phased upskilling roadmap tailored to your career aspirations.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Coursera-Inspired Clean, Organized Form
    with st.form("employee_onboarding_form"):
        st.markdown("### 🏢 Section 1: Personal & Organizational Details")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            form_name = st.text_input(
                "Employee Full Name *",
                value=active_emp["name"] if is_editing_existing else "",
                placeholder="e.g. Maya Chen"
            )
            default_emp_code = (
                active_emp.get("employee_code") or f"EMP-{active_emp['id']:04d}"
                if is_editing_existing
                else f"EMP-{1001 + len(employees_df)}"
            )
            form_code = st.text_input(
                "Employee ID / Code *",
                value=default_emp_code,
                placeholder="e.g. EMP-1045",
                help="Unique enterprise identifier (alphanumeric)."
            )
            default_email = active_emp["email"] if is_editing_existing else ""
            form_email = st.text_input(
                "Corporate Email Address *",
                value=default_email,
                placeholder="e.g. maya.chen@enterprise.com",
                help="Used for notifications and skill credentials."
            )
        with col_p2:
            default_dept_idx = 0
            if is_editing_existing and active_emp["department"] in DEPARTMENTS:
                default_dept_idx = DEPARTMENTS.index(active_emp["department"])
            form_dept = st.selectbox(
                "Department *",
                DEPARTMENTS,
                index=default_dept_idx,
                help="Your primary business or operational unit."
            )
            form_curr_role = st.text_input(
                "Current Job Role / Designation *",
                value=active_emp["current_role"] if is_editing_existing else "",
                placeholder="e.g. Associate Data Analyst",
                help="Your official active designation."
            )

        st.markdown("---")
        st.markdown("### 🎯 Section 2: Career Aspirations & Learning Commitment")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            default_target_idx = 0
            if is_editing_existing and active_emp["target_role"] in STANDARD_ROLES:
                default_target_idx = STANDARD_ROLES.index(active_emp["target_role"])
            form_target_role = st.selectbox(
                "Target Aspirational Role *",
                STANDARD_ROLES,
                index=default_target_idx,
                help="The benchmark role you are upskilling toward."
            )
            form_exp = st.number_input(
                "Years of Professional Experience *",
                min_value=0.0,
                max_value=50.0,
                value=float(active_emp["experience_years"]) if is_editing_existing else 2.0,
                step=0.5,
                help="Total years of professional industry experience."
            )
        with col_c2:
            form_hours = st.number_input(
                "Weekly Learning Commitment (Hours / Week) *",
                min_value=1.0,
                max_value=40.0,
                value=float(active_emp["weekly_learning_hours"]) if is_editing_existing else 5.0,
                step=1.0,
                help="Dedicated weekly hours you can commit to upskilling."
            )
            form_interests = st.text_input(
                "Career Interests & Focus Domains",
                value=active_emp.get("career_interests", "") if is_editing_existing else "",
                placeholder="e.g. Generative AI, Cloud Native Architecture, Technical Leadership",
                help="Key technical or managerial topics you are passionate about exploring."
            )

        st.markdown("---")
        st.markdown("### 🧠 Section 3: Current Capabilities & Learning Goals")
        all_skills_df = get_all_skills()
        skill_catalog_names = all_skills_df["name"].tolist() if not all_skills_df.empty else []

        # Pre-select skills already assessed for this employee
        preselected_skills = []
        if is_editing_existing:
            emp_sk_df = get_employee_skills(active_emp["id"])
            if not emp_sk_df.empty:
                preselected_skills = emp_sk_df[emp_sk_df["proficiency_level"] > 0]["skill_name"].tolist()

        form_current_skills = st.multiselect(
            "Current Skills & Competencies (Select all that apply)",
            options=skill_catalog_names,
            default=[s for s in preselected_skills if s in skill_catalog_names],
            help="Select the skills you already have practical or theoretical experience with."
        )

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            form_tech_skills = st.text_area(
                "Technical Skills & Toolchain Stack",
                value=active_emp.get("technical_skills_summary", "") if is_editing_existing else "",
                placeholder="e.g. Python, SQL, Docker, Git, REST APIs, Linux, AWS",
                help="Specific libraries, frameworks, tools, or languages you regularly use."
            )
        with col_s2:
            form_goals = st.text_area(
                "Primary Learning Goals",
                value=active_emp.get("learning_goals", "") if is_editing_existing else "",
                placeholder="e.g. Close critical machine learning gaps, achieve cloud practitioner certification, and earn promotion to Senior AI Engineer.",
                help="Specific upskilling milestones or certification objectives you want to achieve."
            )

        st.markdown("<br>", unsafe_allow_html=True)
        col_sub1, col_sub2 = st.columns([1.5, 3])
        with col_sub1:
            submit_label = "💾 Save and Continue ➔" if not is_editing_existing else "💾 Save Profile Changes ➔"
            submitted = st.form_submit_button(submit_label, use_container_width=True)

        if submitted:
            # Generate email if blank
            clean_email = form_email.strip().lower()
            if not clean_email:
                clean_email = f"{form_name.strip().lower().replace(' ', '.')}@enterprise.com"

            saved_id, err = save_or_update_employee(
                name=form_name.strip(),
                email=clean_email,
                department=form_dept,
                current_role=form_curr_role.strip(),
                target_role=form_target_role,
                experience_years=form_exp,
                weekly_learning_hours=form_hours,
                employee_id=active_emp["id"] if is_editing_existing else None,
                employee_code=form_code.strip(),
                career_interests=form_interests.strip(),
                learning_goals=form_goals.strip(),
                current_skills_summary=", ".join(form_current_skills) if form_current_skills else "",
                technical_skills_summary=form_tech_skills.strip()
            )

            if err:
                st.error(f"❌ {err}")
            else:
                # If skills were selected in multiselect, initialize baseline ratings if missing
                if form_current_skills:
                    name_to_id = {row["name"]: int(row["id"]) for _, row in all_skills_df.iterrows()}
                    current_sk = get_employee_skills(saved_id)
                    existing_ratings = dict(zip(current_sk["skill_id"], current_sk["proficiency_level"]))
                    new_ratings = {}
                    for sk_name in form_current_skills:
                        sk_id = name_to_id.get(sk_name)
                        if sk_id and existing_ratings.get(sk_id, 0) == 0:
                            new_ratings[sk_id] = 2  # Default to elementary baseline
                    if new_ratings:
                        save_employee_skill_assessment(saved_id, new_ratings)

                st.session_state["active_employee_id"] = saved_id
                st.session_state["is_onboarding_new"] = False
                set_preference("active_employee_id", str(saved_id))
                st.balloons()
                st.success(f"🎉 Employee profile for {form_name} successfully saved!")
                navigate_to(PAGE_DASHBOARD)


# =============================================================
# PAGE 2: DASHBOARD – USER JOURNEY & PROMINENT ACTION CARDS
# =============================================================
elif selected_page == PAGE_DASHBOARD:
    if not active_emp:
        st.warning("⚠️ No active employee profile selected. Please set up an employee profile in Employee Information.")
        if st.button("👤 Go to Employee Information", key="dash_no_emp_btn"):
            navigate_to(PAGE_EMPLOYEE_INFO)
    else:
        render_section_header(
            title="🏠 Executive Talent & Capability Dashboard",
            subtitle=f"Tracking employee benchmark readiness, immediate interventions, and personalized career growth for <b>{active_emp['name']}</b>.",
            badge="📊 EXECUTIVE TALENT PULSE",
            lottie_filename="growth.json",
            image_url="https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=600&q=80",
            anim_height=160,
            key_prefix="dash_header"
        )

        gap_res = analyze_skill_gap(current_emp_id)
        tracker_res = get_employee_tracker_summary(current_emp_id)

        # ---------------------------------------------------------
        # PROMINENT COURSERA-STYLE DASHBOARD ACTION CARDS
        # ---------------------------------------------------------
        st.markdown("### 🚀 Primary Learning Journey Actions")
        st.caption("Select any action below to navigate directly to your upskilling milestone.")

        col_act1, col_act2, col_act3, col_act4 = st.columns(4)

        with col_act1:
            st.markdown("""
            <div class="dash-action-card">
                <span class="dash-action-icon">📝</span>
                <h4 class="dash-action-title">Skill Assessment</h4>
                <p class="dash-action-desc">Benchmark your competencies via self-ratings & objective diagnostic quiz.</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Start Skill Assessment", key="dash_btn_assess", use_container_width=True):
                navigate_to(PAGE_SKILL_ASSESSMENT)

        with col_act2:
            st.markdown("""
            <div class="dash-action-card">
                <span class="dash-action-icon">🎯</span>
                <h4 class="dash-action-title">Skill Gap Analyzer</h4>
                <p class="dash-action-desc">Examine competency radar, role benchmarks & priority deficit areas.</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Analyze Skill Gaps", key="dash_btn_gaps", use_container_width=True):
                navigate_to(PAGE_SKILL_GAP)

        with col_act3:
            st.markdown("""
            <div class="dash-action-card">
                <span class="dash-action-icon">🗺️</span>
                <h4 class="dash-action-title">Personalized Roadmap</h4>
                <p class="dash-action-desc">Explore AI-curated courses & phased milestone study timeline.</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Explore Learning Roadmap", key="dash_btn_roadmap", use_container_width=True):
                navigate_to(PAGE_PERSONALIZED_LEARNING)

        with col_act4:
            st.markdown("""
            <div class="dash-action-card">
                <span class="dash-action-icon">📈</span>
                <h4 class="dash-action-title">Progress Tracking</h4>
                <p class="dash-action-desc">Monitor course progress, log study hours & earn skill badges.</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Track My Progress", key="dash_btn_tracker", use_container_width=True):
                navigate_to(PAGE_PROGRESS_TRACKING)

        st.markdown("<br>", unsafe_allow_html=True)

        # High level metric cards for active employee
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                label="🎯 Target Role Readiness",
                value=f"{gap_res['readiness_score']}%",
                delta=f"{len(gap_res['strengths'])} skills benchmark met"
            )
        with col2:
            st.metric(
                label="🚨 Critical Skill Deficits",
                value=len(gap_res["critical_gaps"]),
                delta=f"-{len(gap_res['critical_gaps'])} required" if gap_res["critical_gaps"] else "All core met",
                delta_color="inverse"
            )
        with col3:
            st.metric(
                label="📚 Active Enrollments",
                value=tracker_res["active_courses"],
                delta=f"{tracker_res['completed_courses']} completed"
            )
        with col4:
            st.metric(
                label="⏱️ Logged Learning Time",
                value=f"{tracker_res['total_hours']} hrs",
                delta=f"Pace: {active_emp['weekly_learning_hours']} hrs/wk"
            )

        # Readiness progress meter
        st.markdown(f"**🎯 Overall Target Role Benchmark Readiness:** `{gap_res['readiness_score']}%`")
        st.progress(max(0.0, min(1.0, gap_res['readiness_score'] / 100.0)))
        st.markdown("<br>", unsafe_allow_html=True)

        # Dashboard Section Tabs
        dash_tab1, dash_tab2, dash_tab3 = st.tabs([
            "🌐 Competency Radar & Action Plan",
            "🏆 Unlocked Achievements & Badges",
            "📋 Active Employee Summary Profile"
        ])

        with dash_tab1:
            col_left, col_right = st.columns([1.25, 1])

            with col_left:
                st.subheader(f"🌐 Competency Radar: {active_emp['name']}")
                st.caption(f"Comparing current proficiency against benchmark for **{active_emp['target_role']}**")
                radar_fig = create_radar_chart(gap_res["gap_df"], active_emp["target_role"], active_emp["name"])
                # FIXED NON-INTERACTIVE CHART: cannot be zoomed, panned, or toolbar-manipulated
                render_static_chart(radar_fig, key="dash_radar_chart")

            with col_right:
                st.subheader("⚡ Priority Capability Intervention")
                if gap_res["critical_gaps"]:
                    st.warning(f"🚨 **{len(gap_res['critical_gaps'])} Critical Skill Gaps** require immediate intervention:")
                    for cg in gap_res["critical_gaps"][:3]:
                        st.markdown(
                            f"- **🎯 {cg['skill_name']}**: Current Level {cg['current_level']} ➔ Required Level {cg['required_level']} (*Gap: +{cg['gap']}*)"
                        )
                else:
                    st.success("✅ **No critical gaps detected!** You are well-aligned with your target role benchmark.")

                st.markdown("#### 💡 Recommended Next Course")
                recs = recommend_courses(current_emp_id, top_n=1)
                if recs:
                    top_rec = recs[0]
                    st.markdown(f"**[{top_rec['title']}]({top_rec['platform_url']})**")
                    st.caption(f"🏛️ Provider: {top_rec['provider']} | 🎯 Skill: {top_rec['skill_name']} (Lvl {top_rec['level']})")
                    st.info(f"💡 {top_rec['explanation']}")
                    if st.button("➕ Quick Enroll in Next Course", key="dash_quick_enroll"):
                        ok, err = enroll_employee_in_course(current_emp_id, top_rec["course_id"])
                        if ok:
                            st.success(f"Enrolled in {top_rec['title']}!")
                            st.rerun()
                        else:
                            st.warning(err)

        with dash_tab2:
            st.subheader("🏆 Unlocked Badges & Upskilling Achievements")
            if tracker_res["badges"]:
                b_cols = st.columns(min(4, len(tracker_res["badges"])))
                for i, badge in enumerate(tracker_res["badges"]):
                    with b_cols[i % len(b_cols)]:
                        st.markdown(f"""
                        <div class="badge-pill-card">
                            <div style="font-size: 2.2rem; margin-bottom: 6px;">{badge['icon']}</div>
                            <h4 style="margin: 0; color: #1E293B;">{badge['title']}</h4>
                            <p style="font-size: 0.85rem; color: #64748B; margin-top: 4px;">{badge['desc']}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("🎓 Enroll in courses and log study sessions to unlock enterprise capability achievements!")

        with dash_tab3:
            emp_code_display = active_emp.get("employee_code") or f"EMP-{active_emp['id']:04d}"
            st.subheader(f"📋 Employee Profile Overview: {active_emp['name']}")
            sc1, sc2 = st.columns(2)
            with sc1:
                st.write(f"👤 **Full Name:** {active_emp['name']}")
                st.write(f"🆔 **Employee ID:** {emp_code_display}")
                st.write(f"✉️ **Corporate Email:** {active_emp['email']}")
                st.write(f"🏢 **Department:** {active_emp['department']}")
                st.write(f"💼 **Current Designation:** {active_emp['current_role']}")
            with sc2:
                st.write(f"🎯 **Target Aspirational Role:** {active_emp['target_role']}")
                st.write(f"📅 **Industry Experience:** {active_emp['experience_years']} years")
                st.write(f"⏱️ **Weekly Study Commitment:** {active_emp['weekly_learning_hours']} hrs/week")
                st.write(f"📈 **Active In Progress Courses:** {tracker_res['active_courses']}")
                if active_emp.get("career_interests"):
                    st.write(f"🌟 **Career Interests:** {active_emp['career_interests']}")
                if active_emp.get("learning_goals"):
                    st.write(f"🎯 **Learning Goals:** {active_emp['learning_goals']}")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✏️ Edit Profile in Employee Information", key="dash_edit_profile"):
                navigate_to(PAGE_EMPLOYEE_INFO)


# =============================================================
# PAGE 3: SKILL ASSESSMENT – DIAGNOSTICS & RATINGS
# =============================================================
elif selected_page == PAGE_SKILL_ASSESSMENT:
    if not active_emp:
        st.warning("⚠️ Please select or create an active employee profile in Employee Information.")
        if st.button("👤 Go to Employee Information", key="assess_no_emp_btn"):
            navigate_to(PAGE_EMPLOYEE_INFO)
    else:
        render_section_header(
            title="📝 Employee Skill Assessment & Diagnostics",
            subtitle="Benchmark employee competencies via self-rating or take the objective diagnostic mini-quiz to eliminate self-assessment bias.",
            badge="📝 CAPABILITY BENCHMARKING",
            lottie_filename="skills.json",
            image_url="https://images.unsplash.com/photo-1434030216411-0b793f4b4173?auto=format&fit=crop&w=600&q=80",
            anim_height=160,
            key_prefix="assess_header"
        )

        col_assess_nav1, col_assess_nav2, _ = st.columns([2, 1.5, 3])
        with col_assess_nav1:
            if st.button("🎯 Proceed to Skill Gap Analyzer ➔", key="assess_nav_gap", use_container_width=True):
                navigate_to(PAGE_SKILL_GAP)
        with col_assess_nav2:
            if st.button("🏠 Return to Dashboard", key="assess_nav_dash", use_container_width=True):
                navigate_to(PAGE_DASHBOARD)

        st.markdown("<br>", unsafe_allow_html=True)

        tab_self_assess, tab_quiz, tab_profile_view = st.tabs([
            "🎚️ Competency Self-Assessment Rating",
            "🧠 Objective Diagnostic Mini-Quiz",
            "👤 Employee Profile Overview"
        ])

        with tab_self_assess:
            st.subheader(f"🎚️ Rate Competencies for: {active_emp['name']}")
            st.markdown("""
            <div class="white-card" style="padding: 1rem 1.25rem; margin-bottom: 1.25rem;">
                <b>💡 Proficiency Scale Reference:</b><br>
                <b>Level 1: Novice</b> (Basic conceptual understanding) · 
                <b>Level 2: Elementary</b> (Assisted routine tasks) · 
                <b>Level 3: Intermediate</b> (Independent practitioner) · 
                <b>Level 4: Advanced</b> (Deep working knowledge & design) · 
                <b>Level 5: Expert</b> (Authoritative subject expert)
            </div>
            """, unsafe_allow_html=True)

            emp_skills_df = get_employee_skills(current_emp_id)
            current_ratings = dict(zip(emp_skills_df["skill_id"], emp_skills_df["proficiency_level"]))

            skills_by_cat = get_skills_by_category()
            updated_ratings = {}

            with st.form("self_assessment_form"):
                for category, skills_list in skills_by_cat.items():
                    st.markdown(f"#### 📂 {category}")
                    cols = st.columns(2)
                    for i, skill in enumerate(skills_list):
                        sid = skill["id"]
                        curr_val = current_ratings.get(sid, 1)
                        curr_val = max(1, min(5, curr_val))
                        with cols[i % 2]:
                            updated_ratings[sid] = st.slider(
                                f"🎯 {skill['name']}",
                                min_value=1,
                                max_value=5,
                                value=curr_val,
                                key=f"skill_slider_{sid}",
                                help=skill["description"]
                            )
                            level_pct = updated_ratings[sid] / 5.0
                            st.progress(level_pct)
                            st.caption(f"Current Rating: **Level {updated_ratings[sid]}/5** ({PROFICIENCY_LEVELS[updated_ratings[sid]]['name']})")
                    st.markdown("---")

                col_save_sub, _ = st.columns([2, 3])
                with col_save_sub:
                    submit_ratings = st.form_submit_button("✅ Submit Assessment Ratings", use_container_width=True)

                if submit_ratings:
                    success, err = save_employee_skill_assessment(current_emp_id, updated_ratings)
                    if success:
                        st.success("✅ Skill assessment ratings successfully saved and synchronized with Skill Gap Analyzer!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ Error saving ratings: {err}")

        with tab_quiz:
            st.subheader("🧠 Objective Skill Diagnostic Mini-Quiz")
            st.caption("Standardized questions to objectively benchmark employee foundational competencies and eliminate self-reporting bias.")

            with st.form("diagnostic_quiz_form"):
                user_answers = {}
                for q in DIAGNOSTIC_QUESTIONS:
                    st.markdown(f"**Q{q['id']}. [{q['category']} / {q['skill']}]** {q['question']}")
                    selected_idx = st.radio(
                        "Select best answer:",
                        options=range(len(q["options"])),
                        format_func=lambda i, opts=q["options"]: opts[i],
                        key=f"quiz_q_{q['id']}"
                    )
                    user_answers[q["id"]] = selected_idx
                    st.markdown("---")

                col_quiz_sub, _ = st.columns([2, 3])
                with col_quiz_sub:
                    submit_quiz = st.form_submit_button("📊 Submit Diagnostic Answers", use_container_width=True)

                if submit_quiz:
                    quiz_result = score_diagnostic_quiz(user_answers)
                    ok_apply, err_apply = apply_diagnostic_results(current_emp_id, quiz_result)

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.subheader(f"🎯 Diagnostic Score: {quiz_result['score_pct']}% ({quiz_result['correct_answers']}/{quiz_result['total_questions']} correct)")
                    st.progress(quiz_result['score_pct'] / 100.0)
                    st.info(f"🎯 **Suggested Baseline Proficiency Level:** Level {quiz_result['suggested_baseline']} ({PROFICIENCY_LEVELS[quiz_result['suggested_baseline']]['name']})")

                    if ok_apply:
                        st.success("✅ Diagnostic quiz results and baseline ratings have been saved to the Skill Gap Analyzer!")

                    with st.expander("🔍 Review Answer Breakdown", expanded=True):
                        for b in quiz_result["breakdown"]:
                            if b["is_correct"]:
                                st.success(f"✅ **{b['skill']}**: Correct ({b['correct_option']})")
                            else:
                                st.error(f"❌ **{b['skill']}**: Your answer: '{b['selected_option']}' | Correct: '{b['correct_option']}'")

        with tab_profile_view:
            st.subheader(f"👤 Employee Profile Overview: {active_emp['name']}")
            st.write(f"🏢 **Department:** {active_emp['department']}")
            st.write(f"💼 **Current Role:** {active_emp['current_role']}")
            st.write(f"🎯 **Target Role:** {active_emp['target_role']}")
            st.write(f"📅 **Experience:** {active_emp['experience_years']} years")
            st.write(f"⏱️ **Weekly Hours:** {active_emp['weekly_learning_hours']} hrs/wk")
            if active_emp.get("career_interests"):
                st.write(f"🌟 **Career Interests:** {active_emp['career_interests']}")
            if active_emp.get("learning_goals"):
                st.write(f"🎯 **Learning Goals:** {active_emp['learning_goals']}")
            if st.button("✏️ Edit Profile in Employee Information", key="assess_to_emp_info"):
                navigate_to(PAGE_EMPLOYEE_INFO)


# =============================================================
# PAGE 4: SKILL GAP ANALYZER – BENCHMARKS & RADAR CHARTS
# =============================================================
elif selected_page == PAGE_SKILL_GAP:
    if not active_emp:
        st.warning("⚠️ Please select or create an active employee profile in Employee Information.")
        if st.button("👤 Go to Employee Information", key="gap_no_emp_btn"):
            navigate_to(PAGE_EMPLOYEE_INFO)
    else:
        render_section_header(
            title="🎯 Target Role Skill Gap Analyzer",
            subtitle=f"Evaluating <b>{active_emp['name']}</b>'s skill profile against <b>{active_emp['target_role']}</b> benchmarks with what-if scenario simulation.",
            badge="🎯 GAP ANALYSIS & SIMULATION",
            lottie_filename="ai.json",
            image_url="https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=600&q=80",
            anim_height=160,
            key_prefix="gap_header"
        )

        # Direct Navigation Action Bar
        col_gap_act1, col_gap_act2, _ = st.columns([2.2, 1.5, 3])
        with col_gap_act1:
            if st.button("💡 Explore Personalized Learning ➔", key="gap_nav_to_learning", use_container_width=True):
                navigate_to(PAGE_PERSONALIZED_LEARNING)
        with col_gap_act2:
            if st.button("🏠 Return to Dashboard", key="gap_nav_to_dash", use_container_width=True):
                navigate_to(PAGE_DASHBOARD)

        st.markdown("<br>", unsafe_allow_html=True)

        # What-if role benchmark switching
        col_t1, _ = st.columns([2.5, 1])
        with col_t1:
            target_role_eval = st.selectbox(
                "🔮 Simulate Target Role Benchmark (What-if scenario):",
                STANDARD_ROLES,
                index=STANDARD_ROLES.index(active_emp["target_role"]) if active_emp["target_role"] in STANDARD_ROLES else 0
            )

        gap_data = analyze_skill_gap(current_emp_id, target_role=target_role_eval)
        gap_df = gap_data["gap_df"]

        # Top KPI row
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.metric("🎯 Benchmark Readiness Score", f"{gap_data['readiness_score']}%")
        with kpi2:
            st.metric("📚 Total Skills Evaluated", gap_data["total_skills_required"])
        with kpi3:
            st.metric("🚨 Critical Gaps", len(gap_data["critical_gaps"]))
        with kpi4:
            st.metric("✅ Competencies Met", len(gap_data["strengths"]))

        # Visual readiness progress bar
        st.markdown(f"**🎯 Benchmark Readiness Meter:** `{gap_data['readiness_score']}%`")
        st.progress(max(0.0, min(1.0, gap_data['readiness_score'] / 100.0)))
        st.markdown("<br>", unsafe_allow_html=True)

        # Tabs for Gap Analyzer
        gap_tab1, gap_tab2, gap_tab3 = st.tabs([
            "🌐 Competency Radar & Benchmarks",
            "📉 Gap Severity Breakdown",
            "📋 Full Competency Matrix & Progress Levels"
        ])

        with gap_tab1:
            st.subheader("🌐 Competency Radar vs Role Benchmark")
            radar_fig = create_radar_chart(gap_df, target_role_eval, active_emp["name"])
            # FIXED NON-INTERACTIVE CHART
            render_static_chart(radar_fig, key="gap_radar_chart")

        with gap_tab2:
            st.subheader("📉 Gap Severity by Competency")
            bar_fig = create_gap_bar_chart(gap_df)
            # FIXED NON-INTERACTIVE CHART
            render_static_chart(bar_fig, key="gap_bar_chart")

        with gap_tab3:
            st.subheader("📋 Individual Skill Progress Levels")
            st.caption("Visual breakdown of current proficiency versus required role benchmarks for all competencies.")

            if not gap_df.empty:
                for _, row in gap_df.iterrows():
                    render_skill_progress_item(
                        skill_name=row["skill_name"],
                        category=row["category"],
                        current_lvl=int(row["current_level"]),
                        required_lvl=int(row["required_level"]),
                        gap=int(row["gap"]),
                        status=row["status"],
                        is_core=int(row["is_core"])
                    )

                st.markdown("---")
                st.subheader("📑 Tabular Gap Breakdown")
                display_df = gap_df[["skill_name", "category", "current_level", "required_level", "gap", "is_core", "status"]].copy()
                display_df["is_core"] = display_df["is_core"].apply(lambda x: "⭐ Core" if x == 1 else "Elective")
                display_df.columns = ["Skill Name", "Category", "Current Level", "Required Benchmark", "Gap", "Role Importance", "Status"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_c2a, _ = st.columns([2.5, 3])
        with col_c2a:
            if st.button("💡 View Personalized Learning Recommendations ➔", key="gap_btn_to_recs", use_container_width=True):
                navigate_to(PAGE_PERSONALIZED_LEARNING)


# =============================================================
# PAGE 5: PERSONALIZED LEARNING – COURSES & ROADMAP
# =============================================================
elif selected_page == PAGE_PERSONALIZED_LEARNING:
    if not active_emp:
        st.warning("⚠️ Please select or create an active employee profile in Employee Information.")
        if st.button("👤 Go to Employee Information", key="pl_no_emp_btn"):
            navigate_to(PAGE_EMPLOYEE_INFO)
    else:
        render_section_header(
            title="💡 Personalized Learning & Career Roadmap",
            subtitle=f"Personalized course recommendations and structured learning trajectory targeting identified skill gaps for <b>{active_emp['name']}</b>.",
            badge="💡 EXPLAINABLE AI SCORING & ROADMAP",
            lottie_filename="learning.json",
            image_url="https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=600&q=80",
            anim_height=160,
            key_prefix="recs_header"
        )

        # Clear Action & Return Bar
        col_pl1, col_pl2, col_pl3, _ = st.columns([1.6, 1.8, 1.8, 2])
        with col_pl1:
            if st.button("🏠 Return to Dashboard", key="pl_return_dash", use_container_width=True):
                navigate_to(PAGE_DASHBOARD)
        with col_pl2:
            if st.button("🎯 Review Skill Gaps", key="pl_to_gaps", use_container_width=True):
                navigate_to(PAGE_SKILL_GAP)
        with col_pl3:
            if st.button("📈 Track My Progress ➔", key="pl_to_tracker", use_container_width=True):
                navigate_to(PAGE_PROGRESS_TRACKING)

        st.markdown("<br>", unsafe_allow_html=True)

        rec_tab1, rec_tab2, rec_tab3 = st.tabs([
            "✨ Curated Course Recommendations",
            "🗺️ Phased Learning Roadmap & Timeline",
            "⚙️ Scoring Rationale & Course Catalog"
        ])

        with rec_tab1:
            # Controls row
            rc1, rc2, rc3 = st.columns([1.5, 1.5, 1])
            with rc1:
                use_ai = st.toggle("🤖 Use AI Multi-Criteria Scoring (vs Deterministic Fallback)", value=True)
            with rc2:
                skills_df = get_all_skills()
                skill_filter = st.selectbox(
                    "🎯 Filter by Specific Gap Skill",
                    options=["All Gap Skills"] + list(skills_df["name"].unique())
                )
                selected_skill_id = None
                if skill_filter != "All Gap Skills":
                    match = skills_df[skills_df["name"] == skill_filter]
                    if not match.empty:
                        selected_skill_id = int(match.iloc[0]["id"])
            with rc3:
                num_recs = st.slider("🔢 Top Recommendations Count", min_value=3, max_value=10, value=6)

            recs = recommend_courses(
                current_emp_id,
                use_ai_heuristic=use_ai,
                top_n=num_recs,
                filter_skill_id=selected_skill_id
            )

            # Check enrolled courses to display progress
            emp_enrollments_df = get_employee_enrollments(current_emp_id)
            enrolled_ids = {}
            if not emp_enrollments_df.empty:
                for _, erow in emp_enrollments_df.iterrows():
                    enrolled_ids[int(erow["course_id"])] = {
                        "status": erow["status"],
                        "progress_pct": int(erow["progress_pct"])
                    }

            if not recs:
                st.info("ℹ️ No courses found matching current criteria.")
            else:
                st.caption(f"Showing **{len(recs)}** recommended courses sorted by relevance score.")
                for rec in recs:
                    cid = rec["course_id"]
                    enroll_info = enrolled_ids.get(cid)
                    if enroll_info:
                        rec["learning_progress"] = enroll_info["progress_pct"]

                    render_course_card(rec)
                    col_btn1, col_btn2, _ = st.columns([1.8, 2.2, 5])
                    with col_btn1:
                        st.link_button("🔗 Explore Course", rec["platform_url"])
                    with col_btn2:
                        if enroll_info:
                            st.button(f"✅ Enrolled ({enroll_info['progress_pct']}%)", key=f"already_enrolled_{cid}", disabled=True)
                        else:
                            if st.button("➕ Start Learning / Enroll Now", key=f"rec_enroll_{cid}"):
                                ok, err = enroll_employee_in_course(current_emp_id, cid)
                                if ok:
                                    st.success(f"✅ Successfully enrolled in {rec['title']}!")
                                    st.rerun()
                                else:
                                    st.warning(err)
                    st.markdown("<br>", unsafe_allow_html=True)

        with rec_tab2:
            st.subheader("🗺️ Phased Learning Roadmap & Phased Timeline")
            st.caption(f"Structured learning trajectory for **{active_emp['name']}** at **{active_emp['weekly_learning_hours']} hrs/week**.")

            roadmap = generate_learning_roadmap(current_emp_id)

            # Roadmap Metrics Row
            rcol1, rcol2, rcol3, rcol4 = st.columns(4)
            with rcol1:
                st.metric("📚 Total Recommended Modules", roadmap["total_courses"])
            with rcol2:
                st.metric("⏱️ Total Learning Commitment", f"{roadmap['total_hours']} hrs")
            with rcol3:
                st.metric("📅 Estimated Program Timeline", f"{roadmap['total_weeks']} weeks")
            with rcol4:
                st.metric("⏳ Weekly Study Pace", f"{roadmap['weekly_hours']} hrs/wk")

            st.markdown("<br>", unsafe_allow_html=True)

            # Phased Steps
            if not roadmap["phases"]:
                st.info("ℹ️ No roadmap milestones found. Ensure target role skills are configured.")
            else:
                for phase_name, milestone_list in roadmap["phases"].items():
                    st.markdown(f"### 📂 {phase_name}")
                    for m in milestone_list:
                        render_roadmap_step_card(m)
                        col_m1, col_m2, _ = st.columns([1.5, 2, 5])
                        with col_m1:
                            st.link_button("🔗 View Course", m["platform_url"])
                        with col_m2:
                            if st.button("➕ Enroll in Module", key=f"road_enroll_{m['course_id']}"):
                                ok, err = enroll_employee_in_course(current_emp_id, m["course_id"])
                                if ok:
                                    st.success(f"✅ Enrolled in {m['title']}!")
                                    st.rerun()
                                else:
                                    st.warning(err)
                        st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("📅 Interactive Gantt Schedule Timeline")
            timeline_fig = create_roadmap_timeline_chart(roadmap)
            # FIXED NON-INTERACTIVE CHART: cannot be zoomed, panned, or toolbar-manipulated
            render_static_chart(timeline_fig, key="roadmap_timeline_chart")

            st.markdown("---")
            st.subheader("⚡ Accelerated Study Pace Simulation")
            st.markdown(f"""
            <div class="white-card">
                <h4>🚀 Fast-Track Your Roadmap:</h4>
                <p>At your current weekly commitment of <b>{roadmap['weekly_hours']} hrs/week</b>, your program duration is estimated at <b>{roadmap['total_weeks']} weeks</b>.</p>
                <div style="display: flex; gap: 16px; margin-top: 1rem; flex-wrap: wrap;">
                    <div style="background: #EEF2FF; padding: 12px 18px; border-radius: 12px; border: 1px solid #C7D2FE;">
                        <b>Pace: 5 hrs/week</b> ➔ ~{round(roadmap['total_hours'] / 5.0, 1)} weeks
                    </div>
                    <div style="background: #F0FDF4; padding: 12px 18px; border-radius: 12px; border: 1px solid #BBF7D0;">
                        <b>Pace: 8 hrs/week</b> ➔ ~{round(roadmap['total_hours'] / 8.0, 1)} weeks
                    </div>
                    <div style="background: #FDF2F8; padding: 12px 18px; border-radius: 12px; border: 1px solid #FBCFE8;">
                        <b>Pace: 12 hrs/week</b> ➔ ~{round(roadmap['total_hours'] / 12.0, 1)} weeks
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with rec_tab3:
            st.subheader("⚙️ Transparent Multi-Criteria AI Heuristic Weights")
            st.markdown("""
            <div class="white-card">
                <h4>🧠 Scoring Mathematical Breakdown:</h4>
                <p>Every course recommendation score (0 - 100) is deterministically calculated using 4 weighted parameters:</p>
                <ul>
                    <li><b>🎯 Skill Gap Magnitude (45% weight):</b> Direct alignment with the employee's critical deficits for their target role benchmark.</li>
                    <li><b>📈 Difficulty Alignment (25% weight):</b> Ensures course level (1-5) matches the employee's current capability for optimal learning zone.</li>
                    <li><b>⭐ Course Quality Rating (15% weight):</b> Verified external learner rating (out of 5.0).</li>
                    <li><b>⏱️ Weekly Study Fit (15% weight):</b> Feasibility of course completion based on the employee's weekly time commitment.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("📚 Enterprise Course Catalog & Provider Coverage")
            all_courses = get_all_courses()
            st.caption(f"Covering **{len(all_courses)}** verified courses from Coursera, edX, MIT OCW, freeCodeCamp, and official docs.")
            cat_df = pd.DataFrame(all_courses)[["title", "provider", "skill_name", "level", "duration_hours", "rating"]]
            cat_df.columns = ["Course Title", "Provider", "Target Skill", "Level (1-5)", "Duration (Hours)", "Rating"]
            st.dataframe(cat_df, use_container_width=True, hide_index=True)


# =============================================================
# PAGE 6: PROGRESS TRACKING – ENROLLMENTS & LOGS
# =============================================================
elif selected_page == PAGE_PROGRESS_TRACKING:
    if not active_emp:
        st.warning("⚠️ Please select or create an active employee profile in Employee Information.")
        if st.button("👤 Go to Employee Information", key="track_no_emp_btn"):
            navigate_to(PAGE_EMPLOYEE_INFO)
    else:
        render_section_header(
            title="📈 Employee Learning Progress Tracker",
            subtitle=f"Track active courses, log study hours, and earn automated skill promotions for <b>{active_emp['name']}</b>.",
            badge="📈 REAL-TIME LEARNING TRACKER",
            lottie_filename="celebrate.json",
            image_url="https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=600&q=80",
            anim_height=160,
            key_prefix="track_header"
        )

        col_track_nav1, col_track_nav2, _ = st.columns([1.6, 1.8, 3.6])
        with col_track_nav1:
            if st.button("🏠 Return to Dashboard", key="track_nav_dash", use_container_width=True):
                navigate_to(PAGE_DASHBOARD)
        with col_track_nav2:
            if st.button("💡 Explore More Courses", key="track_nav_recs", use_container_width=True):
                navigate_to(PAGE_PERSONALIZED_LEARNING)

        st.markdown("<br>", unsafe_allow_html=True)

        tracker_data = get_employee_tracker_summary(current_emp_id)
        gap_res = analyze_skill_gap(current_emp_id)

        # Top tracker metrics
        t1, t2, t3, t4 = st.columns(4)
        with t1:
            st.metric("📚 Enrolled Courses", tracker_data["total_enrollments"])
        with t2:
            st.metric("✅ Completed Courses", tracker_data["completed_courses"])
        with t3:
            st.metric("⏱️ Total Hours Invested", f"{tracker_data['total_hours']} hrs")
        with t4:
            st.metric("📈 Avg Course Completion", f"{tracker_data['avg_progress']}%")

        st.markdown("<br>", unsafe_allow_html=True)

        # Comprehensive Skill Progress & Evolution Breakdown
        st.markdown("### 🎯 Executive Skill Evolution Overview")
        col_sk1, col_sk2, col_sk3, col_sk4 = st.columns(4)
        with col_sk1:
            st.markdown(f"""
            <div class="white-card" style="border-top: 4px solid #10B981;">
                <h4 style="margin: 0; color: #10B981;">🎯 Skills Acquired</h4>
                <div style="font-size: 1.8rem; font-weight: 800; color: #1E293B; margin: 4px 0;">{len(gap_res['strengths'])}</div>
                <p style="margin: 0; color: #64748B; font-size: 0.82rem;">Benchmark proficiency met or exceeded.</p>
            </div>
            """, unsafe_allow_html=True)
        with col_sk2:
            developing_count = tracker_data["active_courses"]
            st.markdown(f"""
            <div class="white-card" style="border-top: 4px solid #3B82F6;">
                <h4 style="margin: 0; color: #3B82F6;">📚 Skills Developing</h4>
                <div style="font-size: 1.8rem; font-weight: 800; color: #1E293B; margin: 4px 0;">{developing_count}</div>
                <p style="margin: 0; color: #64748B; font-size: 0.82rem;">Actively being acquired through enrollments.</p>
            </div>
            """, unsafe_allow_html=True)
        with col_sk3:
            st.markdown(f"""
            <div class="white-card" style="border-top: 4px solid #EF4444;">
                <h4 style="margin: 0; color: #EF4444;">🚨 Remaining Gaps</h4>
                <div style="font-size: 1.8rem; font-weight: 800; color: #1E293B; margin: 4px 0;">{len(gap_res['critical_gaps'])}</div>
                <p style="margin: 0; color: #64748B; font-size: 0.82rem;">Critical role competencies still needed.</p>
            </div>
            """, unsafe_allow_html=True)
        with col_sk4:
            st.markdown(f"""
            <div class="white-card" style="border-top: 4px solid #8B5CF6;">
                <h4 style="margin: 0; color: #8B5CF6;">📈 Target Readiness</h4>
                <div style="font-size: 1.8rem; font-weight: 800; color: #1E293B; margin: 4px 0;">{gap_res['readiness_score']}%</div>
                <p style="margin: 0; color: #64748B; font-size: 0.82rem;">Overall progress toward target role.</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        track_tab1, track_tab2, track_tab3 = st.tabs([
            "📖 Active Course Enrollments & Progress",
            "⏱️ Record New Study Activity Session",
            "🏆 Unlocked Badges & Activity History"
        ])

        with track_tab1:
            st.subheader("📖 Current Enrollments & Course Progress")
            enrollments_df = tracker_data["enrollments_df"]

            if enrollments_df.empty:
                st.info("ℹ️ No active course enrollments yet. Visit '💡 Personalized Learning' to enroll in courses!")
                if st.button("💡 Browse Courses in Personalized Learning", key="track_to_recs_empty"):
                    navigate_to(PAGE_PERSONALIZED_LEARNING)
            else:
                for _, enroll in enrollments_df.iterrows():
                    cid = enroll["course_id"]
                    st.markdown(f"""
                    <div class="white-card">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
                            <h4 style="margin: 0; color: #1E293B;">
                                <a href="{enroll['platform_url']}" target="_blank" style="color: #4338CA; text-decoration: none;">
                                    🎓 {enroll['title']}
                                </a>
                            </h4>
                            <span style="background: #EEF2FF; color: #4338CA; font-weight: 700; font-size: 0.8rem; padding: 3px 10px; border-radius: 12px;">
                                {enroll['status'].replace('_', ' ').title()}
                            </span>
                        </div>
                        <p style="color: #64748B; font-size: 0.85rem; margin: 4px 0 10px 0;">
                            🎯 <b>Target Skill:</b> {enroll['skill_name']} | 📅 <b>Enrolled:</b> {enroll['enrolled_date']}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                    # Progress Bar
                    st.progress(enroll["progress_pct"] / 100.0)

                    col_p1, col_p2 = st.columns([3, 1])
                    with col_p1:
                        new_prog = st.slider(
                            f"Update Progress for: {enroll['title']} (%)",
                            min_value=0,
                            max_value=100,
                            value=int(enroll["progress_pct"]),
                            key=f"slider_prog_{cid}"
                        )
                    with col_p2:
                        if st.button("💾 Update Progress", key=f"btn_prog_{cid}"):
                            ok, err, notif = update_course_progress(current_emp_id, cid, new_prog)
                            if ok:
                                if notif:
                                    st.balloons()
                                    st.success(notif)
                                else:
                                    st.success(f"Progress updated to {new_prog}%!")
                                st.rerun()
                            else:
                                st.error(err)
                    st.markdown("<hr style='border: 0; height: 1px; background: #E2E8F0; margin: 1.5rem 0;'>", unsafe_allow_html=True)

        with track_tab2:
            st.subheader("⏱️ Record New Study Session")
            if not enrollments_df.empty:
                with st.form("log_study_form"):
                    course_map = dict(zip(enrollments_df["title"], enrollments_df["course_id"]))
                    selected_course_title = st.selectbox("Select Enrolled Course", list(course_map.keys()))
                    hours_input = st.number_input("Study Time (Hours)", min_value=0.5, max_value=20.0, value=2.0, step=0.5)
                    notes_input = st.text_area("Learning Notes / Summary", placeholder="Key topics reviewed, code built, or concepts mastered...")

                    if st.form_submit_button("📝 Record Study Activity"):
                        cid_selected = course_map[selected_course_title]
                        ok, err = log_learning_activity(current_emp_id, cid_selected, hours_input, notes_input)
                        if ok:
                            st.success(f"✅ Successfully logged {hours_input} hrs for {selected_course_title}!")
                            st.rerun()
                        else:
                            st.error(err)
            else:
                st.info("ℹ️ Enroll in a course first to record study activity logs.")

        with track_tab3:
            st.subheader("🏆 Unlocked Achievement Badges")
            if tracker_data["badges"]:
                b_cols = st.columns(min(4, len(tracker_data["badges"])))
                for i, b in enumerate(tracker_data["badges"]):
                    with b_cols[i % len(b_cols)]:
                        st.markdown(f"""
                        <div class="badge-pill-card">
                            <div style="font-size: 2.2rem; margin-bottom: 6px;">{b['icon']}</div>
                            <h4 style="margin: 0; color: #1E293B;">{b['title']}</h4>
                            <p style="font-size: 0.85rem; color: #64748B; margin-top: 4px;">{b['desc']}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.caption("Enroll in courses and log study hours to unlock achievements.")

            if tracker_data["recent_logs"]:
                st.markdown("---")
                st.subheader("📜 Recent Learning Activity History")
                for rlog in tracker_data["recent_logs"]:
                    st.caption(f"⏱️ **{rlog['hours_spent']} hrs** on *{rlog['course_title']}* ({rlog['logged_at']})")
                    if rlog["notes"]:
                        st.write(f"> 💬 {rlog['notes']}")


# =============================================================
# PAGE 7: HR DASHBOARD – WORKFORCE TALENT INTELLIGENCE
# =============================================================
elif selected_page == PAGE_HR_DASHBOARD:
    render_section_header(
        title="📊 HR Workforce Talent Intelligence",
        subtitle="Company-wide skill distribution, department benchmark readiness, and organizational skill deficits.",
        badge="📊 MACRO TALENT INTELLIGENCE",
        lottie_filename="growth.json",
        image_url="https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=600&q=80",
        anim_height=160,
        key_prefix="hr_header"
    )

    st.markdown("""
    <div style="background: #F1F5F9; border-left: 4px solid #475569; padding: 10px 16px; border-radius: 8px; margin-bottom: 1.25rem;">
        🔒 <b>Enterprise HR Administration:</b> Macro workforce analytics and talent mobility metrics are restricted to corporate HR leadership. Individual employee records remain confidential.
    </div>
    """, unsafe_allow_html=True)

    overview = get_workforce_overview()

    # Macro KPIs
    hkpi1, hkpi2, hkpi3, hkpi4 = st.columns(4)
    with hkpi1:
        st.metric("👥 Total Workforce Tracked", overview["total_employees"])
    with hkpi2:
        st.metric("🎯 Company Avg Skill Readiness", f"{overview['avg_readiness']}%")
    with hkpi3:
        st.metric("⏱️ Cumulative Training Hours", f"{overview['overall_training_hours']} hrs")
    with hkpi4:
        st.metric("📚 Total Active Course Enrollments", overview["total_enrollments"])

    st.markdown("<br>", unsafe_allow_html=True)

    hr_tab1, hr_tab2, hr_tab3 = st.tabs([
        "🏢 Departmental Upskilling & Talent Mobility",
        "⚠️ Organizational Skill Deficits & Heatmap",
        "👥 Workforce Talent Mobility Master Index"
    ])

    with hr_tab1:
        col_hr1, col_hr2 = st.columns([1.3, 1])
        with col_hr1:
            st.subheader("🏢 Departmental Upskilling Readiness (%)")
            dept_fig = create_department_readiness_chart(overview["department_metrics"])
            # FIXED NON-INTERACTIVE CHART
            render_static_chart(dept_fig, key="hr_dept_chart")

        with col_hr2:
            st.subheader("🔄 Talent Mobility Proportions")
            mobility_fig = create_talent_mobility_donut(overview["employee_readiness_df"])
            # FIXED NON-INTERACTIVE CHART
            render_static_chart(mobility_fig, key="hr_mobility_donut")

    with hr_tab2:
        col_hr3, col_hr4 = st.columns([1, 1.3])
        with col_hr3:
            st.subheader("⚠️ Top Critical Organizational Skill Gaps")
            gaps_fig = create_org_gaps_chart(overview["top_org_gaps"])
            # FIXED NON-INTERACTIVE CHART
            render_static_chart(gaps_fig, key="hr_org_gaps_chart")

        with col_hr4:
            st.subheader("🗺️ Departmental Skill Proficiency Heatmap")
            heatmap_fig = create_skill_distribution_heatmap()
            # FIXED NON-INTERACTIVE CHART
            render_static_chart(heatmap_fig, key="hr_heatmap_chart")

    with hr_tab3:
        st.subheader("👥 Employee Talent Mobility Index Table")
        if not overview["employee_readiness_df"].empty:
            st.dataframe(
                overview["employee_readiness_df"][[
                    "name", "department", "current_role", "target_role", "readiness_score", "critical_gap_count", "mobility_status"
                ]],
                use_container_width=True,
                hide_index=True
            )
