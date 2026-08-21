"""
Plagiarism Service - Core orchestrator for evidence-based plagiarism detection.
"""

import time
import uuid
from typing import List, Dict, Optional, Any, Union

from src.plagiarism.config.settings import EngineConfig, get_default_config
from src.plagiarism.documents.models import Document, Passage, SectionType
from src.plagiarism.documents.segmentation import process_document
from src.extractor import DocumentExtractor
from src.plagiarism.providers.registry import ProviderRegistry, create_default_registry
from src.plagiarism.indexing.corpus_indexer import CorpusIndexer
from src.plagiarism.indexing.vector.embedder import EmbeddingService
from src.plagiarism.indexing.vector.faiss_index import VectorIndex
from src.plagiarism.retrieval.lexical import LexicalRetriever
from src.plagiarism.retrieval.semantic import SemanticRetriever
from src.plagiarism.retrieval.exact import ExactPhraseRetriever
from src.plagiarism.retrieval.fusion import HybridRetriever, CandidateHit
from src.plagiarism.matching.features import MatchFeatureExtractor, PassageAggregator
from src.plagiarism.matching.cross_encoder import CrossEncoderReranker
from src.plagiarism.scoring.citations import CitationAnalyzer
from src.plagiarism.scoring.boilerplate import BoilerplateDetector
from src.plagiarism.scoring.classifier import EvidenceClassifier
from src.plagiarism.scoring.aggregate import ScoreAggregator
from src.plagiarism.scoring.models import PlagiarismMatch, PlagiarismReport, MatchClass, MatchEvidence
from src.plagiarism.services.ingestion_service import IngestionService
from src.plagiarism.observability.logging import PlagiarismLogger, set_correlation_id, get_correlation_id
from src.plagiarism.observability.metrics import global_metrics
from src.plagiarism.observability.tracing import PipelineTracer


