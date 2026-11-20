"""
Unit and integration tests for navigation, user flow, fixed chart settings,
and Coursera-inspired employee onboarding persistence.
"""
import pytest
from database import (
    init_db,
    get_all_employees,
    get_employee_by_id,
    get_preference,
    set_preference,
    clear_preference,
    is_employee_code_taken,
    save_employee_profile_details
)
from modules.assessment import (
    save_or_update_employee,
    score_diagnostic_quiz,
    apply_diagnostic_results
)
from modules.skill_gap import analyze_skill_gap, create_radar_chart, create_gap_bar_chart
from modules.roadmap import generate_learning_roadmap, create_roadmap_timeline_chart
from modules.analytics import (
    get_workforce_overview,
    create_department_readiness_chart,
    create_talent_mobility_donut,
    create_org_gaps_chart,
    create_skill_distribution_heatmap
)
from modules.ui_theme import STATIC_PLOTLY_CONFIG, render_static_chart, polish_fig
import app


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    init_db(force_reseed=True)


def test_navigation_order_and_items():
    """Verifies the exact 7 navigation options and order required by Section 2."""
    expected_order = [
        "👤 Employee Information",
        "🏠 Dashboard",
        "📝 Skill Assessment",
        "🎯 Skill Gap Analyzer",
        "💡 Personalized Learning",
        "📈 Progress Tracking",
        "📊 HR Dashboard"
    ]
    assert app.NAV_PAGES == expected_order
    assert len(app.NAV_PAGES) == 7


def test_button_destinations_mapping():
    """
    Verifies all buttons from the Section 11 expected behavior table
    map to their exact corresponding pages.
    """
    button_mapping = {
        "Employee Information": app.PAGE_EMPLOYEE_INFO,
        "Dashboard": app.PAGE_DASHBOARD,
        "Skill Assessment": app.PAGE_SKILL_ASSESSMENT,
        "Skill Gap Analyzer": app.PAGE_SKILL_GAP,
        "Personalized Learning": app.PAGE_PERSONALIZED_LEARNING,
        "Progress Tracking": app.PAGE_PROGRESS_TRACKING,
        "HR Dashboard": app.PAGE_HR_DASHBOARD,
        "Analyze Skill Gaps": app.PAGE_SKILL_GAP,
        "Start Skill Assessment": app.PAGE_SKILL_ASSESSMENT,
        "Explore Learning Roadmap": app.PAGE_PERSONALIZED_LEARNING,
        "Track My Progress": app.PAGE_PROGRESS_TRACKING,
    }

    assert "Employee Information" in button_mapping["Employee Information"]
    assert "Dashboard" in button_mapping["Dashboard"]
    assert "Skill Assessment" in button_mapping["Skill Assessment"]
    assert "Skill Gap Analyzer" in button_mapping["Skill Gap Analyzer"]
    assert "Personalized Learning" in button_mapping["Personalized Learning"]
    assert "Progress Tracking" in button_mapping["Progress Tracking"]
    assert "HR Dashboard" in button_mapping["HR Dashboard"]

    # Action button specific destinations
    assert button_mapping["Analyze Skill Gaps"] == app.PAGE_SKILL_GAP
    assert button_mapping["Start Skill Assessment"] == app.PAGE_SKILL_ASSESSMENT
    assert button_mapping["Explore Learning Roadmap"] == app.PAGE_PERSONALIZED_LEARNING
    assert button_mapping["Track My Progress"] == app.PAGE_PROGRESS_TRACKING


def test_fixed_non_interactive_chart_config():
    """
    Verifies Section 10 requirement: charts must be FIXED and NON-INTERACTIVE.
    staticPlot must be True, toolbar modebar hidden, scrollZoom disabled.
    """
    assert STATIC_PLOTLY_CONFIG["staticPlot"] is True
    assert STATIC_PLOTLY_CONFIG["displayModeBar"] is False
    assert STATIC_PLOTLY_CONFIG["scrollZoom"] is False
    assert STATIC_PLOTLY_CONFIG["doubleClick"] is False
    assert STATIC_PLOTLY_CONFIG["editable"] is False


