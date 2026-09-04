# Semantic Query Design Work Order

Before PubMed execution, an LLM query designer must read each subsection
context as an evidence need and rewrite `query_plan.csv` into executable
semantic PubMed queries. The heuristic scaffold is only a seed.

For each subsection, identify:

- the claim or evidence need being searched;
- primary entity/family terms and allowed synonyms;
- mechanism, endpoint, assay, model, disease, or population terms;
- likely false-positive meanings and exclusions;
- query intents, choosing the number needed for the subsection complexity;
- query intents such as primary mechanism, context/model, method/readout,
  synonym/family analog, or citation recall only when scientifically needed.

Replace each scaffolded `semantic_seed` row with real initial queries
before PubMed execution. Narrow/simple subsections may use a small
number of queries; complex subsections with multiple entities,
mechanisms, models, interventions, or citation-recall needs may use
more. Each initial query in a subsection must have a distinct
`query_type` intent label.

Set `semantic_query_design_status` to `llm_semantic_designed` only after
the LLM has performed this reading and written the executable query.

If PubMed execution later stages `query_redesign` rows, treat them as a
second semantic design work order. The LLM must read the parent
subsection, parent query, count status, diagnostic rationale, and false
positive risks, then rewrite the row and set
`semantic_query_design_status=llm_semantic_redesigned` before execution.

## Subsections

### SUB001: PIK3CA Alteration As Entry Point, Not Resistance Explanation

Draft prose:

PIK3CA alteration provides the main clinical entry point for PI3K-alpha inhibition, especially in HR-positive/HER2-negative advanced breast cancer. SOLAR-1 showed that adding alpelisib to fulvestrant improved progression-free survival in the PIK3CA-mutated cohort, making PIK3CA mutation a treatment-selection biomarker rather than a resistance mechanism by itself. A review on resistance should therefore separate biomarker eligibility from the biological events that emerge after treatment pressure. This distinction matters because PIK3CA-mutant tumors are heterogeneous. Some tumors may depend strongly on PI3K-alpha signaling, while others carry co-alterations or adaptive programs that blunt response. Later retrieval should verify both canonical and noncanonical PIK3CA contexts, but claim verification should reject statements that treat PIK3CA positivity alone as proof of sensitivity or resistance. Full text may be needed for biomarker subgroup details, testing methods, co-alterations, and clinical context. Later stages should convert this subsection into explicit claims, PubMed queries, access checks, and evidence-priority notes. Claim verification should separate direct resistance evidence from background biology, trial context, and plausible but unproven combination rationale.

Citation/search notes:

- S01-C001: Andre et al., SOLAR-1 alpelisib plus fulvestrant in PIK3CA-mutated advanced breast cancer; PMID=31091374; DOI=10.1056/NEJMoa1813904; notes=Clinical entry-point anchor; verify subgroup and safety details.
- S01-C002: Genomic determinants of response to alpelisib plus fulvestrant in SOLAR-1; PMID=41967638; DOI=10.1016/j.annonc.2026.04.003; notes=Biomarker heterogeneity anchor; full text likely important.
- S01-C003: Extended spectrum of PIK3CA mutations detected in breast carcinoma; PMID=36321996; DOI=unknown; notes=Noncanonical PIK3CA mutation and testing context.
- S01-C004: citation needed; PMID=unknown; DOI=unknown; notes=Broad PIK3CA alteration prevalence across cancers.

### SUB002: Approved Alpelisib Benefit And The Durability Problem

Draft prose:

