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
    comp1_password = "password123"
    comp1_name = "AI Innovations Inc."
    
    register_company(comp1_email, comp1_password, comp1_name)
    token1 = login_company(comp1_email, comp1_password)
    
    if token1:
        jds_comp1 = [
            {
                "jd_name": "Senior AI Developer",
                "job_description": "We are looking for a Senior AI Developer with a minimum of 6 years of experience in software engineering, with at least 3 years focused on Machine Learning and NLP. Required: You must be proficient in Python, PyTorch, and building RAG (Retrieval-Augmented Generation) pipelines using LangChain and LlamaIndex. Deep expertise in vector databases like ChromaDB or Pinecone is required. You must have experience deploying models using HuggingFace and OpenAI APIs. Cloud platform experience (GCP or Azure) is mandatory. Nice to have: Experience with model evaluation techniques, CI/CD for ML pipelines, TensorFlow, and excellent communication skills for collaborating with product managers is a plus.",
                "is_public": 1
            },
            {
                "jd_name": "Junior AI Engineer",
                "job_description": "We are looking for a Junior AI Engineer with 1 year of experience or strong academic projects in machine learning. Required: You must be comfortable writing Python scripts and have basic understanding of machine learning concepts. Experience with Scikit-learn, Pandas, and NumPy for data preprocessing and feature engineering is required. Basic understanding of neural networks is mandatory. Nice to have: Familiarity with deep learning frameworks like TensorFlow or PyTorch, Jupyter Notebooks, Git, SQL, and basic Linux commands is preferred. Curiosity about AI research and strong problem-solving abilities are a plus.",
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
                "jd_name": "Senior Software Engineer",
                "job_description": "We are hiring a Senior Software Engineer with a minimum of 5 years of experience. Required skills: You must be proficient in Python, FastAPI, and PostgreSQL. Strong experience in building RESTful APIs, writing unit tests with pytest, and using Docker for containerization is required. You must have hands-on experience with Git, CI/CD pipelines, and Linux system administration. Nice to have: Experience with Kubernetes, Redis caching, message queues like RabbitMQ or Kafka, and monitoring tools such as Prometheus and Grafana is a plus. Familiarity with Agile/Scrum methodologies and strong communication skills are desirable.",
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
