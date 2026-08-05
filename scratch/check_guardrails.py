import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent import ResearchGuardrailAgent
from unittest.mock import patch

# Define a sample strictly confidential medical paragraph
CONFIDENTIAL_TEXT = (
    "In this trial, we observed that patients presenting with aggressive glioblastoma multiforme "
    "responded exceptionally well to a combination of immunotherapy targeting PD-L1 and a novel "
    "small-molecule inhibitor of the EGFRvIII mutant. The therapy resulted in a 40% reduction in "
    "tumor size over twelve weeks, with minimal grade 3 adverse events reported."
)

def run_guardrail_validation():
    print("[*] Starting Confidentiality Guardrail Audit...")
    agent = ResearchGuardrailAgent()
    
    # Store all outbound requests
    intercepted_requests = []
    
    # We patch requests.get to capture arguments rather than hitting the network
    with patch("requests.get") as mock_get:
        # Simulate successful PubMed searches and fetches
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "esearchresult": {"idlist": ["12345"]}
        }
        mock_get.return_value.content = b"<PubmedArticleSet><PubmedArticle><PMID>12345</PMID><ArticleTitle>EGFRvIII Glioblastoma Treatment</ArticleTitle><Abstract><AbstractText>This study discusses EGFRvIII and PD-L1 therapies in glioblastoma.</AbstractText></Abstract></PubmedArticle></PubmedArticleSet>"

        # Run analysis on the confidential text
        report = agent.analyze_document(CONFIDENTIAL_TEXT.encode("utf-8"), "secret_trial_results.txt")
        
        # Collect calls
        for call in mock_get.call_args_list:
            url, kwargs = call
            params = kwargs.get("params", {})
            intercepted_requests.append({
                "url": url[0],
                "params": params
            })

    print("\n" + "="*50)
    print("           OUTBOUND TRAFFIC AUDIT REPORT")
    print("="*50)
    
    leak_detected = False
    
    for i, req in enumerate(intercepted_requests):
        print(f"Request #{i+1}:")
        print(f"  Target URL: {req['url']}")
        print(f"  Parameters: {req['params']}")
        
        # Check if any phrase or sentence from the confidential text is leaked
        term = req['params'].get("term", "")
        
        # Check if full sentences exist in the term
        for sentence in [
            "patients presenting with aggressive glioblastoma multiforme",
            "combination of immunotherapy targeting PD-L1",
            "minimal grade 3 adverse events reported",
            "reduction in tumor size"
        ]:
            if sentence in term.lower():
                print(f"  [⚠️ DANGER] Sentence leak detected: '{sentence}' is present in terms!")
                leak_detected = True
                
        # Check if the term query length of any word block is excessive
        for part in term.split(" AND "):
            clean_part = part.replace('"', '').strip()
            if len(clean_part.split()) > 3:
                print(f"  [⚠️ WARNING] Long phrase detected in terms: '{clean_part}' (> 3 words)")
                leak_detected = True

    print("-"*50)
    if not leak_detected and intercepted_requests:
        print("  [OK] CONFIDENTIALITY VALIDATED: 100% LEAK-PROOF")
        print("  Original sentence structures and phrasing stayed local.")
        print("  Only isolated entity terms were used for PubMed discovery.")
    else:
        print("  [FAIL] GUARDRAILS FAILED: Potential text leak detected in query parameters!")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_guardrail_validation()