Alpelisib established that selective PI3K-alpha inhibition can be clinically useful, but the same clinical experience makes the durability problem visible. A median progression-free survival benefit does not imply durable disease control for all patients, and progression after benefit may reflect acquired tumor evolution, pre-existing resistant subclones, endocrine partner failure, incomplete pathway suppression, or treatment interruption due to adverse events. Resistance review language should preserve these alternatives rather than assigning every progression event to a single biological mechanism. Safety and pharmacology are part of the resistance frame because dose intensity and tolerability can shape apparent efficacy. Hyperglycemia, rash, diarrhea, and discontinuation are not tumor resistance, but they may reduce exposure and complicate comparisons among inhibitors. Later stages should retrieve trial reports and toxicity-management papers while keeping supportive-care claims separate from mechanistic resistance claims. Later stages should convert this subsection into explicit claims, PubMed queries, access checks, and evidence-priority notes. Claim verification should separate direct resistance evidence from background biology, trial context, and plausible but unproven combination rationale.

Citation/search notes:

- S02-C001: Andre et al., SOLAR-1 primary report; PMID=31091374; DOI=10.1056/NEJMoa1813904; notes=Primary alpelisib efficacy/safety anchor.
- S02-C002: Andre et al., SOLAR-1 final overall survival; PMID=33246021; DOI=10.1016/j.annonc.2020.11.011; notes=Mature OS and time-to-chemotherapy interpretation.
- S02-C003: citation needed; PMID=unknown; DOI=unknown; notes=BYLieve alpelisib after CDK4/6 inhibitor exposure.
- S02-C004: citation needed; PMID=unknown; DOI=unknown; notes=Alpelisib combination trials limited by toxicity or lack of efficacy.

### SUB003: Inavolisib And The Clinical Triplet Context

Draft prose:

Inavolisib should be reviewed as a clinically advanced PI3K-alpha inhibitor in a specific regimen, not as generic proof that next-generation inhibitors overcome alpelisib resistance. INAVO120 tested inavolisib with palbociclib and fulvestrant in endocrine-resistant, PIK3CA-mutated HR-positive/HER2-negative advanced breast cancer, and PubMed-indexed reports describe clinically meaningful PFS and OS outcomes. Those data are central to the inhibitor landscape and to combination strategy, but they do not automatically establish a post-alpelisib resistance solution unless the treated population and prior PI3K-alpha inhibitor exposure support that claim. The review should separate four claims: inavolisib efficacy in its studied setting, safety/tolerability versus other inhibitors, mechanistic features of mutant p110-alpha targeting or degradation, and ability to overcome defined resistance mechanisms. Later verification should inspect eligibility, prior adjuvant endocrine therapy, CDK4/6 inhibitor exposure, biomarker testing, adverse events, and whether progression samples define resistance mechanisms. Later stages should convert this subsection into explicit claims, PubMed queries, access checks, and evidence-priority notes. Claim verification should separate direct resistance evidence from background biology, trial context, and plausible but unproven combination rationale.

Citation/search notes:

- S03-C001: Overall survival with inavolisib in PIK3CA-mutated advanced breast cancer; PMID=40454641; DOI=unknown; notes=INAVO120 mature OS and safety anchor.
- S03-C002: FDA approval summary for inavolisib with palbociclib and fulvestrant; PMID=40845250; DOI=10.1200/JCO-25-00663; notes=PubMed-indexed approval summary and regimen details.
- S03-C003: Inavolisib review in HR-positive/HER2-negative breast cancer; PMID=42496151; DOI=10.1080/17425255.2026.2710110; notes=Background review only; not primary resistance evidence.
- S03-C004: citation needed; PMID=unknown; DOI=unknown; notes=Primary mechanistic paper on inavolisib degradation or selectivity.

### SUB004: STX-478, RLY-2608, And Mutant-Selective Hypotheses

Draft prose:

STX-478 and RLY-2608 are important because they ask whether inhibitor design can improve the therapeutic index or overcome specific resistance mutations. A mutant-selective or allosteric inhibitor might spare wild-type PI3K-alpha biology, reduce hyperglycemia, allow deeper pathway suppression, or retain potency against secondary mutations that impair orthosteric inhibitors. Those are distinct hypotheses requiring different evidence: biochemical selectivity, cellular pharmacodynamics, animal tolerability, clinical dose exposure, and acquired-resistance models. The initial draft should avoid implying that investigational agents have already solved clinical resistance. Later PubMed retrieval should search both name variants and broader terms such as allosteric PI3K-alpha inhibitor and mutant-selective PI3K-alpha inhibitor. Full text is likely required because abstracts may not specify binding mode, mutation panels, clinical dose relevance, or whether models represent acquired resistance after PI3K-alpha inhibitor exposure. Later stages should convert this subsection into explicit claims, PubMed queries, access checks, and evidence-priority notes. Claim verification should separate direct resistance evidence from background biology, trial context, and plausible but unproven combination rationale.

