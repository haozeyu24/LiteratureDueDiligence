# Structured Review Instruction

## Objective

- objective: Produce a comprehensive literature review on mechanisms of resistance to PI3K-alpha inhibition in cancer treatment, spanning laboratory mechanism studies, translational patient evidence, clinical trial outcomes, and treatment-combination strategies for approved and investigational PI3K-alpha/PIK3CA-directed inhibitors.
- why this review is needed: The user wants to understand the many potential resistance mechanisms to PI3K-alpha inhibition and connect those mechanisms to real drug development, trial success or failure, and combination approaches designed to prevent or overcome resistance.

## Downstream Use And Audience

- downstream use: initial review drafting followed by claim-centered RAG, citation verification, full-text review when available, and human scientific inspection
- likely audience: cancer biology, translational oncology, precision oncology, targeted therapy, and oncology drug development readers
- expertise level: specialist scientific or clinical-translational audience

## Desired Review Product

- product type: structured review draft that can later be decomposed into chapters, sections, and claims for verification
- expected depth: broad and evidence-rich, with enough paper coverage to support downstream RAG and claim verification
- target length or paper count: as many relevant PubMed-indexed papers as practical unless the user later provides a specific paper-count target; initial draft should be expansive rather than a compact essay
- required tables, figures, or special sections: inferred useful outputs include an inhibitor landscape table, clinical trial table across phases and outcomes, resistance mechanism evidence table, combination-strategy table, full-text-needed queue, and optional mechanism map

## Primary Scope

### Primary Entities

- named entities: PI3K-alpha; PI3Ki; alpelisib; inavolisib; STX478; RLy2608
- aliases or synonyms: PIK3CA; PI3K alpha; PI3K-alpha inhibition; PI3K-alpha inhibitors; PI3Kalpha inhibitors; PIK3CA inhibitors
- inferred aliases: RLY-2608 as an alternate spelling for RLy2608; mutant-selective PI3K-alpha inhibitors; PIK3CA-directed inhibitors; approved and investigational PI3K-alpha-selective agents

### Required Context

- disease, biological system, population, organism, model, or setting: cancer treatment; laboratory cancer models; patient-derived material; translational oncology; clinical trial cohorts
- required exposure, perturbation, comparator, or condition: PI3K-alpha/PIK3CA inhibitor exposure, treatment, response, non-response, relapse, progression, resistance, clinical outcome, biomarker evidence, or combination strategy related to overcoming PI3Ki resistance

### Mechanisms, Processes, Or Evidence Classes

- primary mechanisms/processes/evidence classes: acquired resistance; intrinsic resistance; adaptive resistance; bypass signaling; pathway reactivation; feedback activation; secondary or compensatory genomic alterations; loss or alteration of pathway regulators; tumor heterogeneity; phenotypic plasticity; clinical resistance; biomarker-defined response or resistance; combination strategies designed to overcome resistance
- secondary mechanisms/processes/evidence classes: toxicity, dosing, pharmacokinetics, pharmacodynamics, study design, and tolerability only when they explain clinical failure, limited pathway suppression, discontinuation, or feasibility of resistance-overcoming combinations

### Outcomes Or Relationships Of Interest

- primary outcomes or relationships: resistance mechanism; treatment response; lack of response; relapse; progression; acquired alteration; sensitivity; durable response; clinical benefit; trial success; trial failure; biomarker-associated response or resistance; rationale for drug combinations
- secondary outcomes or relationships: pathway activation, cancer prognosis, biomarker prevalence, or general pathway biology only when directly connected to PI3K-alpha inhibitor treatment, response, resistance, or clinical trial interpretation
- outcomes insufficient by themselves: PIK3CA mutation frequency; generic PI3K pathway activation; general cancer prognosis; pathway biology without inhibitor exposure; biomarker associations without treatment-response or resistance connection

## Paper And Evidence Preferences

### Paper Types To Prioritize

- primary laboratory mechanism papers studying resistance to PI3K-alpha/PIK3CA inhibition
- studies using cancer cell lines, organoids, xenografts, patient-derived models, perturbation/rescue experiments, tumor biopsies, ctDNA, or biomarker analyses
- clinical trial publications across phases, including positive, negative, failed, discontinued, and combination trials
- translational analyses from real patients or clinical trial specimens
- papers on approved and investigational PI3K-alpha/PIK3CA-directed inhibitors, including named agents and closely related agents
- high-value reviews for background, field framing, inhibitor landscape, and identification of primary evidence
- preprints when relevant, especially for emerging investigational inhibitors or recent resistance findings

### Paper Types To Deprioritize