class PlagiarismService:
    """
    High-level service orchestrating confidential, multi-channel scholarly plagiarism checks.
    """

    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        provider_registry: Optional[ProviderRegistry] = None,
        corpus_indexer: Optional[CorpusIndexer] = None,
        vector_index: Optional[VectorIndex] = None,
        embedder: Optional[EmbeddingService] = None,
    ):
        self.config = config or get_default_config()
        self.logger = PlagiarismLogger("PlagiarismService")
        self.provider_registry = provider_registry or create_default_registry()
        self.corpus_indexer = corpus_indexer or CorpusIndexer(config=self.config)
        self.embedder = embedder or EmbeddingService(self.config.semantic)
        self.vector_index = vector_index or VectorIndex(
            dimension=self.embedder.dimension,
            model_name=self.config.semantic.model_name,
            index_version=self.config.semantic.version,
        )

        self.ingestion_service = IngestionService(
            config=self.config,
            corpus_indexer=self.corpus_indexer,
        )

        # Retrieval components
        self.lexical_retriever = LexicalRetriever(
            lexical_index=self.corpus_indexer.lexical_index,
            top_k=self.config.lexical.top_k,
            threshold=self.config.lexical.containment_threshold,
        )
        self.semantic_retriever = SemanticRetriever(
            embedder=self.embedder,
            vector_index=self.vector_index,
            top_k=self.config.semantic.top_k,
            threshold=self.config.semantic.similarity_threshold,
        )
        self.exact_retriever = ExactPhraseRetriever(
            lexical_index=self.corpus_indexer.lexical_index,
            top_k=20,
        )
        self.hybrid_retriever = HybridRetriever(
            lexical_retriever=self.lexical_retriever,
            semantic_retriever=self.semantic_retriever,
            exact_retriever=self.exact_retriever,
            top_k=40,
        )

        # Matching, scoring & classifiers
        self.feature_extractor = MatchFeatureExtractor(
            embedder=self.embedder,
            shingle_size=self.config.lexical.shingle_size,
        )
        self.reranker = CrossEncoderReranker(self.config.reranker)
        self.boilerplate_detector = BoilerplateDetector()
        self.classifier = EvidenceClassifier(self.config.scoring)

    def check_file_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> PlagiarismReport:
        """
        Parses document bytes in-memory and executes the plagiarism check.
        """
        from src.extractor import DocumentExtractor
        extractor = DocumentExtractor()
        raw_text = extractor.extract_text_from_bytes(file_bytes, filename)
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        return self.check_text(raw_text, title=filename, document_id=doc_id, options=options)

    def check_text(
        self,
        text: str,
        title: str = "",
        document_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> PlagiarismReport:
        """
        Analyzes plain text manuscript against persistent indexed sources and online discovery.
        """
        start_time = time.time()
        check_id = get_correlation_id()
        tracer = PipelineTracer()
        opts = options or {}

        doc_id = document_id or f"doc_{uuid.uuid4().hex[:8]}"
        doc_title = title or doc_id

        self.logger.info(f"Starting plagiarism check for document '{doc_title}' ({doc_id})")

        # 1. Document parsing and passage segmentation
        with tracer.trace_stage("document_processing"):
            document = process_document(
                document_id=doc_id,
                text=text,
                title=doc_title,
                settings=self.config.segmentation,
            )

        if not document.raw_text.strip() or not document.passages:
            return ScoreAggregator.aggregate_report(
                check_id=check_id,
                document=document,
                matches=[],
                engine_version=self.config.engine_version,
                threshold_version=self.config.scoring.threshold_version,
                warnings=["Document contains no readable textual content."],
            )

        # 2. Confidential Anonymous Discovery (Guardrails)
        warnings: List[str] = []
        with tracer.trace_stage("provider_discovery"):
            from src.extractor import DocumentExtractor
            extractor = DocumentExtractor()
            sanitized_keywords = extractor.extract_anonymized_keywords(document.raw_text, max_keywords=8)
            
            # Query providers using ONLY anonymized keywords
            target_providers = opts.get("sources")
            if sanitized_keywords and (target_providers is None or len(target_providers) > 0):
                query_str = " ".join(sanitized_keywords)
                records, prov_warnings = self.provider_registry.search_all_sync(
                    query_str,
                    limit_per_provider=opts.get("limit_per_provider", 10),
                    provider_names=target_providers,
                )
                warnings.extend(prov_warnings)

                # Ingest discovered records into persistent passage index
                for rec in records:
                    provider_inst = self.provider_registry.get(rec.provider)
                    if provider_inst:
                        try:
                            source_doc = provider_inst.get_full_text(rec.source_id)
                            if source_doc is not None and asyncio.iscoroutine(source_doc):
                                try:
                                    loop = asyncio.get_event_loop()
                                    if loop.is_running():
                                        import concurrent.futures
                                        with concurrent.futures.ThreadPoolExecutor() as pool:
                                            source_doc = pool.submit(asyncio.run, provider_inst.get_full_text(rec.source_id)).result()
                                    else:
                                        source_doc = loop.run_until_complete(source_doc)
                                except RuntimeError:
                                    source_doc = asyncio.run(source_doc)
                        except Exception:
                            source_doc = None
                        if source_doc is None:
                            source_doc = SourceDocument(
                                document_id=f"{rec.provider}:{rec.source_id}",
                                provider=rec.provider,
                                provider_source_id=rec.source_id,
                                doi=rec.doi,
                                pmid=rec.pmid,
                                pmcid=rec.pmcid,
                                title=rec.title,
                                abstract=rec.abstract,
                                full_text=rec.abstract,
                                authors=rec.authors,
                                journal=rec.journal,
                                publication_year=rec.publication_year,
                                rights_id="abstract_fair_use",
                            )
                        self.ingestion_service.ingest_source_document(source_doc)

        # 3. Vector indexing of indexed corpus passages if needed
        with tracer.trace_stage("vector_indexing"):
            # Ensure any newly ingested passages have embeddings in vector index
            unvectorized_pids = [
                pid for pid in self.corpus_indexer.passage_store.keys()
                if pid not in self.vector_index.passage_ids
            ]
            if unvectorized_pids:
                passages_to_embed = [self.corpus_indexer.passage_store[pid] for pid in unvectorized_pids]
                vectors = self.embedder.encode_passages(passages_to_embed)
                doc_ids = [p.document_id for p in passages_to_embed]
                metas = [p.to_dict() for p in passages_to_embed]
                self.vector_index.insert_batch(unvectorized_pids, vectors, doc_ids, metas)

        # 4. Multi-channel hybrid retrieval
        raw_matches: List[PlagiarismMatch] = []
        with tracer.trace_stage("hybrid_retrieval_and_matching"):
            for q_passage in document.passages:
                # Skip query reference sections from querying
                if q_passage.is_reference and not opts.get("include_references", False):
                    continue

                candidate_hits = self.hybrid_retriever.retrieve(q_passage)
                
                # Optional Cross-Encoder reranking
                if self.reranker.enabled:
                    candidate_hits = self.reranker.rerank(
                        query_passage=q_passage,
                        candidate_hits=candidate_hits,
                        source_passages_map=self.corpus_indexer.passage_store,
                    )

                # 5. Detailed matching & classification for top candidates
                for hit in candidate_hits[:15]:
                    s_passage = self.corpus_indexer.get_passage(hit.source_passage_id)
                    if not s_passage:
                        continue

                    # Feature extraction
                    feats = self.feature_extractor.extract_features(q_passage, s_passage)
                    bp_score = self.boilerplate_detector.compute_boilerplate_score(feats.longest_copied_phrase)

                    # Citation evaluation
                    source_meta = self.corpus_indexer.document_registry.get(
                        s_passage.document_id, {}
                    ).get("extra_metadata", {})
                    if not source_meta:
                        source_meta = {
                            "doi": getattr(s_passage, "doi", None),
                            "authors": getattr(s_passage, "authors", []),
                            "title": s_passage.section or "",
                        }
                    cit_ctx = CitationAnalyzer.evaluate_citation_context(
                        query_passage=q_passage,
                        document=document,
                        source_metadata=source_meta,
                    )

                    evidence = MatchEvidence(
                        query_passage_id=q_passage.passage_id,
                        source_passage_id=s_passage.passage_id,
                        exact_overlap=feats.exact_overlap,
                        shingle_containment=feats.shingle_containment,
                        jaccard_similarity=feats.jaccard_similarity,
                        edit_similarity=feats.edit_similarity,
                        semantic_similarity=feats.semantic_similarity,
                        cross_encoder_score=hit.cross_encoder_score,
                        matched_token_count=feats.matched_token_count,
                        query_token_count=feats.query_token_count,
                        source_token_count=feats.source_token_count,
                        longest_copied_tokens=feats.longest_copied_tokens,
                        longest_copied_phrase=feats.longest_copied_phrase,
                        citation_present=cit_ctx.is_cited,
                        quoted_text=cit_ctx.is_quoted,
                        boilerplate_score=bp_score,
                        matching_phrases=feats.matching_phrases,
                    )

                    match_class, confidence = self.classifier.classify_match(
                        evidence=evidence,
                        is_reference_section=q_passage.is_reference,
                    )

                    if match_class not in [MatchClass.UNRELATED, MatchClass.LOW_SIGNIFICANCE]:
                        match_id = f"match_{uuid.uuid4().hex[:8]}"
                        raw_matches.append(
                            PlagiarismMatch(
                                match_id=match_id,
                                classification=match_class,
                                confidence=confidence,
                                query_span={
                                    "start": q_passage.start_offset,
                                    "end": q_passage.end_offset,
                                },
                                source_document_id=s_passage.document_id,
                                source=source_meta,
                                evidence=evidence,
                            )
                        )

        # 6. Aggregation and Report Construction
        with tracer.trace_stage("report_aggregation"):
            report = ScoreAggregator.aggregate_report(
                check_id=check_id,
                document=document,
                matches=raw_matches,
                engine_version=self.config.engine_version,
                threshold_version=self.config.scoring.threshold_version,
                warnings=warnings,
            )

        elapsed = time.time() - start_time
        self.logger.info(
            f"Plagiarism check complete for '{doc_title}' in {elapsed:.2f}s | "
            f"Suspicious: {report.suspicious_coverage:.1f}% | Risk: {report.risk_level}"
        )

        # Record metrics
        class_counts = {}
        for m in report.matches:
            c_name = m.classification.value
            class_counts[c_name] = class_counts.get(c_name, 0) + 1
        global_metrics.record_check(elapsed, class_counts)

        return report
