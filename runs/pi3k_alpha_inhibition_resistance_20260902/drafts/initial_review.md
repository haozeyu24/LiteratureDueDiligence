# Mechanisms of Resistance to PI3K-alpha Inhibition in Cancer Treatment

## Draft Status

This is an initial verification-ready draft. Claims and citations are not final until later PubMed retrieval, metadata verification, full-text review, claim verification, and human inspection are complete.

`draft_access_status` values are provisional labels, not verified access states. Later retrieval agents must verify full text, abstract-only, title-only, unavailable, or user-download-needed status.

`discovery_provenance` values distinguish citations found by explicit search from citations recalled by the drafting model. Later agents must verify `llm_memory`, `unknown`, and `citation_needed` rows before using them as support.

## Executive Summary

PI3K-alpha inhibition is a clinically important strategy for selected PIK3CA-altered cancers, but resistance is expected because tumors can escape through target-pathway reactivation, compensatory signaling, phenotypic adaptation, incomplete pathway suppression, and treatment-context constraints. This initial draft maps the topic broadly so later agents can perform targeted PubMed retrieval, full-text review, RAG, and claim-by-claim verification.

The review should span approved and investigational inhibitors, including alpelisib, inavolisib, taselisib, STX-478, RLY-2608/RLy2608, and related PI3K-alpha or PIK3CA-directed agents. Clinical trials should be treated as evidence for both efficacy context and resistance interpretation, while avoiding the mistake of equating trial failure with biological resistance unless mechanistic, biomarker, pharmacodynamic, or specimen-based support is available.

## Chapter 1: Clinical And Biological Rationale

### Subsection 1.1: PIK3CA Alteration As A Therapeutic Entry Point

PIK3CA mutation and PI3K pathway activation provide the therapeutic entry point for PI3K-alpha inhibition. In a review about resistance, this background matters because the target is not merely a druggable node; it defines the molecular context in which response and escape should be interpreted. A later verification pass should distinguish evidence that establishes PIK3CA as a selection biomarker from evidence that explains why a treated tumor fails to respond or progresses.

The first drafting pass should therefore keep target-rationale papers, clinical testing guidance, and major trial papers visible, but not allow them to substitute for resistance evidence. Mutation prevalence, pathway activation, or biomarker-test adoption can justify why the field studies PI3K-alpha, yet those facts do not prove a resistance mechanism. Later agents should search for papers that connect PIK3CA alteration status to treatment exposure, response duration, acquired alterations, or functional escape.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S01-C001 | Andre et al., 2019, SOLAR-1 alpelisib plus fulvestrant | 31091374 | 10.1056/NEJMoa1813904 | trial_or_intervention | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | Clinical anchor for PIK3CA-mutated HR-positive advanced breast cancer. |
| S01-C002 | De Angelis et al., 2026, PIK3CA testing consensus | 41999684 | 10.1016/j.breast.2026.104786 | review_or_background | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Background for clinical testing; not primary resistance evidence. |
| S01-C003 | citation needed | unknown | unknown | review_or_background | full_text_needed_for_verification | unknown | citation_needed | Landmark review on PI3K pathway biology and PIK3CA mutation as target rationale. |
| S01-C004 | citation needed | unknown | unknown | clinical_or_translational | full_text_needed_for_verification | unknown | citation_needed | Large genomic/clinical source on PIK3CA alteration frequency by cancer type. |

### Subsection 1.2: Approved PI3K-alpha Inhibition And Clinical Benefit

Alpelisib established that selective PI3K-alpha inhibition can produce clinical benefit in a biomarker-selected population, but the same trial context also makes resistance visible. A durable-benefit question follows naturally from the gap between pathway rationale and the eventual recurrence or progression seen in advanced cancer treatment. For this review, alpelisib should be treated as the anchor for what PI3K-alpha inhibition can achieve and as a baseline for asking which biological or clinical factors limit that benefit.