Citation/search notes:

- S04-C001: citation needed; PMID=unknown; DOI=unknown; notes=STX-478 mutant-selective PI3K-alpha inhibitor discovery and resistance-relevant data.
- S04-C002: citation needed; PMID=unknown; DOI=unknown; notes=RLY-2608 allosteric or mutant-selective inhibitor discovery and resistance-relevant data.
- S04-C003: citation needed; PMID=unknown; DOI=unknown; notes=Preprint or early report comparing mutant-selective inhibitors against secondary PIK3CA mutations.
- S04-C004: citation needed; PMID=unknown; DOI=unknown; notes=Early clinical trial publication or abstract for RLY-2608 or STX-478 if PubMed-indexed.

### SUB005: PTEN Loss And p110-beta Compensation

Draft prose:

PTEN loss is a central resistance candidate because it can restore downstream pathway signaling despite PI3K-alpha inhibition. The strongest draft anchor is the patient-derived BYL719 resistance study in which metastatic lesions evolved convergent PTEN loss after response, with functional work supporting resistance and reversal through p110-beta blockade. This is unusually direct evidence because it links treatment exposure, progression, tumor evolution, and model-based rescue. Verification should still avoid making PTEN loss universal. Baseline PTEN loss, acquired PTEN loss, PTEN protein suppression, and post-translational PTEN inactivation are different evidence classes. A resistance claim should specify whether PTEN alteration appears after therapy, whether pathway output persists, whether p110-beta or AKT/mTOR signaling is implicated, and whether combination rescue was tested. Patient evidence and model evidence should be presented separately. Later stages should convert this subsection into explicit claims, PubMed queries, access checks, and evidence-priority notes. Claim verification should separate direct resistance evidence from background biology, trial context, and plausible but unproven combination rationale.

Citation/search notes:

- S05-C001: Juric et al., convergent loss of PTEN and resistance to PI(3)K-alpha inhibition; PMID=25409150; DOI=10.1038/nature13948; notes=Direct patient-derived and functional resistance anchor.
- S05-C002: citation needed; PMID=unknown; DOI=unknown; notes=Alpelisib-resistant breast cancer model with IGF1R/p110-beta compensation.
- S05-C003: citation needed; PMID=unknown; DOI=unknown; notes=Clinical biomarker analysis linking PTEN status to PI3K-alpha inhibitor outcomes.
- S05-C004: citation needed; PMID=unknown; DOI=unknown; notes=Non-genetic PTEN suppression or PTEN post-translational inactivation under PI3K inhibition.

### SUB006: Secondary PIK3CA Mutations And On-Target Resistance

Draft prose:

Secondary PIK3CA mutations are conceptually attractive because they could directly alter inhibitor binding or kinase regulation. For PI3K-alpha inhibitors, the review should separate acquired secondary mutations from baseline multiple PIK3CA mutations that may instead mark stronger pathway dependence. It should also distinguish orthosteric ATP-competitive inhibitor resistance from sensitivity to allosteric or mutant-selective inhibitors. Later retrieval should search for patient ctDNA, biopsy, and model papers that identify secondary PIK3CA mutations after alpelisib, inavolisib, or related inhibitor exposure. Full text will likely be needed to determine allele phase, baseline absence, timing of emergence, co-occurring PTEN or AKT alterations, and cross-drug sensitivity. Claims about RLY-2608 overcoming secondary PIK3CA mutations should be narrow unless supported by clinical post-progression evidence. Later stages should convert this subsection into explicit claims, PubMed queries, access checks, and evidence-priority notes. Claim verification should separate direct resistance evidence from background biology, trial context, and plausible but unproven combination rationale.

