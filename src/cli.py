import argparse
import sys
import json
import os
from src.agent import ResearchGuardrailAgent

def main():
    parser = argparse.ArgumentParser(
        description="Confidential Research Plagiarism & Semantic Similarity Checker (Local-First CLI)"
    )
    parser.add_argument("file", help="Path to the document to verify (PDF, DOCX, or TXT)")
    parser.add_argument(
        "-o", "--output", 
        help="Path to write JSON analysis report"
    )
    parser.add_argument(
        "--json", 
        action="store_true", 
        help="Print raw JSON results directly to stdout instead of formatted text"
    )
    parser.add_argument(
        "--v2",
        action="store_true",
        help="Use v2 multi-channel passage segmentation and calibrated evidence engine"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    # Read file bytes
    try:
        with open(args.file, "rb") as f:
            file_bytes = f.read()
    except Exception as e:
        print(f"Error reading file '{args.file}': {e}", file=sys.stderr)
        sys.exit(1)
        
    print(f"[*] Processing document '{os.path.basename(args.file)}' locally...", file=sys.stderr)
    
    # Initialize the local AI agent
    try:
        agent = ResearchGuardrailAgent()
        if args.v2:
            report_v2 = agent.analyze_document_v2(file_bytes, os.path.basename(args.file))
            if args.json:
                print(json.dumps(report_v2.to_dict(), indent=2))
            else:
                from src.plagiarism.reporting.builder import ReportBuilder
                print(ReportBuilder.build_text_summary(report_v2))
            
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(report_v2.to_dict(), f, indent=2)
                print(f"[*] Report saved successfully to '{args.output}'", file=sys.stderr)
            return

        report = agent.analyze_document(file_bytes, os.path.basename(args.file))
    except Exception as e:
        print(f"Error running analysis: {e}", file=sys.stderr)
        sys.exit(1)

    if report.get("status") == "error":
        print(f"Analysis failed: {report.get('error')}", file=sys.stderr)
        sys.exit(1)

    # Output selection
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        # Formatted console output
        meta = report["metadata"]
        guardrails = report["guardrails"]
        results = report["results"]
        
        print("\n" + "="*60)
        print("  SECURE PLAGIARISM & SIMILARITY AUDIT REPORT")
        print("="*60)
        print(f"File Name:            {meta['filename']}")
        print(f"Word Count:           {meta['word_count']}")
        print(f"Sentences Analyzed:   {meta['sentences_analyzed']}")
        print(f"Execution Time:       {meta['execution_time_seconds']} seconds")
        print("-"*60)
        print("[SECURE] DATA CONFIDENTIALITY AUDIT LOG")
        print(f"Status:               {guardrails['confidentiality_status']}")
        print(f"Anonymized Search Terms Sent Out:")
        if guardrails["anonymized_search_keywords"]:
            print("  " + ", ".join([f"'{kw}'" for kw in guardrails["anonymized_search_keywords"]]))
        else:
            print("  None (Too few words to extract keywords safely)")
        print(f"Matching PubMed PMIDs: {', '.join(guardrails['external_pmids_queried']) or 'None'}")
        print("-"*60)
        print("[RISK] PLAGIARISM & SIMILARITY RISK ASSESSMENT")
        
        risk_color = "\033[92m" # Green
        if results["risk_level"] == "HIGH":
            risk_color = "\033[91m" # Red
        elif results["risk_level"] == "MODERATE":
            risk_color = "\033[93m" # Yellow
            
        print(f"Overall Risk Level:   {risk_color}{results['risk_level']} RISK\033[0m")
        print(f"Max Verbatim Match:   {int(results['max_verbatim_score'] * 100)}%")
        print(f"Max Semantic Match:   {int(results['max_semantic_score'] * 100)}%")
        print("-"*60)
        
        # Verbose details
        if results["verbatim_plagiarism_flags"]:
            print(f"\n[!] Flagged {len(results['verbatim_plagiarism_flags'])} Verbatim Matches:")
            for item in results["verbatim_plagiarism_flags"]:
                print(f"  - PMID {item['pmid']} ({item['title'][:50]}...): Jaccard Score {int(item['jaccard_score']*100)}%")
                for phrase in item["matching_phrases"]:
                    print(f"    Verbatim overlap: \"{phrase}\"")
                    
        if results["semantic_similarity_flags"]:
            print(f"\n[!] Flagged {len(results['semantic_similarity_flags'])} Semantic Overlaps:")
            for item in results["semantic_similarity_flags"]:
                print(f"  - PMID {item['pmid']} ({item['title'][:50]}...): Similarity {int(item['score']*100)}%")
                print(f"    Source:   \"{item['source_sentence']}\"")
                print(f"    Matching: \"{item['matching_sentence']}\"")
        
        if not results["verbatim_plagiarism_flags"] and not results["semantic_similarity_flags"]:
            print("\n[OK] Clean! No matching life sciences publications or plagiarism detected.")
            
        print("="*60 + "\n")

    # Save output if path is given
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            print(f"[*] Report saved successfully to '{args.output}'", file=sys.stderr)
        except Exception as e:
            print(f"Error saving report to '{args.output}': {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