The later verification workflow should inspect trial details rather than relying only on summary statements. Important extraction targets include prior therapy, endocrine context, PIK3CA testing method, progression-free survival, overall survival, adverse events, discontinuation, and subgroup findings. Those details determine whether a statement is really about biological resistance, treatment tolerability, trial design, patient selection, or incomplete pathway suppression.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S02-C001 | Andre et al., 2019, SOLAR-1 primary report | 31091374 | 10.1056/NEJMoa1813904 | trial_or_intervention | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | Primary alpelisib efficacy and safety context. |
| S02-C002 | Andre et al., 2021, SOLAR-1 final overall survival | 33246021 | 10.1016/j.annonc.2020.11.011 | trial_or_intervention | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | Follow-up survival interpretation. |
| S02-C003 | Rugo et al., BYLieve cohort A | 39637900 | unknown | trial_or_intervention | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | Post-CDK4/6 alpelisib setting; metadata needs verification. |
| S02-C004 | citation needed | unknown | unknown | clinical_or_translational | full_text_needed_for_verification | unknown | citation_needed | Real-world alpelisib outcomes and resistance/tolerability experience. |

### Subsection 1.3: Investigational Agents And Therapeutic-Index Hypothesis

Newer PI3K-alpha inhibitors are relevant because resistance is shaped by both tumor biology and drug properties. If an inhibitor cannot suppress the pathway deeply or continuously because of toxicity, hyperglycemia, rash, gastrointestinal toxicity, or other tolerability limits, then an apparent resistance pattern may reflect pharmacologic constraint rather than a purely genetic escape mechanism. Inavolisib, RLY-2608, and STX-478 should therefore be framed as attempts to improve selectivity, therapeutic index, mutant targeting, or combination feasibility.

This section should be careful not to overstate what next-generation inhibitors have proven. Improved selectivity, improved tolerability, clinical efficacy, and overcoming resistance are separate claims requiring different kinds of evidence. Later agents should search PubMed for each named investigational agent, distinguish preclinical from clinical evidence, and identify whether any paper actually tests resistance after prior PI3K-alpha inhibitor exposure.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S03-C001 | Wedam et al., 2025, FDA approval summary for inavolisib combination | 40845250 | 10.1200/JCO-25-00663 | trial_or_intervention | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | PubMed-indexed approval summary; not mechanistic proof. |
| S03-C002 | Overall survival with inavolisib in PIK3CA-mutated advanced breast cancer | 40454641 | unknown | trial_or_intervention | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | INAVO120 clinical outcome context; metadata needs verification. |
| S03-C003 | Varkaris et al., RLY-2608 discovery and clinical proof-of-concept | unknown | unknown | hypothesis_or_emerging | full_text_likely_available | reputable_or_likely_reputable | citation_needed | Mutant-selective allosteric inhibitor context; metadata needs verification. |
| S03-C004 | Buckbinder et al., 2023, STX-478 mutant-selective allosteric inhibitor | 37623743 | unknown | primary_mechanism | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | STX-478 preclinical/landscape anchor; DOI needs verification. |

## Chapter 2: On-Target And Pathway Reactivation Resistance

### Subsection 2.1: PTEN Loss As Acquired Resistance

PTEN loss is one of the clearest candidate mechanisms because it has a direct pathway rationale and has been described in acquired resistance contexts. Loss of PTEN can remove negative regulation of PI3K pathway signaling, allowing downstream signaling to persist or recover despite PI3K-alpha inhibition. This makes PTEN loss a strong early focus for claim verification, especially when patient-derived specimens or serial sampling show emergence after treatment.

The final review must still avoid making PTEN loss sound universal. A baseline PTEN alteration, a model-system perturbation, and an acquired lesion in a progressing patient are different evidence classes. Later agents should verify whether each paper shows treatment exposure, timing of emergence, functional rescue or perturbation, and tumor context. Full text will likely be required because abstract-level summaries may not contain enough detail to separate acquired resistance from background pathway alteration.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S04-C001 | Juric et al., 2015, convergent PTEN loss and resistance to BYL719 | 25409150 | 10.1038/nature13948 | primary_mechanism | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Direct acquired-resistance source; full text should be reviewed. |
| S04-C002 | Varkaris et al., 2024, acquired resistance alterations during alpelisib/inavolisib therapy | 37916958 | 10.1158/2159-8290.CD-23-0704 | primary_mechanism | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Patient evidence for acquired pathway alterations. |
| S04-C003 | citation needed | unknown | unknown | primary_mechanism | full_text_needed_for_verification | unknown | citation_needed | Functional model paper testing PTEN loss and PI3K-alpha inhibitor sensitivity. |
| S04-C004 | citation needed | unknown | unknown | clinical_or_translational | full_text_needed_for_verification | unknown | citation_needed | Clinical cohort or biomarker analysis linking PTEN status to PI3K-alpha inhibitor outcome. |

