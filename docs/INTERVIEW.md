# Explain the project clearly

## A concise introduction

OpsPilot is a Kubernetes incident investigation assistant. It combines logs and events with retrieved operational runbooks, then produces structured hypotheses, evidence quotations, source references, and read-only checks. It has an offline demo and a live RAG path using OpenAI embeddings, Qdrant, and lexical retrieval.

## Decisions to understand

1. **Why RAG?** Operational guidance can be inspected, updated, and cited without training a model. Retrieval does not ensure reasoning correctness.
2. **Why hybrid retrieval?** Exact signals such as `OOMKilled` benefit from lexical matching, while semantic retrieval can help with paraphrased symptoms. Reciprocal rank fusion combines ranks without pretending BM25 and cosine scores share a scale.
3. **Why structured responses?** A defined schema makes output parsing and application validation explicit. JSON validity is not factual validity.
4. **Why validate evidence?** A model can invent citations or quotes. The backend checks source IDs, exact quotes, abstention consistency, and command vocabulary before displaying the answer.
5. **Why abstain?** `CrashLoopBackOff` describes backoff behavior. It does not identify the underlying failure. Asking for previous logs is more useful than inventing a cause.
6. **Why no autonomous fixes?** Investigation and remediation are separate responsibilities. The service has no cluster credentials and cannot execute its displayed commands.
7. **Why demo mode?** It makes the interface and operational workflow reproducible without account access or API spend. Its results are explicitly distinguished from LLM evaluation.
8. **What can improve?** Independent real incidents, causal support grading, retrieval ablations, reranking, ingestion coordination, provider circuit breaking, and trace correlation.

## Demonstration

- Show the offline memory-limit incident: evidence, hypothesis, cited passage, suggested check, and metrics.
- Show generic CrashLoopBackOff: the assistant requests more information.
- Explain which tests exercise real Qdrant and which mock OpenAI HTTP responses.
- Once you run live mode, compare its output on the same cases and manually assess citation support.
- Once you run the Kubernetes lab, show actual pod events and the matching investigation.

## CV wording grounded in the current verification

- Developed a Kubernetes incident investigation assistant with a FastAPI interface, operational runbooks, hybrid retrieval, and structured LLM integration with citation and evidence validation.
- Added Docker/Kubernetes deployment configurations, GitHub Actions workflows, Prometheus metrics, and automated tests for retrieval, API behavior, and insufficient-evidence handling.

Say “deployed on Kubernetes” only after running and validating that deployment. Add measured live-model results only after conducting the live evaluation. Do not present demo rule matches as LLM diagnostic accuracy.