- generic PI3K pathway biology without cancer-treatment resistance or clinical outcome relevance
- prognostic PIK3CA mutation papers without PI3K-alpha inhibitor exposure or response/resistance evidence
- pan-PI3K, PI3K-beta, PI3K-delta, PI3K-gamma, AKT, mTOR, or MAPK inhibitor papers unless directly tied to PI3K-alpha resistance, comparator context, or a relevant combination strategy
- toxicity-only, pharmacokinetic-only, formulation-only, or dosing-only papers unless they explain trial failure, discontinuation, limited pathway suppression, or combination feasibility
- low-trust or hard-blocked venue papers, except for audit logging or user-requested discussion of noisy literature

### Must-Include Seeds

- alpelisib
- inavolisib
- STX478
- RLy2608
- other approved or investigational PI3K-alpha/PIK3CA-directed inhibitors when connected to resistance, clinical outcome, or combination evidence

### Date, Species, Model, Or Setting Preferences

- date range: unspecified
- species: human patient evidence and cancer laboratory models are both in scope
- model systems: cancer cell lines, organoids, xenografts, patient-derived models, translational specimens, and clinical trial cohorts are in scope
- setting preferences: clinical trial evidence should span phase, outcome, success/failure status, and combination rationale when available

### Preprint Policy

- include preprints: yes
- how preprints should be labeled or limited: preprints should be clearly labeled as non-peer-reviewed or preprint evidence. They may inform emerging areas but should not alone establish settled mechanistic or clinical claims when peer-reviewed evidence is available. Major preprint-dependent claims should be flagged for human inspection.

## Retrieval Scope

### Search Anchors

- required anchors: PI3K-alpha; PI3K alpha; PIK3CA; PI3Ki; alpelisib; inavolisib; STX478; RLy2608; RLY-2608; other PI3K-alpha/PIK3CA-directed inhibitor terms
- optional anchors: resistance; acquired resistance; intrinsic resistance; adaptive resistance; relapse; progression; non-response; sensitivity; clinical benefit; biomarker; trial outcome; combination therapy; pathway reactivation; bypass signaling; feedback activation
- citation clues: none provided by the user

### Allowed Expansion Terms

- synonyms: PI3K-alpha; PI3K alpha; PI3Kalpha; PIK3CA; PI3K-alpha inhibitor; PIK3CA inhibitor; PI3Ki; mutant-selective PI3K-alpha inhibitor
- assay or method terms: cell line; organoid; xenograft; patient-derived model; tumor biopsy; ctDNA; biomarker analysis; clinical trial; phase 1; phase 2; phase 3; translational analysis
- related entities allowed only with the primary anchors: AKT; mTOR; MAPK; ERK; HER2; ERBB2; EGFR; endocrine therapy; CDK4/6 inhibitors; PTEN; pathway reactivation; bypass signaling; feedback activation; combination therapy

### Background-Only Context

- context useful for framing but not as standalone retrieval drivers: general PI3K pathway biology; targeted therapy resistance; breast cancer treatment background; endocrine resistance; HER2 crosstalk; pathway feedback; inhibitor development history; precision oncology biomarker concepts

### Explicit Exclusions

- excluded topics: generic cancer prognosis, mutation prevalence, or pathway signaling without PI3K-alpha inhibitor treatment relevance
- excluded paper types: toxicity-only, pharmacokinetic-only, dosing-only, or formulation-only reports unless connected to trial failure, pathway suppression, resistance, or combination feasibility
- excluded contexts: non-PI3K-alpha isoform inhibitor literature unless used as direct comparator, historical development context, or mechanism/combination evidence tied back to PI3K-alpha inhibition

### Source And Venue Trust

- primary discovery source: PubMed
- hard blocklist: apply `resources/journal_blocklist.csv`; hard-blocked papers should not support final review claims
- reputable-journal policy: prefer reputable or likely reputable journals, but do not invent a rigid universal whitelist of acceptable journals
- uncertain venue handling: label each paper's venue as `reputable_or_likely_reputable`, `uncertain`, `preprint_server`, or `hard_blocked`; keep uncertain venue labels visible for downstream RAG, claim verification, rewrite confidence, and human inspection

## Claim Verification Rules

### Evidence That Supports A Claim

- direct evidence: a paper directly studies PI3K-alpha/PIK3CA inhibitor exposure in cancer and reports resistance, response, progression, relapse, biomarker outcome, acquired alteration, mechanistic experiment, patient-derived evidence, or combination response
- indirect evidence: a paper studies a related pathway, comparator, or combination only when the evidence is explicitly tied back to PI3K-alpha/PIK3CA inhibitor resistance or clinical outcome
- review-level evidence: useful for field framing, historical context, inhibitor landscape, and finding primary studies, but not sufficient by itself for final mechanistic or clinical claims unless the claim is explicitly review-level
- acceptable use of negative or failed results: failed, negative, discontinued, or toxicity-limited trials are important when they clarify biological resistance, lack of efficacy, biomarker selection, dosing limitations, pathway suppression, or rationale for later combinations