### Subsection 2.2: Secondary PIK3CA Mutations

Secondary PIK3CA mutations are important because they represent a possible on-target route to acquired resistance. Unlike bypass mechanisms, on-target alterations can directly change the relationship between drug structure, mutant kinase activity, and inhibitor potency. For a review that includes next-generation inhibitors, this section should separate resistance to orthosteric inhibitors from sensitivity or resistance to allosteric and mutant-selective agents.

The evidence here is likely to be technically nuanced. A secondary mutation may alter binding, change kinase activity, occur in cis or trans with an oncogenic mutation, or create a context in which one inhibitor class fails while another remains active. Later verification should prioritize full text, structural interpretation, functional assays, and patient-derived temporal evidence. If the draft uses broad language such as "secondary PIK3CA mutations drive resistance," that claim should be narrowed to the specific alterations and drugs supported by the evidence.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S05-C001 | Varkaris et al., 2024, secondary PIK3CA resistance mutations | 37916958 | 10.1158/2159-8290.CD-23-0704 | primary_mechanism | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Key source for acquired secondary PIK3CA alterations. |
| S05-C002 | Varkaris et al., 2024, RLY-2608 overcoming resistance mutations | 37916958 | 10.1158/2159-8290.CD-23-0704 | primary_mechanism | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Same source may support resistance-overcoming hypothesis. |
| S05-C003 | citation needed | unknown | unknown | primary_mechanism | full_text_needed_for_verification | unknown | citation_needed | Structural or biochemical paper on secondary PIK3CA mutations and inhibitor binding. |
| S05-C004 | citation needed | unknown | unknown | hypothesis_or_emerging | full_text_needed_for_verification | unknown | citation_needed | Preclinical paper comparing orthosteric and allosteric inhibitors against double mutants. |

### Subsection 2.3: AKT/mTOR Axis Compensation

Persistence or reactivation of AKT/mTOR signaling is a plausible resistance route because PI3K-alpha sits upstream of key survival and growth pathways. If downstream signaling remains active despite target inhibition, tumor cells may survive even when the primary driver is partially suppressed. This section should include model-system and translational evidence, but it must separate pathway-adjacent biology from experiments that specifically test PI3K-alpha inhibitor resistance.

Later agents should search for papers measuring phosphorylated AKT, mTOR signaling, pharmacodynamic suppression, and adaptive pathway rebound after treatment. They should also identify combination studies involving mTOR or AKT pathway cotargeting and decide whether those studies test resistance biology or merely add another active therapy. Full text is likely needed because abstracts often compress pathway readouts and do not always clarify timing, treatment dose, or whether the signaling change is causal.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S06-C001 | Varkaris et al., 2024, acquired pathway alterations | 37916958 | 10.1158/2159-8290.CD-23-0704 | primary_mechanism | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | May support convergent pathway reactivation. |
| S06-C002 | citation needed | unknown | unknown | primary_mechanism | full_text_needed_for_verification | unknown | citation_needed | Model-system paper showing AKT/mTOR reactivation after PI3K-alpha inhibitor treatment. |
| S06-C003 | citation needed | unknown | unknown | trial_or_intervention | full_text_needed_for_verification | unknown | citation_needed | Clinical combination paper involving PI3K-alpha inhibition and mTOR/AKT pathway strategy. |
| S06-C004 | citation needed | unknown | unknown | review_or_background | access_unknown | unknown | citation_needed | Review summarizing PI3K/AKT/mTOR feedback with primary-study pointers. |

## Chapter 3: Bypass Signaling And Crosstalk

### Subsection 3.1: MAPK/ERK Bypass

