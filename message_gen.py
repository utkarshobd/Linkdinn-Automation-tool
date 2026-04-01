import random
import os

TEMPLATES = [
    "Hi {name}, I came across {company} and was genuinely impressed by what you're building. I'd love to connect and learn more about your journey as a founder.",
    "Hey {name}, {company} caught my attention — the problem you're solving is really interesting. Would love to connect and exchange ideas.",
    "Hi {name}, I've been following the work at {company} and think it's doing something meaningful. Would be great to connect with you.",
    "Hello {name}, I noticed {company} in the MarsShot portfolio and was curious to learn more. Would love to add you to my network.",
]


def generate_message(founder_name: str, company_name: str) -> str:
    first_name = founder_name.split()[0] if founder_name else "there"
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return _llm_message(first_name, company_name, openai_key)
    return random.choice(TEMPLATES).format(name=first_name, company=company_name)


def _llm_message(first_name: str, company_name: str, api_key: str) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        prompt = (
            f"Write a short, friendly LinkedIn connection request (under 300 chars) "
            f"to {first_name}, founder of {company_name}. "
            f"Be genuine, non-salesy, and mention their company naturally."
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return generate_message(first_name, company_name)
