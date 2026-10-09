import requests
import time

BASE_URL = "http://localhost:8000"

def register_company(email, password, company_name):
    print(f"\n--- Registering Company: {company_name} ---")
    url = f"{BASE_URL}/auth/register"
    payload = {
        "email": email,
        "password": password,
        "name": company_name,
        "role": "COMPANY"
    }
    response = requests.post(url, json=payload)
    if response.status_code == 201:
        print(f"Successfully registered {company_name}")
    elif response.status_code == 400 and "Email already registered" in response.text:
        print(f"Company {company_name} already registered")
    else:
        print(f"Failed to register {company_name}: {response.text}")

def login_company(email, password):
    print(f"Logging in {email}...")
    url = f"{BASE_URL}/auth/login"
    payload = {
        "email": email,
        "password": password
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Login successful")
        return response.json().get("access_token")
    else:
        print(f"Login failed: {response.text}")
        return None

def create_jd(token, jd_data):
    print(f"Creating JD: {jd_data['jd_name']}...")
    url = f"{BASE_URL}/nlp/jd"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=jd_data, headers=headers)
    if response.status_code in [200, 201]:
        print(f"Successfully created JD: {jd_data['jd_name']}")
    else:
        print(f"Failed to create JD: {response.text}")

def main():
    # --- COMPANY 1 ---
    comp1_email = "ai_company@gmail.com"
    comp1_password = "123"
    comp1_name = "AI Innovations Inc."
    
    register_company(comp1_email, comp1_password, comp1_name)
    token1 = login_company(comp1_email, comp1_password)
    
    if token1:
        jds_comp1 = [
            {
                "jd_name": "Senior Data Engineer",
                "job_description": "We need a Senior Data Engineer with 5+ years of experience to architect our real-time data platform. Required: You must have deep expertise in Apache Kafka, Apache Spark, and data warehousing with Snowflake or Databricks. Proficiency in Python, Scala, and advanced SQL is required. Experience with data lakehouse architectures using Delta Lake and orchestration with Airflow or Prefect is mandatory. Nice to have: Experience with Apache Flink, data governance tools, data lineage tracking, Great Expectations for data quality, and cost optimization of cloud data workloads on AWS or GCP is a plus. Leadership experience including mentoring and sprint planning is desirable.",
                "is_public": 1
            },
            {
                "jd_name": "Junior Data Engineer",
                "job_description": "Hiring a Junior Data Engineer with 1 year of experience to join our analytics team. Required: You must be able to build ETL pipelines using Python and SQL. Basic understanding of data modeling and data quality validation is required. Familiarity with Apache Airflow and data warehouses like BigQuery or Snowflake is mandatory. Nice to have: Experience with Git, Docker, cloud storage services like AWS S3 or GCS, dbt for data transformation, and visualization tools like Metabase or Looker is a plus. Attention to detail and good documentation habits are desirable.",
                "is_public": 1
            }
        ]
        for jd in jds_comp1:
            create_jd(token1, jd)
            time.sleep(2) # Prevent rate-limiting / DB lock

    # --- COMPANY 2 ---
    comp2_email = "software_co@example.com"
    comp2_password = "password123"
    comp2_name = "Global Software Solutions"
    
    register_company(comp2_email, comp2_password, comp2_name)
    token2 = login_company(comp2_email, comp2_password)
    
    if token2:
        jds_comp2 = [
            {
                "jd_name": "Junior DevOps Engineer",
                "job_description": "We are looking for a Junior DevOps Engineer with 1 year of experience to support our infrastructure team. Required: You must have basic knowledge of Linux system administration, Docker containers, and CI/CD pipelines using GitHub Actions or Jenkins. Writing automation scripts in Bash and Python is required. Understanding of Git workflows and networking fundamentals (DNS, TCP/IP, HTTP) is mandatory. Nice to have: Familiarity with cloud platforms like AWS (EC2, S3, IAM) or GCP, Nginx, log monitoring with ELK Stack, and basic security practices is preferred. Willingness to participate in on-call rotation is a plus.",
                "is_public": 1
            },
            {
                "jd_name": "Junior Backend Developer",
                "job_description": "Looking for a Junior Backend Developer with 1 year of experience. You must have a solid understanding of Python and basic web frameworks like Flask or Django. SQL knowledge and experience with relational databases such as MySQL or PostgreSQL is required. Basic understanding of REST APIs and HTTP protocols is mandatory. Nice to have: Familiarity with Docker, Git version control, cloud services like AWS or GCP, and basic Linux commands is preferred but not required. Good problem-solving skills and willingness to learn are beneficial.",
                "is_public": 1
            }
        ]
        for jd in jds_comp2:
            create_jd(token2, jd)
            time.sleep(2) # Prevent rate-limiting / DB lock

if __name__ == "__main__":
    main()