MAPK/ERK signaling is a plausible bypass route when PI3K-alpha blockade fails to produce durable control. A tumor may maintain proliferation or survival by shifting dependence toward parallel signaling networks, especially when receptor tyrosine kinase input or downstream pathway rewiring activates MAPK-family signaling. This idea is biologically plausible, but a review should not treat plausibility as proof. The key question is whether MAPK/ERK activation is observed after PI3K-alpha inhibitor exposure and whether inhibiting it reverses resistance.

For later verification, this subsection should become a focused search task rather than a broad pathway discussion. Agents should look for PI3K-alpha inhibitor-treated models with ERK rebound, MEK/MAPK cotargeting experiments, paired tumor or ctDNA analyses, and trial evidence where MAPK pathway alterations shape response. Full text will likely be required because abstracts may mention pathway crosstalk without showing whether it is causal, adaptive, or merely correlative.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S07-C001 | Varkaris et al., 2024, acquired resistance landscape | 37916958 | 10.1158/2159-8290.CD-23-0704 | primary_mechanism | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Check whether MAPK-family alterations are directly reported. |
| S07-C002 | citation needed | unknown | unknown | primary_mechanism | full_text_needed_for_verification | unknown | citation_needed | Experimental PI3K-alpha plus MEK/MAPK bypass-resistance paper. |
| S07-C003 | citation needed | unknown | unknown | trial_or_intervention | full_text_needed_for_verification | unknown | citation_needed | Combination trial or translational paper involving MAPK pathway cotargeting. |
| S07-C004 | citation needed | unknown | unknown | review_or_background | access_unknown | unknown | citation_needed | Background review on PI3K-MAPK crosstalk in targeted therapy resistance. |

### Subsection 3.2: HER2/ERBB And Receptor Tyrosine Kinase Crosstalk

Receptor tyrosine kinase signaling may maintain growth and survival despite PI3K-alpha inhibition. In HER2-driven or ERBB-active contexts, PI3K pathway activity can be shaped by upstream receptor signaling, feedback loops, and combination partners. This makes HER2/ERBB crosstalk relevant to a resistance review, but only when the paper explicitly connects that crosstalk to PI3K-alpha inhibitor response, resistance, or combination treatment.

Later verification should avoid drifting into general HER2 biology. The needed evidence is narrower: studies where PI3K-alpha inhibition is tested with HER2-directed therapy, where ERBB/EGFR signaling emerges during resistance, or where patient biomarker data link receptor signaling to PI3K-alpha inhibitor outcomes. A title/abstract pass may be enough to triage many papers, but full text is likely necessary for claims about causality, dose schedule, combination rationale, or subgroup interpretation.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S08-C001 | citation needed | unknown | unknown | primary_mechanism | full_text_needed_for_verification | unknown | citation_needed | Paper on HER2/ERBB crosstalk and PI3K-alpha inhibitor resistance. |
| S08-C002 | citation needed | unknown | unknown | trial_or_intervention | full_text_needed_for_verification | unknown | citation_needed | Trial of PI3K-alpha inhibitor combination in HER2-positive or HER2-altered setting. |
| S08-C003 | citation needed | unknown | unknown | clinical_or_translational | full_text_needed_for_verification | unknown | citation_needed | Patient biomarker paper connecting ERBB/EGFR signaling to PI3K-alpha inhibitor response. |
| S08-C004 | CD36 inhibition with PI3K inhibitors in PTEN-loss anti-HER2 resistant breast cancer cells | 39920872 | unknown | primary_mechanism | abstract_only_likely | uncertain | local_prior_run | Possible HER2-context/metabolism paper; venue and full text need verification. |

### Subsection 3.3: Endocrine Therapy Crosstalk

In HR-positive breast cancer, PI3K-alpha inhibition is often interpreted through endocrine resistance because approved and investigational regimens commonly combine PI3K-alpha inhibition with endocrine therapy. This creates a challenge for the review: endocrine resistance may be the clinical setting that motivates PI3K-alpha inhibition, the biological context that modifies response, or a parallel process that is not itself PI3K-alpha inhibitor resistance.