Citation/search notes:

- S06-C001: citation needed; PMID=unknown; DOI=unknown; notes=Patient-derived acquired secondary PIK3CA mutation paper after PI3K-alpha inhibitor exposure.
- S06-C002: citation needed; PMID=unknown; DOI=unknown; notes=Structural or biochemical paper on secondary PIK3CA mutations and orthosteric inhibitor binding.
- S06-C003: citation needed; PMID=unknown; DOI=unknown; notes=Allosteric inhibitor activity against secondary PIK3CA resistance mutations.
- S06-C004: citation needed; PMID=unknown; DOI=unknown; notes=Baseline multiple PIK3CA mutation clonality and PI3K inhibitor sensitivity.

### SUB007: AKT/mTOR Output Persistence

Draft prose:

Some resistant tumors may escape PI3K-alpha inhibition by maintaining signaling downstream of PI3K. This can involve activating AKT alterations, p110-beta-driven AKT reactivation, mTORC1 activation, nutrient-sensing pathway alterations, or feedback loops that preserve pS6 and p4E-BP1 even when pAKT is suppressed. The key review task is to avoid treating all pathway rebound as the same mechanism. Verification should require timing and perturbation. A claim that AKT/mTOR compensation mediates resistance should show drug exposure, persistent or rebounding pathway output, and ideally genetic or pharmacologic rescue. Combination trials with AKT or mTOR inhibitors should be interpreted carefully: clinical benefit of a combination can support pathway rationale, but it does not prove the combination overcame acquired PI3K-alpha inhibitor resistance unless prior exposure and resistance context are explicit. Later stages should convert this subsection into explicit claims, PubMed queries, access checks, and evidence-priority notes. Claim verification should separate direct resistance evidence from background biology, trial context, and plausible but unproven combination rationale.

Citation/search notes:

- S07-C001: citation needed; PMID=unknown; DOI=unknown; notes=AKT1 activating mutations emerging with PI3K-alpha inhibitor resistance.
- S07-C002: citation needed; PMID=unknown; DOI=unknown; notes=mTORC1 regulator loss causing PI3K-alpha inhibitor resistance.
- S07-C003: citation needed; PMID=unknown; DOI=unknown; notes=PI3K-alpha plus AKT or mTOR inhibitor combination trial relevant to resistance.
- S07-C004: citation needed; PMID=unknown; DOI=unknown; notes=Pharmacodynamic paper measuring pAKT, pS6, or p4E-BP1 under PI3K-alpha inhibition.

### SUB008: RTK, HER-family, IGF1R, And MAPK/ERK Bypass

Draft prose:

Bypass signaling is likely to be one of the broadest resistance categories. Receptor tyrosine kinases can restore PI3K pathway signaling, activate MAPK/ERK, or create parallel survival circuits when PI3K-alpha is inhibited. HER-family signaling, EGFR, IGF1R, FGFR, c-MET, and other RTKs should be considered only when linked to PI3K-alpha inhibitor exposure, pathway rebound, reduced sensitivity, or combination rescue. The review must distinguish evidence from breast cancer, colorectal cancer, head and neck cancer, and other tumor models. Pan-PI3K or dual PI3K/mTOR studies can inform biology, but they should not be silently substituted for alpha-selective inhibitor evidence. Later stages should retrieve studies that test PI3K-alpha inhibitors with HER2, EGFR, IGF1R, MEK, ERK, or SHP2 blockade and should classify whether the evidence is direct resistance, combination rationale, or background crosstalk. Later stages should convert this subsection into explicit claims, PubMed queries, access checks, and evidence-priority notes. Claim verification should separate direct resistance evidence from background biology, trial context, and plausible but unproven combination rationale.

Citation/search notes:

- S08-C001: citation needed; PMID=unknown; DOI=unknown; notes=HER-family or RTK activation after PI3K pathway inhibition in breast cancer.
- S08-C002: citation needed; PMID=unknown; DOI=unknown; notes=IGF1R/p110-beta compensation in alpelisib-resistant breast cancer cells.
- S08-C003: citation needed; PMID=unknown; DOI=unknown; notes=MAPK/ERK bypass after PI3K-alpha or PI3K pathway inhibition.
- S08-C004: citation needed; PMID=unknown; DOI=unknown; notes=Clinical trial combining PI3K-alpha inhibitor with HER2, EGFR, MEK, ERK, or RTK-targeted therapy.

### SUB009: Endocrine Therapy Crosstalk And Prior CDK4/6 Exposure

Draft prose:

Most approved clinical use of PI3K-alpha inhibition sits inside endocrine-resistant HR-positive breast cancer, so endocrine biology is not background noise. ESR1 alterations, ER signaling adaptation, CDK4/6 inhibitor exposure, and endocrine partner choice can change the meaning of response and progression. A tumor progressing on alpelisib plus fulvestrant may reflect PI3K-alpha escape, endocrine resistance, or both. Clinical trial interpretation should therefore track prior therapy and regimen. SOLAR-1, BYLieve, INAVO120, and related studies differ in population, prior CDK4/6 exposure, treatment line, endocrine partner, and combination design. Later claim verification should reject cross-trial comparisons that ignore these differences. Full text is likely required for eligibility, subgroup results, and sequencing details. Later stages should convert this subsection into explicit claims, PubMed queries, access checks, and evidence-priority notes. Claim verification should separate direct resistance evidence from background biology, trial context, and plausible but unproven combination rationale.

Citation/search notes:

- S09-C001: Andre et al., SOLAR-1 alpelisib plus fulvestrant; PMID=31091374; DOI=10.1056/NEJMoa1813904; notes=Endocrine-resistant advanced breast cancer anchor.
- S09-C002: citation needed; PMID=unknown; DOI=unknown; notes=BYLieve cohort A or other post-CDK4/6 alpelisib report.
- S09-C003: Overall survival with inavolisib in PIK3CA-mutated advanced breast cancer; PMID=40454641; DOI=unknown; notes=Inavolisib triplet trial context.
- S09-C004: citation needed; PMID=unknown; DOI=unknown; notes=ESR1 or endocrine-resistance alterations during PI3K-alpha inhibitor therapy.

### SUB010: Heterogeneity, Clonal Selection, And Patient-Derived Evidence

Draft prose:

Resistance in patients may not follow one linear pathway. Separate metastatic lesions can evolve distinct genetic solutions; ctDNA can reveal convergent pathway alterations; and baseline subclones may expand under therapy. This is one reason patient-derived evidence should be weighted heavily when available. A mechanism seen in a cell line becomes more compelling when paired with temporal patient sampling and functional rescue. The review should rank evidence by directness: serial patient specimens and resistance-selected models are stronger than untreated tumor profiling; single-patient rapid autopsy can be mechanistically rich but not prevalence-estimating; ctDNA cohorts can show recurrence but may miss spatial heterogeneity. Later stages should preserve uncertainty about how common each mechanism is and whether mechanisms differ across breast cancer, gynecologic cancer, colorectal cancer, and other tumors. Later stages should convert this subsection into explicit claims, PubMed queries, access checks, and evidence-priority notes. Claim verification should separate direct resistance evidence from background biology, trial context, and plausible but unproven combination rationale.

Citation/search notes:

- S10-C001: Juric et al., convergent PTEN loss under BYL719 pressure; PMID=25409150; DOI=10.1038/nature13948; notes=Rapid autopsy and convergent-evolution anchor.
- S10-C002: citation needed; PMID=unknown; DOI=unknown; notes=Serial ctDNA cohort after alpelisib or inavolisib progression.
- S10-C003: citation needed; PMID=unknown; DOI=unknown; notes=Patient-derived organoid or xenograft study modeling PI3K-alpha resistance.
- S10-C004: citation needed; PMID=unknown; DOI=unknown; notes=Review or primary source on tumor heterogeneity under targeted therapy pressure.

