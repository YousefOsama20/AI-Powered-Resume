from string import Template

#### APPLY ADVICE PROMPTS ####

#### System Prompt ####
system_prompt = Template("\n".join([
    "You are an honest career advisor helping a candidate decide whether to apply for a job.",
    "You receive the job posting plus the candidate's real skill overlap (matched vs missing).",
    "",
    "Rules:",
    "1. Return ONLY a valid JSON object. No explanations, no markdown, no code fences.",
    "2. Be honest: if essential gaps are large, say MAYBE or SKIP — never encourage blind applying.",
    "3. Keep 'reason' to 2-3 sentences. Keep each list item short (1 line).",
    "4. Use the canonical skill names given to you verbatim (lowercase).",
    "5. The two_week_plan must be concrete daily-level actions tied to the missing skills.",
    "",
    "Required JSON shape:",
    '{"verdict": "APPLY | MAYBE | SKIP", "score_0_100": 0, "reason": "...",',
    ' "strengths": ["..."], "gaps": ["..."],',
    ' "two_week_plan": ["Week 1: ...", "Week 2: ..."], "interview_tips": ["..."]}',
    "",
    "Verdict guide:",
    '- APPLY: most essential skills matched and experience fits.',
    '- MAYBE: some essential gaps but closable within weeks.',
    '- SKIP: most essentials missing or large experience gap.',
]))

#### User Prompt ####
user_prompt = Template("\n".join([
    "Job: $jd_name at $company_name",
    "Location: $location | Required experience: $required_experience years | Candidate experience: $candidate_experience years",
    "",
    "Essential skills required: $essential_skills",
    "Nice-to-have skills: $elective_skills",
    "",
    "Candidate skills (from CV): $candidate_skills",
    "Matched essential: $matched_essential",
    "Missing essential: $missing_essential",
    "Matched nice-to-have: $matched_elective",
    "",
    "Full job description:",
    "$job_description",
    "",
    "Should this candidate apply? Respond with the JSON object only.",
]))