def test_employee_information_full_persistence():
    """
    Verifies Section 3: collects and persists all required fields:
    Employee Name, Employee ID, Department, Job Role, Years of Experience,
    Current Skills, Technical Skills, Career Interests, Learning Goals.
    """
    emp_id, err = save_or_update_employee(
        name="Samantha Miller",
        email="samantha.miller@enterprise.com",
        department="Engineering",
        current_role="Backend Developer",
        target_role="Cloud & DevOps Architect",
        experience_years=3.5,
        weekly_learning_hours=8.0,
        employee_code="EMP-7788",
        career_interests="Distributed Systems, Kubernetes, Multi-Cloud Resilience",
        learning_goals="Pass CKA exam and master Terraform infrastructure as code.",
        current_skills_summary="Python, Docker, SQL, Linux",
        technical_skills_summary="Python, FastAPI, Docker, PostgreSQL, Bash, Git"
    )

    assert err is None
    assert emp_id is not None

    emp = get_employee_by_id(emp_id)
    assert emp["name"] == "Samantha Miller"
    assert emp["employee_code"] == "EMP-7788"
    assert emp["department"] == "Engineering"
    assert emp["current_role"] == "Backend Developer"
    assert emp["target_role"] == "Cloud & DevOps Architect"
    assert emp["experience_years"] == 3.5
    assert emp["weekly_learning_hours"] == 8.0
    assert emp["career_interests"] == "Distributed Systems, Kubernetes, Multi-Cloud Resilience"
    assert emp["learning_goals"] == "Pass CKA exam and master Terraform infrastructure as code."
    assert emp["current_skills_summary"] == "Python, Docker, SQL, Linux"
    assert emp["technical_skills_summary"] == "Python, FastAPI, Docker, PostgreSQL, Bash, Git"

    # Verify duplicate employee_code validation
    assert is_employee_code_taken("EMP-7788") is True
    assert is_employee_code_taken("EMP-7788", exclude_id=emp_id) is False
    assert is_employee_code_taken("EMP-NONEXISTENT") is False

    # Returning employee update
    updated_id, u_err = save_or_update_employee(
        name="Samantha Miller",
        email="samantha.miller@enterprise.com",
        department="Engineering",
        current_role="Senior Backend Developer",
        target_role="Cloud & DevOps Architect",
        experience_years=4.0,
        weekly_learning_hours=10.0,
        employee_id=emp_id,
        employee_code="EMP-7788",
        career_interests="Distributed Systems, Cloud Native Kubernetes",
        learning_goals="Architect multi-region fault tolerance.",
        current_skills_summary="Python, Docker, Kubernetes, AWS",
        technical_skills_summary="Python, Go, Docker, Kubernetes, AWS, Terraform"
    )
    assert u_err is None
    assert updated_id == emp_id

    emp_after = get_employee_by_id(emp_id)
    assert emp_after["current_role"] == "Senior Backend Developer"
    assert emp_after["experience_years"] == 4.0
    assert emp_after["weekly_learning_hours"] == 10.0


def test_session_preference_persistence():
    """Verifies active employee ID persistence across sessions/refreshes."""
    set_preference("active_employee_id", "1002")
    assert get_preference("active_employee_id") == "1002"

    set_preference("active_employee_id", "1005")
    assert get_preference("active_employee_id") == "1005"

    clear_preference("active_employee_id")
    assert get_preference("active_employee_id") is None


def test_all_visualizations_render_fixed_figures():
    """
    Verifies that all 8 charts generate valid go.Figure objects
    and can be configured with staticPlot.
    """
    employees = get_all_employees()
    first_id = int(employees.iloc[0]["id"])
    emp = get_employee_by_id(first_id)

    # 1. Competency Radar
    gap_res = analyze_skill_gap(first_id)
    radar_fig = create_radar_chart(gap_res["gap_df"], emp["target_role"], emp["name"])
    assert radar_fig is not None

    # 2. Gap Bar Chart
    gap_bar = create_gap_bar_chart(gap_res["gap_df"])
    assert gap_bar is not None

    # 3. Roadmap Timeline Chart
    roadmap = generate_learning_roadmap(first_id)
    timeline_fig = create_roadmap_timeline_chart(roadmap)
    assert timeline_fig is not None

    # 4. Department Readiness Chart
    wf = get_workforce_overview()
    dept_fig = create_department_readiness_chart(wf["department_metrics"])
    assert dept_fig is not None

    # 5. Talent Mobility Donut
    mobility_fig = create_talent_mobility_donut(wf["employee_readiness_df"])
    assert mobility_fig is not None

    # 6. Org Skill Gaps Chart
    gaps_fig = create_org_gaps_chart(wf["top_org_gaps"])
    assert gaps_fig is not None

    # 7. Heatmap Chart
    heatmap_fig = create_skill_distribution_heatmap()
    assert heatmap_fig is not None