The later verification workflow should therefore mark claims carefully. A paper showing benefit from alpelisib plus fulvestrant supports a combination strategy, but does not automatically prove that endocrine resistance is overcome through a specific molecular mechanism. Agents should search for translational analyses, ESR1 or ER pathway interactions, post-CDK4/6 settings, and biomarker-stratified outcomes. Full text will often be needed to interpret subgroup definitions and treatment history.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S09-C001 | Andre et al., 2019, SOLAR-1 | 31091374 | 10.1056/NEJMoa1813904 | trial_or_intervention | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | Fulvestrant combination context. |
| S09-C002 | Rugo et al., BYLieve cohort A | 39637900 | unknown | trial_or_intervention | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | Post-CDK4/6 endocrine-resistant setting. |
| S09-C003 | Wedam et al., 2025, inavolisib approval summary | 40845250 | 10.1200/JCO-25-00663 | trial_or_intervention | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | Inavolisib plus palbociclib and fulvestrant context. |
| S09-C004 | citation needed | unknown | unknown | clinical_or_translational | full_text_needed_for_verification | unknown | citation_needed | Translational endocrine-resistance biomarker paper tied to PI3K-alpha therapy. |

## Chapter 4: Cellular State And Microenvironmental Resistance

### Subsection 4.1: Tumor Heterogeneity And Clonal Selection

PI3K-alpha inhibitor resistance may reflect pre-existing resistant clones, therapy-induced selection, or mixed subclonal dependencies rather than a single uniform mechanism. This matters because a trial-level response can hide heterogeneous biology: one lesion may remain sensitive while another progresses through a distinct acquired alteration. Serial sampling, ctDNA, and autopsy studies are therefore especially valuable for connecting resistance claims to temporal evidence.

The final review should not overinterpret heterogeneity without strong evidence. A baseline mixed tumor population is not the same as a clone selected by PI3K-alpha inhibitor therapy, and a ctDNA alteration detected at progression is not automatically causal. Later agents should extract timing, allele dynamics, treatment exposure, lesion context, and any functional validation. Full text will be important because these details are rarely complete in abstracts.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S10-C001 | Varkaris et al., 2024, patient acquired resistance analysis | 37916958 | 10.1158/2159-8290.CD-23-0704 | clinical_or_translational | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Serial/resistance evidence; full text needed. |
| S10-C002 | citation needed | unknown | unknown | clinical_or_translational | full_text_needed_for_verification | unknown | citation_needed | ctDNA paper tracking PIK3CA-pathway alterations after PI3K-alpha inhibitor exposure. |
| S10-C003 | citation needed | unknown | unknown | primary_mechanism | full_text_needed_for_verification | unknown | citation_needed | Clonal selection model paper after PI3K-alpha inhibitor treatment. |
| S10-C004 | citation needed | unknown | unknown | review_or_background | access_unknown | unknown | citation_needed | Review on tumor heterogeneity in targeted therapy resistance with relevant primary pointers. |

### Subsection 4.2: Phenotypic Plasticity And Lineage Adaptation

Some resistance may arise through phenotypic adaptation rather than a single genomic alteration. Cells may shift transcriptional state, lineage program, metabolic dependency, or stress-response behavior in ways that reduce dependence on the inhibited PI3K-alpha node. This is an attractive explanation for incomplete responses and heterogeneous escape, but it is also a zone where review writing can become too speculative.

Later verification should demand direct connection to PI3K-alpha inhibitor exposure. Evidence should show that a plasticity state appears during treatment, predicts response, changes drug sensitivity, or can be reversed by a rational combination. If only general targeted-therapy plasticity literature exists, the final review should mark the mechanism as a hypothesis or background concept rather than a demonstrated PI3K-alpha resistance mechanism.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S11-C001 | citation needed | unknown | unknown | primary_mechanism | full_text_needed_for_verification | unknown | citation_needed | Paper on transcriptional or lineage plasticity after PI3K-alpha inhibitor exposure. |
| S11-C002 | citation needed | unknown | unknown | primary_mechanism | full_text_needed_for_verification | unknown | citation_needed | Single-cell or functional-state paper tied to PI3K-alpha inhibitor resistance. |
| S11-C003 | citation needed | unknown | unknown | clinical_or_translational | full_text_needed_for_verification | unknown | citation_needed | Patient-derived evidence for adaptive state changes during PI3K-alpha therapy. |
| S11-C004 | citation needed | unknown | unknown | hypothesis_or_emerging | access_unknown | unknown | citation_needed | Emerging/preprint evidence on non-genetic resistance state. |