### Evidence That Is Insufficient By Itself

- co-occurrence-only signals: papers that merely mention PIK3CA/PI3K-alpha and resistance without demonstrating a relevant treatment-response, resistance, or mechanism relationship
- background-only signals: general PI3K pathway activation or oncogenic signaling without PI3K-alpha inhibitor response/resistance relevance
- association-only signals: PIK3CA mutation prevalence, prognosis, or pathway activation alone, especially when used to support causal resistance claims
- review-only signals: review statements without traceable primary evidence for mechanistic, translational, or clinical claims

### Full-Text Handling

- full-text review requirement: full text should be reviewed whenever available, especially for mechanistic, causal, patient-derived, trial-failure, comparative, or combination-strategy claims
- title/abstract fallback: if full text is unavailable, title and abstract should still be reviewed and the evidence should be labeled as title/abstract-only
- missing full-text queue: relevant papers whose full text is needed for confident verification should be added to a user-download queue with PMID/DOI/title, why full text is needed, and the claims it affects
- claims that require full text before final acceptance: causal mechanism claims, patient-derived resistance claims, clinical trial interpretation, failed-trial rationale, comparative claims across inhibitors or combinations, and claims based on subgroup or biomarker analyses

### Claims Requiring Extra Scrutiny

- broad mechanism claims: any statement that a pathway, mutation, or cellular state broadly causes PI3K-alpha inhibitor resistance across cancers
- causal claims: claims that a specific alteration, bypass pathway, feedback loop, or phenotype drives resistance
- clinical/translational claims: claims about patient resistance, biomarker-response relationships, trial outcomes, or treatment failure
- comparative or superiority claims: claims that one inhibitor, combination, or strategy overcomes resistance better than another
- citation-sensitive claims: claims involving investigational agents, failed trials, subgroup analyses, preprints, and cross-trial comparisons

### Citation Risk Areas

- likely citation traps: confusing PI3K-alpha-selective inhibitors with pan-PI3K or other PI3K isoform inhibitors; citing general PI3K biology as resistance evidence; citing biomarker prevalence as treatment-resistance evidence; using trial toxicity or dosing limits as if they proved biological resistance; overusing reviews as primary evidence
- papers that may be easy to confuse: trials of related PI3K pathway inhibitors, AKT inhibitors, mTOR inhibitors, endocrine combinations, HER2 combinations, or pan-PI3K agents that are not specifically PI3K-alpha/PIK3CA inhibitor resistance studies
- claims likely to need full text: mechanistic claims, patient-derived resistance claims, clinical trial interpretation, failed-trial rationale, subgroup biomarker claims, investigational-agent claims, and combination strategy claims

## Review Structure Guidance

- desired chapter order: introduce the clinical and biological rationale for PI3K-alpha inhibition; summarize approved and investigational inhibitor landscape; organize resistance mechanisms by evidence type and biological process; integrate patient and clinical trial evidence; discuss combination strategies; identify unresolved questions and translational outlook
- required recurring distinctions: distinguish laboratory evidence from patient evidence; intrinsic from acquired from adaptive resistance; direct evidence from pathway-adjacent rationale; peer-reviewed evidence from preprints; approved inhibitor evidence from investigational-agent evidence; trial failure due to resistance from failure due to toxicity, dosing, biomarker selection, or study design; venue-reliable evidence from uncertain or hard-blocked evidence
- places where tables or mechanism maps may help: inhibitor landscape table, clinical trial table, resistance mechanism evidence table, full-text-needed queue, combination strategy table, and mechanism map

## Uncertainty And Controversy Guidance

- unresolved questions: which mechanisms are causal in patients versus model-specific; how often resistance reflects target-pathway reactivation versus bypass signaling; whether combination strategies overcome biological resistance or mainly manage tolerability and selection constraints; how mutant-selective investigational inhibitors change resistance mechanisms
- competing explanations: biological resistance, inadequate pathway suppression, toxicity-limited dosing, tumor heterogeneity, biomarker selection, line-of-therapy context, and study design can each explain clinical outcomes
- known limitations: the user did not specify cancer-type priorities, target paper count, date range, citation style, final review length, or a formal definition of reputable journal

## Notes

- user-stated priorities: include laboratory mechanisms, real-patient evidence, clinical trial outcomes, approved and investigational inhibitors, named agents, trials across phases, successful and failed trials, and combination trials designed to overcome PI3Ki resistance
- important inferences: PIK3CA is treated as a key synonym/entity for PI3K-alpha inhibition; RLY-2608 is treated as an inferred spelling variant of RLy2608; related pathway components and combination partners are allowed only when tied back to PI3K-alpha/PIK3CA inhibitor resistance or clinical outcome
- things deliberately left unspecified: target paper count, cancer-type prioritization, date range, citation style, final review length, and exact reputable-journal whitelist
