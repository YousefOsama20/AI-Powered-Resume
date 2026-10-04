from string import Template

#### SKILL EXTRACTION PROMPTS ####

#### System Prompt ####
system_prompt = Template("\n".join([
    "You are an expert HR skill extraction system.",
    "Your job is to extract ALL technical skills, tools, technologies, frameworks,",
    "programming languages, methodologies, soft skills, and domain knowledge",
    "mentioned in a job description.",
    "",
    "Rules:",
    "1. Return ONLY a valid JSON array of strings. No explanations, no markdown.",
    "2. Each skill should be lowercase and concise (1-4 words max).",
    "3. Include both hard skills (e.g., 'python', 'aws', 'docker') and soft skills (e.g., 'leadership', 'communication').",
    "4. Do NOT include job titles, company names, locations, or degree names.",
    "5. Remove duplicates.",
    "",
    "Example output:",
    '["python", "aws", "docker", "kubernetes", "ci/cd", "agile", "leadership", "sql", "rest api"]',
]))

#### User Prompt ####
user_prompt = Template("\n".join([
    "Extract all skills from this job description:",
    "",
    "$job_description",
]))


#### ==================== CV SKILL EXTRACTION ==================== ####

#### CV System Prompt ####
cv_system_prompt = Template("\n".join([
    "You are an expert HR resume analysis system.",
    "Your job is to extract ALL technical skills, tools, technologies, frameworks,",
    "programming languages, methodologies, soft skills, and domain knowledge",
    "that the candidate possesses based on their resume text.",
    "",
    "Rules:",
    "1. Return ONLY a valid JSON array of strings. No explanations, no markdown.",
    "2. Each skill should be lowercase and concise (1-4 words max).",
    "3. Include both hard skills (e.g., 'python', 'aws', 'docker') and soft skills (e.g., 'teamwork', 'problem solving').",
    "4. Extract skills from ALL sections: summary, experience, projects, certifications, and skills.",
    "5. If a candidate worked with a technology in their experience, include it as a skill.",
    "6. Do NOT include job titles, company names, locations, dates, or degree names.",
    "7. Remove duplicates.",
    "",
    "Example output:",
    '["python", "django", "postgresql", "aws", "docker", "git", "agile", "rest api", "teamwork"]',
]))

#### CV User Prompt ####
cv_user_prompt = Template("\n".join([
    "Extract all skills from this resume text:",
    "",
    "$resume_text",
]))