### Subsection 4.3: Metabolic And Microenvironmental Escape

Metabolic adaptation and tumor microenvironment effects may contribute to resistance, but they are at high risk of becoming vague background unless directly connected to PI3K-alpha inhibitor response. These mechanisms may matter when tumor cells alter nutrient use, interact with stromal or immune compartments, or survive under therapy-induced stress. Still, the review should separate a biologically plausible escape route from evidence that the route changes sensitivity to a PI3K-alpha inhibitor.

Later agents should search for perturbation experiments, patient-derived correlations, and combination strategies that test metabolic or microenvironmental dependencies in the setting of PI3K-alpha blockade. Title and abstract may identify candidate papers, but full text is likely needed to confirm exact drug, model, pathway readouts, and venue quality. If evidence remains indirect, this section should be written as an emerging hypothesis rather than a settled resistance class.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S12-C001 | CD36 inhibition with PI3K inhibitors in PTEN-loss anti-HER2 resistant breast cancer cells | 39920872 | unknown | primary_mechanism | abstract_only_likely | uncertain | local_prior_run | Possible metabolic/HER2-context mechanism; needs venue and full-text check. |
| S12-C002 | citation needed | unknown | unknown | primary_mechanism | full_text_needed_for_verification | unknown | citation_needed | Metabolic adaptation paper directly after PI3K-alpha inhibition. |
| S12-C003 | citation needed | unknown | unknown | clinical_or_translational | full_text_needed_for_verification | unknown | citation_needed | Patient or translational evidence for microenvironment-mediated PI3K-alpha inhibitor resistance. |
| S12-C004 | citation needed | unknown | unknown | review_or_background | access_unknown | unknown | citation_needed | Review on metabolism or microenvironment in PI3K-pathway targeted therapy resistance. |

## Chapter 5: Clinical Trials As Resistance Evidence

### Subsection 5.1: Positive Trials And Durable-Benefit Limits

Positive trials define the therapeutic settings where PI3K-alpha inhibition has value, but they also show the limits of durability. A progression-free survival benefit confirms clinical activity in a selected population, yet resistance remains visible because advanced cancers eventually progress and because not all selected patients respond equally. These trials are essential for understanding which clinical contexts make PI3K-alpha inhibition useful and which contexts need stronger resistance explanations.

The later verification stage should treat each trial as a structured evidence object. Agents should extract treatment line, prior endocrine therapy, prior CDK4/6 inhibitor exposure, mutation-detection method, response endpoints, survival endpoints, adverse events, dose interruptions, discontinuation, and subgroup analyses. Those details will prevent the final review from making a common error: turning trial outcomes into unsupported mechanism claims. Full text is likely needed for exact subgroup and safety interpretation.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S13-C001 | Andre et al., 2019, SOLAR-1 | 31091374 | 10.1056/NEJMoa1813904 | trial_or_intervention | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | Primary positive-trial anchor. |
| S13-C002 | Andre et al., 2021, SOLAR-1 final OS | 33246021 | 10.1016/j.annonc.2020.11.011 | trial_or_intervention | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | Long-term outcome anchor. |
| S13-C003 | Rugo et al., BYLieve cohort A | 39637900 | unknown | trial_or_intervention | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | Post-CDK4/6 clinical setting. |
| S13-C004 | Overall survival with inavolisib in PIK3CA-mutated advanced breast cancer | 40454641 | unknown | trial_or_intervention | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | Newer inavolisib outcome context. |

### Subsection 5.2: Failed, Negative, Or Limited Trials

Failed, negative, or clinically limited trials identify the boundary between mechanistic rationale and clinical utility. They can show that a target is biologically valid but difficult to drug, that a combination is mechanistically appealing but poorly tolerated, or that patient selection was not sufficient to produce durable benefit. In a resistance review, these papers are valuable because failure often motivates next-generation inhibitors and combinations.

