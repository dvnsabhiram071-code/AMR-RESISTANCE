"""
Groq-Powered AI Copilot & Explainability Engine for AMR Sentinel.
Enforces strict clinical guardrails, evidence grounding, and offline fallback.
"""
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

FALLBACK_MODELS = [
    os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]


def generate_offline_explanation(evidence: Dict[str, Any]) -> str:
    """
    Deterministic rule-based explanation generator used when Groq API key is absent,
    rate-limited, or network fails. Ensures 100% reliable system operation.
    """
    org = evidence.get("organism", "Selected Organism")
    abx = evidence.get("antibiotic", "Selected Antimicrobial")
    dept = evidence.get("department", "Facility")
    curr_rate = evidence.get("current_rate")
    base_rate = evidence.get("baseline_rate")
    pct_change = evidence.get("pct_point_change")
    curr_n = evidence.get("current_tested", 0)
    curr_r = evidence.get("current_resistant", 0)
    base_n = evidence.get("baseline_tested", 0)
    base_r = evidence.get("baseline_resistant", 0)
    curr_p = evidence.get("current_period", "Current window")
    base_p = evidence.get("baseline_period", "Baseline window")
    trigger = evidence.get("trigger_reason", "Surveillance threshold exceeded.")
    caveats = evidence.get("caveats")

    rate_str = f"{curr_rate:.1f}%" if curr_rate is not None else "N/A"
    base_rate_str = f"{base_rate:.1f}%" if base_rate is not None else "N/A"
    change_str = f"{pct_change:+.1f}%" if pct_change is not None else "N/A"

    explanation = f"""### 1. What Changed
A notable shift in antimicrobial resistance was detected for **{org}** against **{abx}** in the **{dept}** department.
The resistance proportion shifted from {base_rate_str} in the baseline period to **{rate_str}** in the current surveillance window ({change_str} percentage points).

### 2. Evidence & Validated Metrics
- **Current Surveillance Window ({curr_p}):** {curr_r} resistant isolates out of {curr_n} eligible tests ({rate_str}).
- **Comparison Baseline Window ({base_p}):** {base_r} resistant isolates out of {base_n} eligible tests ({base_rate_str}).
- **Absolute Shift:** {change_str} percentage points.

### 3. Why Flagged (Rule Evaluation)
- **Trigger Rule:** {trigger}
- **Deterministic Check:** System evaluated organism-antimicrobial resistance rates against configured hospital alert thresholds.

### 4. Data-Quality & Sample-Size Caveats
{f"- **Caution:** {caveats}" if caveats else "- **Sample Reliability:** Both current and baseline sample sizes meet the minimum statistical reporting threshold."}
- *Notice:* Synthetic surveillance data used. Ensure repeat isolates from the same patient within 30 days are deduped per laboratory guidelines.

### 5. Suggested Clinical & Epidemiological Verification Steps
1. **Verify Repeat Sampling:** Check whether multiple positive isolates originate from a single patient or prolonged stay.
2. **Review Laboratory Methods:** Confirm antimicrobial disk diffusion / MIC testing lot consistency and testing standards.
3. **Clinical Governance Review:** Convene the Infection Prevention & Antimicrobial Stewardship Committee to review environmental swab data and ward occupancy.
*Important:* This is a surveillance intelligence aid. It does not replace clinical microbiology judgment and does not provide individual patient prescriptions.
"""
    return explanation.strip()


def query_amr_copilot(
    evidence: Dict[str, Any],
    user_query: Optional[str] = None,
    api_key: Optional[str] = None
) -> str:
    """
    Queries Groq LLM using structured evidence only.
    Falls back gracefully to deterministic rule-based generator if anything fails.
    """
    key = api_key or os.getenv("GROQ_API_KEY")
    if not key or key.strip() in ["", "your_groq_api_key_here"]:
        return generate_offline_explanation(evidence)

    try:
        from groq import Groq
        client = Groq(api_key=key.strip())

        system_prompt = (
            "You are the AMR Sentinel Clinical AI Copilot. You provide objective, evidence-grounded "
            "explanations of antimicrobial resistance surveillance metrics to infection preventionists. "
            "CRITICAL SAFETY RULES:\n"
            "1. ONLY discuss facts present in the structured evidence provided below. Do NOT invent numbers.\n"
            "2. NEVER prescribe antibiotics or offer individual patient diagnoses or treatment plans.\n"
            "3. NEVER assert that a signal definitively proves a clinical outbreak without laboratory confirmation.\n"
            "4. Structure your response in 5 clear sections: 1. What Changed, 2. Evidence & Metrics, "
            "3. Why Flagged, 4. Data Caveats, 5. Suggested Review Steps."
        )

        user_content = f"""Structured Surveillance Evidence:
- Organism: {evidence.get('organism')}
- Antimicrobial: {evidence.get('antibiotic')}
- Department: {evidence.get('department')}
- Current Window: {evidence.get('current_period')} (Tested: {evidence.get('current_tested')}, Resistant: {evidence.get('current_resistant')}, Rate: {evidence.get('current_rate')}%)
- Baseline Window: {evidence.get('baseline_period')} (Tested: {evidence.get('baseline_tested')}, Resistant: {evidence.get('baseline_resistant')}, Rate: {evidence.get('baseline_rate')}%)
- Percentage Point Change: {evidence.get('pct_point_change')}%
- Trigger Reason: {evidence.get('trigger_reason')}
- Caveats: {evidence.get('caveats')}

User Question: {user_query or 'Why was this resistance signal flagged and what evidence supports it?'}
"""

        # Try models in fallback order
        for model_name in FALLBACK_MODELS:
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.2,
                    max_tokens=800,
                )
                content = response.choices[0].message.content
                if content and len(content.strip()) > 50:
                    return content.strip()
            except Exception:
                continue

        # If all API calls fail, fallback safely
        return generate_offline_explanation(evidence)

    except Exception:
        return generate_offline_explanation(evidence)