### SUB011: Reading Successful, Failed, And Combination Trials

Draft prose:

The user specifically wants clinical trial papers across phases, including successful and failed studies. This is essential because a trial can teach different things depending on its design. A positive trial can establish benefit in a defined biomarker and regimen context; a negative trial can reveal toxicity, inadequate target suppression, wrong population, weak combination partner, or insufficient biomarker selection; a failed trial does not automatically reveal a resistance mechanism. Combination trials should be categorized by rationale. Some combinations aim to improve endocrine control, some address cell-cycle escape, some target pathway rebound, and some attempt vertical or parallel pathway blockade. Later retrieval should extract phase, regimen, population, prior therapy, endpoint, biomarker criteria, adverse events, and stated biological rationale. Claim verification should treat “designed to overcome resistance” as a claim requiring trial text or mechanistic support. Later stages should convert this subsection into explicit claims, PubMed queries, access checks, and evidence-priority notes. Claim verification should separate direct resistance evidence from background biology, trial context, and plausible but unproven combination rationale.

Citation/search notes:

- S11-C001: Andre et al., SOLAR-1 primary report; PMID=31091374; DOI=10.1056/NEJMoa1813904; notes=Positive approved-agent trial anchor.
- S11-C002: FDA approval summary for inavolisib with palbociclib and fulvestrant; PMID=40845250; DOI=10.1200/JCO-25-00663; notes=Combination clinical context.
- S11-C003: citation needed; PMID=unknown; DOI=unknown; notes=Failed or negative PI3K-alpha inhibitor trial with interpretable rationale.
- S11-C004: citation needed; PMID=unknown; DOI=unknown; notes=Trial combining PI3K-alpha inhibition with endocrine, CDK4/6, HER2, MEK/ERK, AKT, or mTOR inhibition.

### SUB012: Biomarkers And Practical Resistance Taxonomy

Draft prose:

A useful final review should organize resistance mechanisms into a practical taxonomy rather than a long list. One axis is timing: intrinsic resistance, adaptive early escape, and acquired resistance after initial benefit. A second axis is evidence type: patient-derived, trial-translational, resistance-selected model, perturbation/rescue model, or background-only rationale. A third axis is therapeutic implication: switch PI3K-alpha inhibitor class, add vertical pathway blockade, target bypass RTKs or MAPK, alter endocrine partner, manage toxicity to sustain exposure, or pursue non-PI3K strategies. Biomarkers should be handled with special caution. A biomarker may identify eligibility, predict benefit, mark resistance, or merely correlate with poor prognosis. PTEN loss, AKT1 alterations, ESR1 changes, RTK expression, pAKT rebound, pS6 persistence, and ctDNA dynamics may each have different evidentiary strength. Later claim verification should force each biomarker statement to specify disease context, inhibitor, specimen type, timing, endpoint, and whether the evidence is predictive, prognostic, mechanistic, or exploratory. Later stages should convert this subsection into explicit claims, PubMed queries, access checks, and evidence-priority notes. Claim verification should separate direct resistance evidence from background biology, trial context, and plausible but unproven combination rationale.

Citation/search notes:

- S12-C001: Genomic determinants of response to alpelisib plus fulvestrant in SOLAR-1; PMID=41967638; DOI=10.1016/j.annonc.2026.04.003; notes=Biomarker subgroup and co-alteration anchor.
- S12-C002: Extended spectrum of PIK3CA mutations detected in breast carcinoma; PMID=36321996; DOI=unknown; notes=Biomarker testing and mutation-spectrum anchor.
- S12-C003: citation needed; PMID=unknown; DOI=unknown; notes=ctDNA monitoring or serial sampling method paper relevant to PI3K-alpha resistance.
- S12-C004: citation needed; PMID=unknown; DOI=unknown; notes=Mechanism taxonomy review for PI3K inhibitor resistance, to be verified with primary sources.