The final review should be precise about what failed. A drug may fail because of toxicity, dose intensity, pharmacokinetics, trial design, disease context, lack of pathway suppression, or true biological resistance. Those are not interchangeable explanations. Later agents should collect full text for important negative trials, because abstracts may report headline outcomes without enough detail to decide whether the trial informs resistance biology or mainly therapeutic-index limitations.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S14-C001 | Dent et al., 2021, SANDPIPER taselisib phase III | 33186740 | 10.1016/j.annonc.2020.10.596 | negative_or_failed_result | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Key negative/limited-utility trial. |
| S14-C002 | citation needed | unknown | unknown | negative_or_failed_result | full_text_needed_for_verification | unknown | citation_needed | Earlier taselisib phase I/II trial or toxicity paper. |
| S14-C003 | citation needed | unknown | unknown | negative_or_failed_result | full_text_needed_for_verification | unknown | citation_needed | Pictilisib or other PI3K-alpha-relevant trial with limited efficacy/tolerability. |
| S14-C004 | citation needed | unknown | unknown | review_or_background | access_unknown | unknown | citation_needed | Review comparing PI3K inhibitor development failures and therapeutic index. |

### Subsection 5.3: Combination Trials Designed To Overcome Resistance

Combination trials should be reviewed as tests of resistance logic. Endocrine combinations, CDK4/6 combinations, HER2-directed combinations, and pathway cotargeting each imply a different escape hypothesis. A trial can support the clinical usefulness of a combination, but it does not automatically prove the biological mechanism unless paired with translational samples, pharmacodynamic data, or a design that directly tests a resistance state.

Later agents should build a table that records combination partner, disease context, treatment line, prior therapies, mutation status, response endpoints, toxicity limitations, and whether the trial includes biomarker or specimen evidence. This will let the final review explain why combinations are being tested without overstating what they demonstrate. Papers with unavailable full text should enter the user-download queue if they influence claims about subgroup response or resistance-overcoming rationale.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S15-C001 | Wedam et al., 2025, inavolisib plus palbociclib and fulvestrant approval summary | 40845250 | 10.1200/JCO-25-00663 | trial_or_intervention | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | Triple-combination clinical context. |
| S15-C002 | INAVO120 safety analyses | 42202490 | 10.1016/j.esmoop.2026.107735 | trial_or_intervention | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Combination tolerability context; date/metadata need verification. |
| S15-C003 | citation needed | unknown | unknown | trial_or_intervention | full_text_needed_for_verification | unknown | citation_needed | PI3K-alpha inhibitor plus HER2-directed therapy trial. |
| S15-C004 | citation needed | unknown | unknown | trial_or_intervention | full_text_needed_for_verification | unknown | citation_needed | PI3K-alpha inhibitor plus AKT/mTOR/MAPK-pathway combination trial. |

## Chapter 6: Next-Generation Inhibitors And Future Resistance Questions

### Subsection 6.1: Mutant-Selective And Allosteric PI3K-alpha Inhibitors

Mutant-selective and allosteric PI3K-alpha inhibitors are designed to improve therapeutic index and may change the resistance landscape. This chapter should separate improved selectivity, improved tolerability, improved clinical activity, and resistance-overcoming activity as distinct claims. A paper can strongly support one of these claims while only weakly supporting another. That distinction matters because next-generation drug narratives often compress several advantages into one story.

For later verification, RLY-2608 and STX-478 should each receive targeted PubMed searches that distinguish discovery chemistry, preclinical activity, mutant selectivity, clinical proof-of-concept, and resistance models. Preprints or early reports may be important, but they should be labeled and not treated as settled evidence. Full text will be important for understanding whether a study tests prior alpelisib/inavolisib resistance, secondary PIK3CA mutations, or only untreated PIK3CA-mutant models.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S16-C001 | Varkaris et al., RLY-2608 discovery and clinical proof-of-concept | unknown | unknown | hypothesis_or_emerging | full_text_likely_available | reputable_or_likely_reputable | citation_needed | RLY-2608 landscape and early clinical context; metadata needs verification. |
| S16-C002 | Varkaris et al., 2024, acquired resistance and RLY-2608 | 37916958 | 10.1158/2159-8290.CD-23-0704 | primary_mechanism | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Resistance-overcoming claim source. |
| S16-C003 | Buckbinder et al., 2023, STX-478 | 37623743 | unknown | primary_mechanism | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | STX-478 allosteric inhibitor source. |
| S16-C004 | citation needed | unknown | unknown | hypothesis_or_emerging | access_unknown | unknown | citation_needed | Preprint or recent PubMed-indexed paper on mutant-selective PI3K-alpha inhibitor resistance profile. |

