"""
Labeled benchmark corpus dataset for plagiarism calibration and regression testing.
"""

from typing import List, Dict, Any

BENCHMARK_CORPUS: List[Dict[str, Any]] = [
    # 1. EXACT COPY
    {
        "id": "bench_01_exact_copy",
        "category": "EXACT_COPY",
        "query_text": "Intravitreal ranibizumab was administered monthly in patients with diabetic macular edema to evaluate visual acuity outcomes.",
        "source_text": "Intravitreal ranibizumab was administered monthly in patients with diabetic macular edema to evaluate visual acuity outcomes.",
        "source_metadata": {"title": "Ranibizumab Trial", "pmid": "10001", "authors": ["Brown DM"]},
        "is_quoted": False,
        "is_cited": False,
        "is_reference": False,
        "expected_class": "EXACT_COPY",
        "is_suspicious": True,
    },
    # 2. NEAR EXACT COPY (word substitutions)
    {
        "id": "bench_02_near_exact",
        "category": "NEAR_EXACT_COPY",
        "query_text": "Intravitreal ranibizumab was injected every month in patients with diabetic macular edema to assess visual sharpness outcomes.",
        "source_text": "Intravitreal ranibizumab was administered monthly in patients with diabetic macular edema to evaluate visual acuity outcomes.",
        "source_metadata": {"title": "Ranibizumab Trial", "pmid": "10001", "authors": ["Brown DM"]},
        "is_quoted": False,
        "is_cited": False,
        "is_reference": False,
        "expected_class": "NEAR_EXACT_COPY",
        "is_suspicious": True,
    },
    # 3. LIKELY PARAPHRASE (structural rephrasing with high semantic overlap)
    {
        "id": "bench_03_likely_paraphrase",
        "category": "LIKELY_PARAPHRASE",
        "query_text": "Patients suffering from diabetic retinal swelling received regular anti-VEGF injections, which substantially boosted their sight measurements over the one year investigation.",
        "source_text": "Monthly anti-VEGF therapy delivered significant gains in visual acuity for individuals diagnosed with center-involved diabetic macular edema during the twelve month study.",
        "source_metadata": {"title": "Anti-VEGF in Retinopathy", "pmid": "10002", "authors": ["Kaiser PK"]},
        "is_quoted": False,
        "is_cited": False,
        "is_reference": False,
        "expected_class": "LIKELY_PARAPHRASE",
        "is_suspicious": True,
    },
    # 4. PROPERLY QUOTED
    {
        "id": "bench_04_properly_quoted",
        "category": "PROPERLY_QUOTED",
        "query_text": "As stated by prior guidelines, \"intravitreal ranibizumab was administered monthly in patients with diabetic macular edema to evaluate visual acuity outcomes.\"",
        "source_text": "Intravitreal ranibizumab was administered monthly in patients with diabetic macular edema to evaluate visual acuity outcomes.",
        "source_metadata": {"title": "Ranibizumab Trial", "pmid": "10001", "authors": ["Brown DM"]},
        "is_quoted": True,
        "is_cited": False,
        "is_reference": False,
        "expected_class": "PROPERLY_QUOTED",
        "is_suspicious": False,
    },
    # 5. CITED OVERLAP
    {
        "id": "bench_05_cited_overlap",
        "category": "CITED_OVERLAP",
        "query_text": "Brown et al. reported that intravitreal ranibizumab was administered monthly in patients with diabetic macular edema to evaluate visual acuity outcomes [1].",
        "source_text": "Intravitreal ranibizumab was administered monthly in patients with diabetic macular edema to evaluate visual acuity outcomes.",
        "source_metadata": {"title": "Ranibizumab Trial", "pmid": "10001", "authors": ["Brown DM"]},
        "is_quoted": False,
        "is_cited": True,
        "is_reference": False,
        "expected_class": "CITED_OVERLAP",
        "is_suspicious": False,
    },
    # 6. COMMON SCIENTIFIC PHRASE / METHODS BOILERPLATE
    {
        "id": "bench_06_common_phrase",
        "category": "COMMON_PHRASE",
        "query_text": "All experiments were performed in triplicate and data are presented as mean standard deviation.",
        "source_text": "All experiments were performed in triplicate and data are presented as mean standard deviation.",
        "source_metadata": {"title": "Cell Biology Protocol", "pmid": "10003", "authors": ["Miller T"]},
        "is_quoted": False,
        "is_cited": False,
        "is_reference": False,
        "expected_class": "COMMON_PHRASE",
        "is_suspicious": False,
    },
    # 7. METHODS ETHICS BOILERPLATE
    {
        "id": "bench_07_ethics_boilerplate",
        "category": "COMMON_PHRASE",
        "query_text": "The study protocol was approved by the institutional review board and written informed consent was obtained from all participants.",
        "source_text": "The study protocol was approved by the institutional review board and written informed consent was obtained from all participants.",
        "source_metadata": {"title": "Clinical Trial Ethics", "pmid": "10004", "authors": ["Ethics Board"]},
        "is_quoted": False,
        "is_cited": False,
        "is_reference": False,
        "expected_class": "COMMON_PHRASE",
        "is_suspicious": False,
    },
    # 8. REFERENCE ONLY
    {
        "id": "bench_08_reference_only",
        "category": "REFERENCE_ONLY",
        "query_text": "Brown DM, Kaiser PK, Michels M. Ranibizumab versus verteporfin for neovascular age-related macular degeneration. N Engl J Med. 2006;355(14):1432-1444.",
        "source_text": "Brown DM, Kaiser PK, Michels M. Ranibizumab versus verteporfin for neovascular age-related macular degeneration. N Engl J Med. 2006;355(14):1432-1444.",
        "source_metadata": {"title": "Ranibizumab Trial", "pmid": "10001", "authors": ["Brown DM"]},
        "is_quoted": False,
        "is_cited": False,
        "is_reference": True,
        "expected_class": "REFERENCE_ONLY",
        "is_suspicious": False,
    },
    # 9. UNRELATED DOMAIN PASSAGES
    {
        "id": "bench_09_unrelated",
        "category": "UNRELATED",
        "query_text": "Hydroelectric power plants harness the kinetic energy of flowing water to spin electrical turbines efficiently.",
        "source_text": "Intravitreal ranibizumab was administered monthly in patients with diabetic macular edema to evaluate visual acuity outcomes.",
        "source_metadata": {"title": "Ranibizumab Trial", "pmid": "10001", "authors": ["Brown DM"]},
        "is_quoted": False,
        "is_cited": False,
        "is_reference": False,
        "expected_class": "UNRELATED",
        "is_suspicious": False,
    },
    # 10. POSSIBLE PARAPHRASE (semantic similarity without lexical overlap)
    {
        "id": "bench_10_possible_paraphrase",
        "category": "POSSIBLE_PARAPHRASE",
        "query_text": "Therapeutic protocols focusing on retinal vascular stabilization demonstrated clinically meaningful improvements in patient eyesight.",
        "source_text": "Monthly anti-VEGF therapy delivered significant gains in visual acuity for individuals diagnosed with center-involved diabetic macular edema.",
        "source_metadata": {"title": "Anti-VEGF in Retinopathy", "pmid": "10002", "authors": ["Kaiser PK"]},
        "is_quoted": False,
        "is_cited": False,
        "is_reference": False,
        "expected_class": "POSSIBLE_PARAPHRASE",
        "is_suspicious": False,
    },
]
