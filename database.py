"""
Database layer for SkillPath AI.
Manages SQLite schema, migrations, connection utilities, and verified seed data.
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from config import DB_PATH, DATA_DIR


def get_db_connection() -> sqlite3.Connection:
    """
    Returns an active SQLite connection with row factory enabled for dict-like access.
    Ensures data directory exists.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(force_reseed: bool = False) -> None:
    """
    Initializes the database schema and seeds initial corporate data if empty or forced.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Employees Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                department TEXT NOT NULL,
                current_role TEXT NOT NULL,
                target_role TEXT NOT NULL,
                experience_years REAL NOT NULL DEFAULT 0.0,
                weekly_learning_hours REAL NOT NULL DEFAULT 5.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Skills Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                description TEXT
            )
        """)
        
        # 3. Target Role Requirements Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_name TEXT NOT NULL,
                skill_id INTEGER NOT NULL,
                required_level INTEGER NOT NULL CHECK (required_level BETWEEN 1 AND 5),
                is_core INTEGER NOT NULL DEFAULT 1 CHECK (is_core IN (0, 1)),
                FOREIGN KEY (skill_id) REFERENCES skills (id) ON DELETE CASCADE,
                UNIQUE (role_name, skill_id)
            )
        """)
        
        # 4. Employee Skills Table (Assessed proficiency)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                proficiency_level INTEGER NOT NULL CHECK (proficiency_level BETWEEN 1 AND 5),
                last_assessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills (id) ON DELETE CASCADE,
                UNIQUE (employee_id, skill_id)
            )
        """)
        
        # 5. Course Catalog Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                provider TEXT NOT NULL,
                platform_url TEXT NOT NULL,
                skill_id INTEGER NOT NULL,
                level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 5),
                duration_hours REAL NOT NULL,
                rating REAL NOT NULL CHECK (rating BETWEEN 0 AND 5),
                description TEXT,
                tags TEXT,
                FOREIGN KEY (skill_id) REFERENCES skills (id) ON DELETE CASCADE
            )
        """)
        
        # 6. Course Enrollments Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('not_started', 'in_progress', 'completed')),
                progress_pct INTEGER NOT NULL DEFAULT 0 CHECK (progress_pct BETWEEN 0 AND 100),
                enrolled_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_date TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
                UNIQUE (employee_id, course_id)
            )
        """)
        
        # 7. Learning Activity Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                hours_spent REAL NOT NULL CHECK (hours_spent > 0),
                notes TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
            )
        """)
        
        _ensure_employee_profile_columns(cursor)
        _ensure_preferences_table(cursor)
        conn.commit()

        # Check if seed data exists
        cursor.execute("SELECT COUNT(*) FROM skills")
        count = cursor.fetchone()[0]
        
        if count == 0 or force_reseed:
            seed_initial_data(conn)


def seed_initial_data(conn: sqlite3.Connection) -> None:
    """
    Seeds verified industry skills, role benchmarks, verified genuine course links, and realistic employees.
    """
    cursor = conn.cursor()
    
    # Clear existing if force reseeding
    cursor.execute("DELETE FROM learning_logs")
    cursor.execute("DELETE FROM enrollments")
    cursor.execute("DELETE FROM courses")
    cursor.execute("DELETE FROM employee_skills")
    cursor.execute("DELETE FROM role_requirements")
    cursor.execute("DELETE FROM skills")
    cursor.execute("DELETE FROM employees")
    cursor.execute("DELETE FROM app_preferences WHERE key = 'active_employee_id'")

    # 1. Core Skills
    skills_data = [
        # Programming & Software
        ("Python Programming", "Programming & Software", "Core Python language, data structures, and standard libraries"),
        ("FastAPI & REST APIs", "Programming & Software", "Modern async backend microservices and API design"),
        ("React & Frontend", "Programming & Software", "Component architecture, state management, and modern web UI"),
        ("System Design & Architecture", "Programming & Software", "Scalable distributed systems, caching, and database sharding"),
        
        # Data Science & AI
        ("SQL & Relational Databases", "Data Science & AI", "Complex queries, indexing, joins, and data modeling"),
        ("Machine Learning", "Data Science & AI", "Supervised/unsupervised algorithms, evaluation metrics, and Scikit-Learn"),
        ("Deep Learning & Neural Networks", "Data Science & AI", "PyTorch/TensorFlow, CNNs, Transformers, and gradient descent"),
        ("NLP & LLMs", "Data Science & AI", "Natural language processing, embeddings, prompt engineering, and fine-tuning"),
        ("Data Visualization", "Data Science & AI", "Exploratory data analysis, Plotly, Dash, and storytelling with data"),
        
        # Cloud & DevOps
        ("Docker & Containerization", "Cloud & DevOps", "Dockerfiles, multi-stage builds, and container orchestration"),
        ("Kubernetes", "Cloud & DevOps", "Pods, deployments, services, ingress, and cluster management"),
        ("AWS Cloud Architecture", "Cloud & DevOps", "EC2, S3, IAM, VPC, Lambda, and cloud architecture patterns"),
        ("CI/CD & GitHub Actions", "Cloud & DevOps", "Automated build, test, and deployment pipelines"),
        ("Site Reliability & Monitoring", "Cloud & DevOps", "Observability, Prometheus, Grafana, and SLA/SLO management"),
        
        # Cybersecurity
        ("Cybersecurity Fundamentals", "Cybersecurity", "Threat models, encryption, identity, and security posture"),
        ("Network Security & Pentesting", "Cybersecurity", "Packet inspection, vulnerability analysis, and OWASP Top 10"),
        
        # Product & Agile Leadership
        ("Product Analytics & Metrics", "Product & Agile Leadership", "A/B testing, user funnels, churn analysis, and OKRs"),
        ("Agile & Scrum Methodologies", "Product & Agile Leadership", "Sprint planning, user stories, backlog grooming, and retrospectives"),
    ]
    
    cursor.executemany("INSERT INTO skills (name, category, description) VALUES (?, ?, ?)", skills_data)
    
    # Retrieve skill IDs map
    cursor.execute("SELECT id, name FROM skills")
    skill_map = {row["name"]: row["id"] for row in cursor.fetchall()}

    # 2. Target Role Benchmarks (Required level 1-5, is_core 1 or 0)
    role_benchmarks = [
        # AI / ML Engineer
        ("AI / ML Engineer", "Python Programming", 4, 1),
        ("AI / ML Engineer", "Machine Learning", 4, 1),
        ("AI / ML Engineer", "Deep Learning & Neural Networks", 4, 1),
        ("AI / ML Engineer", "NLP & LLMs", 3, 1),
        ("AI / ML Engineer", "FastAPI & REST APIs", 3, 0),
        ("AI / ML Engineer", "Docker & Containerization", 3, 0),
        ("AI / ML Engineer", "SQL & Relational Databases", 3, 0),

        # Data Scientist
        ("Data Scientist", "Python Programming", 4, 1),
        ("Data Scientist", "SQL & Relational Databases", 4, 1),
        ("Data Scientist", "Machine Learning", 4, 1),
        ("Data Scientist", "Data Visualization", 4, 1),
        ("Data Scientist", "Deep Learning & Neural Networks", 2, 0),
        ("Data Scientist", "Product Analytics & Metrics", 3, 0),

        # Cloud & DevOps Architect
        ("Cloud & DevOps Architect", "AWS Cloud Architecture", 5, 1),
        ("Cloud & DevOps Architect", "Kubernetes", 4, 1),
        ("Cloud & DevOps Architect", "Docker & Containerization", 4, 1),
        ("Cloud & DevOps Architect", "CI/CD & GitHub Actions", 4, 1),
        ("Cloud & DevOps Architect", "Site Reliability & Monitoring", 4, 1),
        ("Cloud & DevOps Architect", "Python Programming", 3, 0),
        ("Cloud & DevOps Architect", "Cybersecurity Fundamentals", 3, 0),

        # Senior Full Stack Developer
        ("Senior Full Stack Developer", "Python Programming", 4, 1),
        ("Senior Full Stack Developer", "FastAPI & REST APIs", 4, 1),
        ("Senior Full Stack Developer", "React & Frontend", 4, 1),
        ("Senior Full Stack Developer", "System Design & Architecture", 4, 1),
        ("Senior Full Stack Developer", "SQL & Relational Databases", 3, 1),
        ("Senior Full Stack Developer", "Docker & Containerization", 3, 0),
        ("Senior Full Stack Developer", "CI/CD & GitHub Actions", 3, 0),

        # Cybersecurity Analyst
        ("Cybersecurity Analyst", "Cybersecurity Fundamentals", 5, 1),
        ("Cybersecurity Analyst", "Network Security & Pentesting", 4, 1),
        ("Cybersecurity Analyst", "Python Programming", 3, 0),
        ("Cybersecurity Analyst", "AWS Cloud Architecture", 3, 0),
        ("Cybersecurity Analyst", "Docker & Containerization", 2, 0),

        # Product Manager (Tech)
        ("Product Manager (Tech)", "Product Analytics & Metrics", 5, 1),
        ("Product Manager (Tech)", "Agile & Scrum Methodologies", 5, 1),
        ("Product Manager (Tech)", "SQL & Relational Databases", 3, 1),
        ("Product Manager (Tech)", "System Design & Architecture", 2, 0),
        ("Product Manager (Tech)", "Data Visualization", 3, 0),

        # Data Analyst
        ("Data Analyst", "SQL & Relational Databases", 4, 1),
        ("Data Analyst", "Data Visualization", 4, 1),
        ("Data Analyst", "Python Programming", 3, 1),
        ("Data Analyst", "Product Analytics & Metrics", 3, 0),

        # Site Reliability Engineer (SRE)
        ("Site Reliability Engineer (SRE)", "Site Reliability & Monitoring", 5, 1),
        ("Site Reliability Engineer (SRE)", "Kubernetes", 4, 1),
        ("Site Reliability Engineer (SRE)", "Docker & Containerization", 4, 1),
        ("Site Reliability Engineer (SRE)", "CI/CD & GitHub Actions", 4, 1),
        ("Site Reliability Engineer (SRE)", "Python Programming", 3, 0),
        ("Site Reliability Engineer (SRE)", "System Design & Architecture", 3, 0),
    ]

    for role_name, skill_name, req_level, is_core in role_benchmarks:
        if skill_name in skill_map:
            cursor.execute("""
                INSERT INTO role_requirements (role_name, skill_id, required_level, is_core)
                VALUES (?, ?, ?, ?)
            """, (role_name, skill_map[skill_name], req_level, is_core))

    # 3. Verified Courses with Authentic URLs (Coursera, edX, MIT OCW, freeCodeCamp, official docs)
    courses_data = [
        # Python
        ("CS50's Introduction to Computer Science", "Harvard / edX", "https://cs50.harvard.edu/x/", 
         "Python Programming", 1, 30.0, 4.9, "World-renowned introductory computer science course by Prof. David J. Malan.", "python,beginner,cs"),
        ("Scientific Computing with Python", "freeCodeCamp", "https://www.freecodecamp.org/learn/scientific-computing-with-python/", 
         "Python Programming", 2, 25.0, 4.8, "Hands-on projects covering algorithms, data structures, and Python programming.", "python,intermediate"),
        ("MIT 6.0001: Intro to Python & Algorithms", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/", 
         "Python Programming", 3, 35.0, 4.9, "Rigorous algorithmic foundations, computational problem solving, and optimization.", "python,algorithms,advanced"),

        # SQL
        ("Relational Database Certification", "freeCodeCamp", "https://www.freecodecamp.org/learn/relational-database/", 
         "SQL & Relational Databases", 2, 20.0, 4.8, "Learn PostgreSQL, Bash, schema design, and complex queries hands-on.", "sql,database,intermediate"),
        ("Google Data Analytics Professional Certificate", "Coursera / Google", "https://www.coursera.org/professional-certificates/google-data-analytics", 
         "SQL & Relational Databases", 3, 40.0, 4.8, "Comprehensive enterprise data analysis, SQL joins, aggregations, and business metrics.", "sql,analytics,advanced"),

        # Machine Learning
        ("Machine Learning Specialization", "DeepLearning.AI / Coursera", "https://www.deeplearning.ai/courses/machine-learning-specialization/", 
         "Machine Learning", 2, 35.0, 4.9, "Created by Andrew Ng: Supervised learning, classification, neural nets, and recommendation systems.", "ml,andrew-ng,core"),
        ("CS50's Introduction to AI with Python", "Harvard / edX", "https://www.edx.org/learn/artificial-intelligence/harvard-university-cs50-s-introduction-to-artificial-intelligence-with-python", 
         "Machine Learning", 3, 30.0, 4.8, "Explore graph search algorithms, probability, Markov models, and machine learning models.", "ai,python,intermediate"),

        # Deep Learning & NLP
        ("Deep Learning Specialization", "DeepLearning.AI", "https://www.deeplearning.ai/courses/deep-learning-specialization/", 
         "Deep Learning & Neural Networks", 3, 45.0, 4.9, "Master deep neural networks, CNNs for computer vision, and sequence models.", "deep-learning,pytorch,expert"),
        ("Generative AI for Everyone", "DeepLearning.AI", "https://www.deeplearning.ai/courses/generative-ai-for-everyone/", 
         "NLP & LLMs", 1, 10.0, 4.8, "Essential executive and developer primer on GenAI, LLMs, and real-world deployment.", "genai,llm,beginner"),
        ("Natural Language Processing with Attention Models", "DeepLearning.AI / Coursera", "https://www.coursera.org/learn/attention-models-in-nlp", 
         "NLP & LLMs", 3, 25.0, 4.8, "Transformers, BERT, GPT architectures, and self-attention mechanisms.", "nlp,transformers,advanced"),

        # Cloud & DevOps
        ("AWS Cloud Practitioner Essentials", "Amazon Web Services", "https://aws.amazon.com/training/digital/aws-cloud-practitioner-essentials/", 
         "AWS Cloud Architecture", 1, 15.0, 4.7, "Official AWS fundamentals covering computing, storage, global infrastructure, and security.", "aws,cloud,beginner"),
        ("AWS Solutions Architect Associate Prep", "Coursera / AWS", "https://www.coursera.org/learn/aws-cloud-solutions-architect", 
         "AWS Cloud Architecture", 3, 35.0, 4.8, "Design scalable, highly available, and cost-optimized systems on AWS.", "aws,architect,advanced"),
        ("Docker & Kubernetes Hands-on Course", "freeCodeCamp", "https://www.freecodecamp.org/news/docker-and-kubernetes-course/", 
         "Docker & Containerization", 2, 16.0, 4.8, "Complete practical guide from container basics to production deployment.", "docker,containers,practical"),
        ("Kubernetes Interactive Basics", "Kubernetes.io", "https://kubernetes.io/docs/tutorials/kubernetes-basics/", 
         "Kubernetes", 3, 20.0, 4.7, "Official hands-on walkthrough of deploying, scaling, and updating apps on k8s.", "kubernetes,k8s,cloud"),
        ("Automating Workflows with GitHub Actions", "GitHub Skills", "https://skills.github.com/", 
         "CI/CD & GitHub Actions", 2, 12.0, 4.8, "Interactive repository-based learning for building CI/CD test and deployment pipelines.", "cicd,github,automation"),
        ("Site Reliability Engineering: Measuring SRE", "Coursera / Google Cloud", "https://www.coursera.org/learn/site-reliability-engineering-slos", 
         "Site Reliability & Monitoring", 4, 18.0, 4.7, "Google's methodology for engineering reliable, observable, and resilient services.", "sre,observability,google"),

        # Software & APIs
        ("FastAPI Official Interactive Tutorial", "FastAPI Documentation", "https://fastapi.tiangolo.com/tutorial/", 
         "FastAPI & REST APIs", 2, 14.0, 4.9, "Build high-performance asynchronous RESTful APIs with Pydantic validation.", "api,fastapi,backend"),
        ("Frontend Development Libraries (React)", "freeCodeCamp", "https://www.freecodecamp.org/learn/front-end-development-libraries/", 
         "React & Frontend", 2, 30.0, 4.7, "Learn React, Redux, Sass, and stateful interactive frontends.", "react,frontend,javascript"),
        ("System Design Primer & Scalability", "GitHub / Donne Martin", "https://github.com/donnemartin/system-design-primer", 
         "System Design & Architecture", 4, 30.0, 4.9, "Industry-standard primer for designing large-scale distributed enterprise systems.", "system-design,architecture"),

        # Cybersecurity
        ("Google Cybersecurity Professional Certificate", "Google / Coursera", "https://www.coursera.org/professional-certificates/google-cybersecurity", 
         "Cybersecurity Fundamentals", 2, 35.0, 4.8, "Comprehensive hands-on training in network defense, SIEM tools, and incident response.", "security,google,defense"),
        ("OWASP Top 10 Security Risks & Mitigations", "OWASP Foundation", "https://owasp.org/www-project-top-ten/", 
         "Network Security & Pentesting", 3, 15.0, 4.8, "Identify and patch critical web vulnerabilities like injection, broken auth, and SSRF.", "security,owasp,pentest"),

        # Product & Agile
        ("Agile with Atlassian Jira", "Atlassian / Coursera", "https://www.coursera.org/learn/agile-atlassian-jira", 
         "Agile & Scrum Methodologies", 2, 14.0, 4.7, "Master agile workflows, sprint planning, Kanban boards, and team velocity.", "agile,scrum,jira"),
        ("Data-Driven Product Management", "Coursera / Highbrow", "https://www.coursera.org/learn/uva-darden-data-driven-product-management", 
         "Product Analytics & Metrics", 3, 20.0, 4.6, "Formulate data hypotheses, design A/B experiments, and drive product growth.", "product,metrics,growth"),
        ("Interactive Data Storytelling with Plotly", "Plotly Community", "https://plotly.com/python/", 
         "Data Visualization", 2, 15.0, 4.8, "Interactive graphing, dashboards, and storytelling using Python Plotly.", "visualization,plotly,python"),
    ]

    for title, provider, url, skill_name, level, duration, rating, desc, tags in courses_data:
        if skill_name in skill_map:
            cursor.execute("""
                INSERT INTO courses (title, provider, platform_url, skill_id, level, duration_hours, rating, description, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, provider, url, skill_map[skill_name], level, duration, rating, desc, tags))

    # 4. Realistic Corporate Employees
    employees_data = [
        ("Aarav Sharma", "aarav.sharma@example.com", "Engineering", "Software Engineer", "AI / ML Engineer", 3.0, 6.0),
        ("Priya Patel", "priya.patel@example.com", "Data & Analytics", "Junior Data Analyst", "Data Scientist", 1.5, 8.0),
        ("Rohan Verma", "rohan.verma@example.com", "Cloud & Infrastructure", "Systems Administrator", "Cloud & DevOps Architect", 4.0, 5.0),
        ("Ananya Iyer", "ananya.iyer@example.com", "Engineering", "Backend Developer", "Senior Full Stack Developer", 2.5, 7.0),
        ("Vikram Malhotra", "vikram.malhotra@example.com", "Cybersecurity", "IT Support Specialist", "Cybersecurity Analyst", 2.0, 6.0),
        ("Sneha Kulkarni", "sneha.kulkarni@example.com", "Product & Design", "Associate Product Manager", "Product Manager (Tech)", 2.0, 4.0),
        ("Arjun Nair", "arjun.nair@example.com", "Engineering", "DevOps Engineer", "Site Reliability Engineer (SRE)", 3.5, 5.0),
        ("Meera Sen", "meera.sen@example.com", "Data & Analytics", "BI Developer", "Data Analyst", 2.0, 5.0),
        ("Kavita Rao", "kavita.rao@example.com", "Engineering", "Full Stack Developer", "AI / ML Engineer", 3.0, 8.0),
        ("Devendra Das", "devendra.das@example.com", "Cloud & Infrastructure", "Cloud Operator", "Cloud & DevOps Architect", 2.0, 6.0)
    ]

    cursor.executemany("""
        INSERT INTO employees (name, email, department, current_role, target_role, experience_years, weekly_learning_hours)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, employees_data)

    # 5. Seed Assessed Skills for Employees
    cursor.execute("SELECT id, email FROM employees")
    emp_map = {row["email"]: row["id"] for row in cursor.fetchall()}
    
    # Pre-populate realistic skill baselines for seeded employees (by email)
    sample_employee_skills = [
        # Aarav Sharma (SWE wanting to become AI/ML Engineer)
        ("aarav.sharma@example.com", "Python Programming", 3),
        ("aarav.sharma@example.com", "FastAPI & REST APIs", 3),
        ("aarav.sharma@example.com", "SQL & Relational Databases", 3),
        ("aarav.sharma@example.com", "Machine Learning", 1),
        ("aarav.sharma@example.com", "Deep Learning & Neural Networks", 1),
        ("aarav.sharma@example.com", "Docker & Containerization", 2),
        
        # Priya Patel (Junior Data Analyst -> Data Scientist)
        ("priya.patel@example.com", "SQL & Relational Databases", 3),
        ("priya.patel@example.com", "Data Visualization", 3),
        ("priya.patel@example.com", "Python Programming", 2),
        ("priya.patel@example.com", "Machine Learning", 1),
        ("priya.patel@example.com", "Product Analytics & Metrics", 2),

        # Rohan Verma (SysAdmin -> Cloud & DevOps Architect)
        ("rohan.verma@example.com", "AWS Cloud Architecture", 2),
        ("rohan.verma@example.com", "Docker & Containerization", 2),
        ("rohan.verma@example.com", "Kubernetes", 1),
        ("rohan.verma@example.com", "CI/CD & GitHub Actions", 2),
        ("rohan.verma@example.com", "Site Reliability & Monitoring", 2),
        ("rohan.verma@example.com", "Python Programming", 2),

        # Ananya Iyer (Backend -> Senior Full Stack)
        ("ananya.iyer@example.com", "Python Programming", 3),
        ("ananya.iyer@example.com", "FastAPI & REST APIs", 3),
        ("ananya.iyer@example.com", "SQL & Relational Databases", 3),
        ("ananya.iyer@example.com", "React & Frontend", 1),
        ("ananya.iyer@example.com", "System Design & Architecture", 2),

        # Vikram Malhotra (IT Support -> Cybersecurity Analyst)
        ("vikram.malhotra@example.com", "Cybersecurity Fundamentals", 2),
        ("vikram.malhotra@example.com", "Network Security & Pentesting", 1),
        ("vikram.malhotra@example.com", "Python Programming", 1),

        # Sneha Kulkarni (APM -> Tech PM)
        ("sneha.kulkarni@example.com", "Agile & Scrum Methodologies", 3),
        ("sneha.kulkarni@example.com", "Product Analytics & Metrics", 2),
        ("sneha.kulkarni@example.com", "SQL & Relational Databases", 1),
        ("sneha.kulkarni@example.com", "System Design & Architecture", 1),

        # Arjun Nair (DevOps -> SRE)
        ("arjun.nair@example.com", "Docker & Containerization", 3),
        ("arjun.nair@example.com", "Kubernetes", 2),
        ("arjun.nair@example.com", "CI/CD & GitHub Actions", 3),
        ("arjun.nair@example.com", "Site Reliability & Monitoring", 2),
        ("arjun.nair@example.com", "Python Programming", 2),

        # Meera Sen (BI -> Data Analyst)
        ("meera.sen@example.com", "SQL & Relational Databases", 3),
        ("meera.sen@example.com", "Data Visualization", 3),
        ("meera.sen@example.com", "Python Programming", 2),

        # Kavita Rao (Full Stack -> AI/ML)
        ("kavita.rao@example.com", "Python Programming", 3),
        ("kavita.rao@example.com", "React & Frontend", 3),
        ("kavita.rao@example.com", "Machine Learning", 2),

        # Devendra Das (Cloud Operator -> Cloud Architect)
        ("devendra.das@example.com", "AWS Cloud Architecture", 2),
        ("devendra.das@example.com", "Docker & Containerization", 2)
    ]

    for emp_email, skill_name, prof_level in sample_employee_skills:
        emp_id = emp_map.get(emp_email)
        if emp_id and skill_name in skill_map:
            cursor.execute("""
                INSERT INTO employee_skills (employee_id, skill_id, proficiency_level)
                VALUES (?, ?, ?)
            """, (emp_id, skill_map[skill_name], prof_level))

    # 6. Seed Sample Enrollments & Logs for realistic tracker stats
    cursor.execute("SELECT id FROM courses WHERE title LIKE '%Scientific Computing with Python%'")
    c1 = cursor.fetchone()
    cursor.execute("SELECT id FROM courses WHERE title LIKE '%AWS Cloud Practitioner%'")
    c2 = cursor.fetchone()
    cursor.execute("SELECT id FROM courses WHERE title LIKE '%Relational Database Certification%'")
    c3 = cursor.fetchone()

    emp_aarav = emp_map.get("aarav.sharma@example.com")
    emp_priya = emp_map.get("priya.patel@example.com")
    emp_rohan = emp_map.get("rohan.verma@example.com")

    if c1 and c2 and c3 and emp_aarav and emp_priya and emp_rohan:
        cursor.execute("""
            INSERT INTO enrollments (employee_id, course_id, status, progress_pct)
            VALUES 
                (?, ?, 'in_progress', 65),
                (?, ?, 'completed', 100),
                (?, ?, 'in_progress', 40)
        """, (emp_aarav, c1[0], emp_priya, c3[0], emp_rohan, c2[0]))

        cursor.execute("""
            INSERT INTO learning_logs (employee_id, course_id, hours_spent, notes)
            VALUES 
                (?, ?, 4.5, 'Completed modular functions and recursion exercises.'),
                (?, ?, 12.0, 'Finished complex multi-table SQL queries and subqueries.'),
                (?, ?, 3.0, 'Reviewed AWS VPC and security groups architecture.')
        """, (emp_aarav, c1[0], emp_priya, c3[0], emp_rohan, c2[0]))

    # 7. Seed Onboarding Profile Details
    seed_profiles = {
        "aarav.sharma@example.com": {
            "employee_code": "EMP-1001",
            "career_interests": "Machine Learning, Deep Learning, Distributed AI Systems",
            "learning_goals": "Transition from Backend to AI/ML Engineer and deploy LLM applications.",
            "current_skills_summary": "Python, FastAPI, SQL, Docker",
            "technical_skills_summary": "Python 3.11, PostgreSQL, PyTorch, Docker, Git"
        },
        "priya.patel@example.com": {
            "employee_code": "EMP-1002",
            "career_interests": "Data Science, Predictive Modeling, Business Analytics",
            "learning_goals": "Become an independent Data Scientist building production ML models.",
            "current_skills_summary": "SQL, Data Visualization, Python",
            "technical_skills_summary": "Python, Pandas, Scikit-Learn, Tableau, SQL"
        },
        "rohan.verma@example.com": {
            "employee_code": "EMP-1003",
            "career_interests": "Cloud Architecture, Kubernetes, Multi-Cloud Strategy",
            "learning_goals": "Earn AWS Solutions Architect and lead enterprise cloud migration.",
            "current_skills_summary": "AWS, Docker, CI/CD, Python",
            "technical_skills_summary": "AWS, Terraform, Docker, Kubernetes, Linux"
        },
        "ananya.iyer@example.com": {
            "employee_code": "EMP-1004",
            "career_interests": "Full Stack Architecture, Modern Frontend, Scalable Web Systems",
            "learning_goals": "Master React ecosystem and advance to Senior Full Stack Developer.",
            "current_skills_summary": "Python, FastAPI, SQL, System Design",
            "technical_skills_summary": "Python, React, TypeScript, PostgreSQL, REST"
        },
        "vikram.malhotra@example.com": {
            "employee_code": "EMP-1005",
            "career_interests": "Cybersecurity, SOC Analysis, Penetration Testing",
            "learning_goals": "Transition from IT support into a dedicated Cybersecurity Analyst role.",
            "current_skills_summary": "Cybersecurity Fundamentals, Network Security",
            "technical_skills_summary": "Wireshark, Nmap, Linux, OWASP, Python"
        },
        "sneha.kulkarni@example.com": {
            "employee_code": "EMP-1006",
            "career_interests": "Technical Product Management, Product Strategy, Data-driven UX",
            "learning_goals": "Drive technical roadmaps and product analytics for SaaS products.",
            "current_skills_summary": "Agile, Scrum, Product Analytics, SQL",
            "technical_skills_summary": "Jira, Amplitude, Mixpanel, SQL, Agile/Scrum"
        },
        "arjun.nair@example.com": {
            "employee_code": "EMP-1007",
            "career_interests": "Site Reliability Engineering, Observability, Chaos Engineering",
            "learning_goals": "Implement 99.99% SLO infrastructure as a senior SRE.",
            "current_skills_summary": "Docker, Kubernetes, CI/CD, SRE",
            "technical_skills_summary": "Prometheus, Grafana, Kubernetes, ArgoCD, Python"
        },
        "meera.sen@example.com": {
            "employee_code": "EMP-1008",
            "career_interests": "Advanced Data Analytics, Dashboard Storytelling, Executive BI",
            "learning_goals": "Master Python analytics and automated data pipelines.",
            "current_skills_summary": "SQL, Data Visualization, Python",
            "technical_skills_summary": "Power BI, SQL, Python, Excel, Metabase"
        },
        "kavita.rao@example.com": {
            "employee_code": "EMP-1009",
            "career_interests": "Applied Machine Learning, Computer Vision, AI Engineering",
            "learning_goals": "Integrate computer vision and neural models into web applications.",
            "current_skills_summary": "Python, React, Machine Learning",
            "technical_skills_summary": "Python, React, PyTorch, FastAPI, OpenCV"
        },
        "devendra.das@example.com": {
            "employee_code": "EMP-1010",
            "career_interests": "Cloud Infrastructure, Infrastructure as Code, DevOps",
            "learning_goals": "Achieve Cloud & DevOps Architect role with multi-cloud certifications.",
            "current_skills_summary": "AWS, Docker, Linux",
            "technical_skills_summary": "AWS, Docker, Bash, Terraform, GitHub Actions"
        }
    }

    for email, profile in seed_profiles.items():
        emp_id = emp_map.get(email)
        if emp_id:
            cursor.execute("""
                UPDATE employees
                SET employee_code = ?, career_interests = ?, learning_goals = ?,
                    current_skills_summary = ?, technical_skills_summary = ?
                WHERE id = ?
            """, (
                profile["employee_code"],
                profile["career_interests"],
                profile["learning_goals"],
                profile["current_skills_summary"],
                profile["technical_skills_summary"],
                emp_id
            ))

    conn.commit()


# --- Database Query Helpers ---

def get_all_employees() -> pd.DataFrame:
    """Returns a pandas DataFrame of all registered employees."""
    with get_db_connection() as conn:
        return pd.read_sql_query("SELECT * FROM employees ORDER BY id ASC", conn)


PROFILE_COLUMNS = {
    "employee_code": "TEXT",
    "career_interests": "TEXT",
    "learning_goals": "TEXT",
    "current_skills_summary": "TEXT",
    "technical_skills_summary": "TEXT",
    "last_quiz_score": "REAL",
    "last_quiz_summary": "TEXT",
}


def _ensure_employee_profile_columns(cursor: sqlite3.Cursor) -> None:
    """Adds profile fields used by onboarding without changing existing columns."""
    cursor.execute("PRAGMA table_info(employees)")
    existing = {row[1] for row in cursor.fetchall()}
    for name, ddl in PROFILE_COLUMNS.items():
        if name not in existing:
            cursor.execute(f"ALTER TABLE employees ADD COLUMN {name} {ddl}")

    # Backfill employee_code if missing
    cursor.execute("SELECT id FROM employees WHERE employee_code IS NULL OR employee_code = ''")
    for row in cursor.fetchall():
        cursor.execute("UPDATE employees SET employee_code = ? WHERE id = ?", (f"EMP-{row[0]:04d}", row[0]))


def _ensure_preferences_table(cursor: sqlite3.Cursor) -> None:
    """Stores the active employee so a refresh returns to the saved profile."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)


def get_preference(key: str) -> Optional[str]:
    """Reads one persisted preference value."""
    with get_db_connection() as conn:
        _ensure_preferences_table(conn.cursor())
        row = conn.execute("SELECT value FROM app_preferences WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def set_preference(key: str, value: str) -> None:
    """Creates or updates one persisted preference value."""
    with get_db_connection() as conn:
        _ensure_preferences_table(conn.cursor())
        conn.execute("""
            INSERT INTO app_preferences (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, value))
        conn.commit()


def clear_preference(key: str) -> None:
    """Removes one persisted preference value."""
    with get_db_connection() as conn:
        _ensure_preferences_table(conn.cursor())
        conn.execute("DELETE FROM app_preferences WHERE key = ?", (key,))
        conn.commit()


def is_employee_code_taken(employee_code: str, exclude_id: Optional[int] = None) -> bool:
    """Returns True when another employee already uses this employee ID."""
    code = (employee_code or "").strip()
    if not code:
        return False
    with get_db_connection() as conn:
        if exclude_id:
            row = conn.execute(
                "SELECT id FROM employees WHERE LOWER(employee_code) = LOWER(?) AND id != ?",
                (code, exclude_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id FROM employees WHERE LOWER(employee_code) = LOWER(?)",
                (code,),
            ).fetchone()
        return row is not None


def save_employee_profile_details(employee_id: int, **fields: Any) -> None:
    """Persists onboarding details that sit alongside the core employee record."""
    assignments = []
    values: List[Any] = []
    for key, value in fields.items():
        if key in PROFILE_COLUMNS:
            assignments.append(f"{key} = ?")
            values.append(value)
    if not assignments:
        return
    values.append(employee_id)
    with get_db_connection() as conn:
        _ensure_employee_profile_columns(conn.cursor())
        conn.execute(
            f"UPDATE employees SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        conn.commit()


def get_employee_by_id(employee_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves single employee record as a dictionary."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_skills() -> pd.DataFrame:
    """Returns all available skills."""
    with get_db_connection() as conn:
        return pd.read_sql_query("SELECT * FROM skills ORDER BY category, name", conn)


def get_skills_by_category() -> Dict[str, List[Dict[str, Any]]]:
    """Returns dictionary mapping category name to list of skills."""
    skills_df = get_all_skills()
    result = {}
    for cat, group in skills_df.groupby("category"):
        result[cat] = group.to_dict(orient="records")
    return result


def get_employee_skills(employee_id: int) -> pd.DataFrame:
    """Returns skills assessed for a specific employee with skill details."""
    query = """
        SELECT 
            s.id AS skill_id,
            s.name AS skill_name,
            s.category,
            COALESCE(es.proficiency_level, 0) AS proficiency_level,
            es.last_assessed
        FROM skills s
        LEFT JOIN employee_skills es 
            ON s.id = es.skill_id AND es.employee_id = ?
        ORDER BY s.category, s.name
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn, params=(employee_id,))


def get_role_requirements(role_name: str) -> pd.DataFrame:
    """Returns required skills and benchmark levels for a specific role."""
    query = """
        SELECT 
            rr.role_name,
            s.id AS skill_id,
            s.name AS skill_name,
            s.category,
            rr.required_level,
            rr.is_core
        FROM role_requirements rr
        JOIN skills s ON rr.skill_id = s.id
        WHERE rr.role_name = ?
        ORDER BY rr.is_core DESC, rr.required_level DESC
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn, params=(role_name,))


def get_all_courses() -> pd.DataFrame:
    """Returns all courses with skill details."""
    query = """
        SELECT 
            c.*,
            s.name AS skill_name,
            s.category AS skill_category
        FROM courses c
        JOIN skills s ON c.skill_id = s.id
        ORDER BY c.rating DESC
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn)


def get_employee_enrollments(employee_id: int) -> pd.DataFrame:
    """Returns all course enrollments and progress for an employee."""
    query = """
        SELECT 
            e.id AS enrollment_id,
            e.employee_id,
            e.course_id,
            e.status,
            e.progress_pct,
            e.enrolled_date,
            e.completed_date,
            c.title,
            c.provider,
            c.platform_url,
            c.level,
            c.duration_hours,
            c.rating,
            s.name AS skill_name,
            s.id AS skill_id
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        JOIN skills s ON c.skill_id = s.id
        WHERE e.employee_id = ?
        ORDER BY e.status ASC, e.enrolled_date DESC
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn, params=(employee_id,))