### Subsection 6.2: Biomarker Strategy And Patient Selection

Resistance is partly a biomarker problem. Baseline PIK3CA mutation may select patients for therapy, but additional genomic, transcriptomic, proteomic, or clinical features may shape sensitivity, resistance, tolerability, and combination choice. A high-quality review should separate predictive biomarkers, acquired resistance biomarkers, prognostic markers, and exploratory correlates. These categories often get blurred in narrative reviews.

Later agents should search for biomarker analyses from major trials and translational studies that link baseline or acquired alterations to outcomes after PI3K-alpha inhibition. Full text is likely necessary for subgroup definitions, assay methods, cutoff values, and treatment context. A biomarker can be clinically useful even if not mechanistically causal, and a mechanistic alteration can be biologically convincing without yet being clinically validated. The final review should keep both distinctions visible.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S17-C001 | Andre et al., 2019, SOLAR-1 biomarker-selected trial | 31091374 | 10.1056/NEJMoa1813904 | clinical_or_translational | abstract_only_likely | reputable_or_likely_reputable | local_prior_run | PIK3CA mutation selection context. |
| S17-C002 | De Angelis et al., 2026, PIK3CA testing consensus | 41999684 | 10.1016/j.breast.2026.104786 | review_or_background | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Testing and clinical implementation. |
| S17-C003 | Varkaris et al., 2024, acquired alterations | 37916958 | 10.1158/2159-8290.CD-23-0704 | clinical_or_translational | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Acquired resistance biomarker context. |
| S17-C004 | citation needed | unknown | unknown | clinical_or_translational | full_text_needed_for_verification | unknown | citation_needed | Biomarker subgroup analysis for alpelisib/inavolisib/taselisib outcome. |

### Subsection 6.3: Verification Priorities For The Next Workflow Stages

The highest-priority verification targets are PTEN loss, secondary PIK3CA mutations, AKT/mTOR reactivation, MAPK/ERBB bypass, endocrine/HER2 crosstalk, and whether next-generation inhibitors overcome resistance rather than only improving tolerability. These are the places where a draft can easily sound confident before the evidence has earned that confidence. The next agents should convert each subsection into explicit claims, PubMed search tasks, and evidence packets.

This final subsection should also guide the human reviewer. The current draft intentionally includes `citation needed` rows because it is safer to expose missing evidence than to invent citation metadata. Those rows are not failures; they are work orders for retrieval and RAG. The downstream system should resolve unknown PMIDs/DOIs, verify access status, apply venue labels, build a user-download queue for missing full text, and rewrite each claim using only verified evidence.


For the next workflow stage, this subsection should be converted into explicit claims, targeted PubMed searches, access checks, venue labels, and full-text-needed decisions, and evidence-priority notes.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S18-C001 | Juric et al., 2015, PTEN loss resistance | 25409150 | 10.1038/nature13948 | primary_mechanism | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Top-priority full-text verification. |
| S18-C002 | Varkaris et al., 2024, acquired resistance mechanisms | 37916958 | 10.1158/2159-8290.CD-23-0704 | primary_mechanism | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Top-priority full-text verification. |
| S18-C003 | Dent et al., 2021, SANDPIPER | 33186740 | 10.1016/j.annonc.2020.10.596 | negative_or_failed_result | full_text_likely_available | reputable_or_likely_reputable | local_prior_run | Trial limitation and safety verification. |
| S18-C004 | citation needed | unknown | unknown | citation_needed | full_text_needed_for_verification | unknown | citation_needed | Comprehensive PubMed retrieval task for PI3K-alpha inhibitor resistance mechanisms not already named in this draft. |

