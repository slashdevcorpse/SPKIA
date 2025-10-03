# Project Brief: **Sensor-PKI Authenticity (SPKIA)**  
_Public-Key Cryptography at the Image Sensor Level + C2PA-aware AI Media Detection + ML-enhanced Detection_

---

## 1) Objective
Develop a privacy-preserving verification platform that determines whether an image or video was:
- **Captured by a real camera** (via sensor-level cryptographic proof and/or valid C2PA credentials),  
- **Likely AI-generated** (Nano Banana, Sora, DALL·E, etc.), or  
- **Provenance unknown**.  

The system must integrate **cryptographic proofs** and **machine learning classifiers** to ensure robustness against adversarial manipulation.  

---

## 2) Scope
**In-scope**
- Verification via **C2PA manifests**.  
- Verification via **sensor-level PKI signatures**.  
- **ML/AI-based detection pipeline** for AI media classification.  
- **Privacy-first operation**: ephemeral processing only, no permanent storage.  

**Out-of-scope**
- Persistent content storage or user profiling.

---

## 3) Architecture
**Frontend (React)**  
- Simple drag-and-drop or URL input.  
- Displays authenticity result and rationale.  
- Option to show cryptographic and ML-based verification details.  

**Backend (Python/FastAPI)**  
- Orchestration of verification pipeline.  
- Calls C2PA validator, Sensor-PKI verifier, and ML classifiers.  
- Stateless; horizontally scalable.  

**Database (MongoDB)**  
- Stores **job states**, extracted metadata, and ML features temporarily.  
- TTL expiration (default: 24h).  

**Deployment (Docker)**  
- Containers: frontend, API, workers, Mongo, Nginx.  
- Portable and easily deployed to cloud or on-prem environments.  

---

## 4) Cryptographic Layer
**Sensor-PKI**  
- Cameras sign capture hashes with secure hardware keys.  
- Public key infrastructure maintained by manufacturers.  
- Signatures embedded as **COSE/CBOR** envelopes or as C2PA assertions.  

**C2PA**  
- Validate provenance claims, trust chains, edit history.  
- Expose results to users.  

---

## 5) ML-Based Detection Layer
When cryptographic proofs are absent or stripped, use **ML classifiers**:  

- **Convolutional Neural Networks (CNNs)** for pixel-level artifact detection.  
- **Noise Residual & PRNU-based models** for identifying real vs synthetic sources.  
- **Transformers (Vision + Multimodal)** for AI-model artifact detection.  
- **Metadata anomaly detection** using ML to classify inconsistencies (e.g., frame cadence, EXIF tags).  

**Classifier Arms Race Strategy**  
- Continuously retrain models against new AI generators.  
- Maintain benchmark sets of **AI-generated vs. real content**.  
- Ensemble classifiers (cryptographic + forensic + ML) for final decision.  

---

## 6) Verification Pipeline
1. **Intake**: File upload or URL provided.  
2. **Hashing & Pre-checks**.  
3. **C2PA Verification** (if present).  
4. **Sensor-PKI Verification** (if present).  
5. **ML Detection Pipeline** (if C2PA/PKI missing or inconclusive).  
   - Extract noise features, encoder toolmarks, metadata.  
   - Run ensemble classifiers.  
6. **Decision Logic**:  
   - Authentic (Camera)  
   - Authentic (C2PA)  
   - Likely AI-generated  
   - Unknown  
7. **Return Results** to frontend.  
8. **Purge Artifacts** after TTL expiry.  

---

## 7) Data & Privacy
- **No raw content retention.**  
- Ephemeral job storage in MongoDB.  
- Explicit “Delete Now” option for users.  
- Transparency page: clearly explains privacy guarantees.  

---

## 8) API Contract
- `POST /verify` — Upload file/URL. Returns `{ job_id }`.  
- `GET /verify/{job_id}` — Returns status, authenticity label, cryptographic proofs, ML classifier results.  
- `DELETE /verify/{job_id}` — Force immediate deletion.  
- `GET /health` — Service health check.  

---

## 9) Data Model (MongoDB)
- **jobs**: `{ id, hash, status, label, reasons[], createdAt }` (TTL).  
- **proofs**: `{ job_id, c2pa, sensor_pki, ml_results }`.  
- **metrics**: anonymized aggregate counts (e.g., % AI, % authentic).  

---

## 10) Deployment
- Docker Compose for development.  
- Kubernetes-ready for production scaling.  
- Secrets managed via Vault/KMS.  
- TLS via Nginx reverse proxy.  

---

## 11) KPIs
- **Precision/Recall** on benchmark datasets.  
- **Coverage**: % with valid proofs (C2PA/PKI).  
- **Detection performance**: ML classifier F1-score > 90%.  
- **Latency**: <2s per image, <4s per short video.  
- **User comprehension**: clear differentiation between “Unknown” and “Likely AI”.  

---

## 12) Implementation Timeline
- **Weeks 1–2**: Requirements, trust anchor setup.  
- **Weeks 3–6**: C2PA verification implementation.  
- **Weeks 5–8**: Sensor-PKI signature verification.  
- **Weeks 7–10**: ML classifier integration (CNN + PRNU + metadata).  
- **Weeks 9–12**: Ensemble decision logic + testing.  
- **Weeks 12–14**: Security hardening, deployment, documentation.  

---

## 13) Risks
- Rapid evolution of AI image generators.  
- Partial adoption of C2PA by platforms.  
- Potential adversarial bypass of ML classifiers.  
- Governance of manufacturer trust anchors.  

---

## 14) Documentation Deliverables
- **System Whitepaper** (cryptography + ML).  
- **Privacy & Security Policy**.  
- **API Reference**.  
- **ML Training Dataset Protocols**.  
- **Threat Model Analysis**.  

---

## 15) Why Hybrid Cryptography + ML Works
- **Positive proofs** (C2PA, sensor-PKI) → strong cryptographic guarantees.  
- **ML classifiers** → resilience against provenance stripping and AI artifacts.  
- **Ensemble decision** → layered assurance, user-facing clarity.  

---