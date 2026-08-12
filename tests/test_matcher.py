from scout_x5.matcher import score
from scout_x5.models import Job

PROFILE = {
    "broad_roles": ["software engineer", "firmware engineer"],
    "resume_boosts": ["c++", "linux", "firmware"],
    "early_career_terms": ["intern", "new grad"],
    "locations": ["remote", "california"],
    "seniority_penalties": ["senior", "staff"],
    "exclude": ["active clearance required"],
}


def job(title: str, description: str = "", location: str = "Remote") -> Job:
    return Job("test", title, title, "Example", location, "https://example.com/job", description)


def test_general_swe_is_eligible_without_resume_specific_keywords() -> None:
    match = score(job("Software Engineer Intern", "Build web products"), PROFILE)
    assert match.score >= 40
    assert "SWE role" in match.reasons[0]


def test_resume_terms_boost_systems_job() -> None:
    broad = score(job("Software Engineer", "Build web products", "New York"), PROFILE)
    aligned = score(job("Firmware Engineer Intern", "Develop C++ firmware on Linux"), PROFILE)
    assert aligned.score > broad.score


def test_senior_role_is_penalized() -> None:
    regular = score(job("Software Engineer", "C++ Linux"), PROFILE)
    senior = score(job("Senior Software Engineer", "C++ Linux"), PROFILE)
    assert senior.score < regular.score


def test_exclusion_wins() -> None:
    match = score(job("Software Engineer Intern", "Active clearance required"), PROFILE)
    assert match.score == 0
