# CasePrep missing-indications clinical review packet

**Status:** DRAFT FOR HUMAN CLINICAL REVIEW — NOT CERTIFIED  
**Prepared:** 2026-07-22  
**Scope:** the 24 procedure records reported by `scripts/caseprep/validate_registry.py` as having no `indications` content  
**Intended use:** a clinician-reviewed starting point for concise `modules.json` entries  

This packet does not authorize clinical use, change a certified payload, or represent approval by a physician. The bullets below are deliberately conservative summaries of professional-society guidance and authoritative surgical references. They are not patient-specific recommendations. A qualified orthopaedic reviewer must check the source, the procedure slug, local practice, exclusions, and wording before anyone edits or re-certifies a module.

## How to review

For every procedure, the reviewer should:

- Confirm the proposed bullets describe **indications for the named operation**, not merely the diagnosis.
- Confirm age/skeletal maturity, fracture classification, displacement/stability, soft-tissue status, neurologic/vascular status, functional demand, comorbidity, and failed nonoperative care are represented where material.
- Confirm alternatives and common contraindications are not obscured by an overbroad statement.
- Resolve every item marked **ambiguity**; split or rename the procedure if one slug combines materially different operations.
- Open and read the linked source, record reviewer name/credentials/date, and cite the reviewed edition in the eventual clinical change.
- Require separate content review and certification; do not treat acceptance of this packet as payload certification.

Confidence labels describe confidence that the wording is a reasonable review candidate, **not** strength of evidence or appropriateness for any patient.

---

## Trauma

### `acetabulum_fracture_orif_anterior`

**Proposed indications bullets**

- Displaced acetabular fracture requiring operative reduction where the dominant fracture component is accessible from an anterior approach (for example, anterior-column, anterior-wall, both-column, or selected anterior-column/posterior-hemitransverse patterns).
- Articular incongruity, instability, incarcerated fragments, marginal impaction, or failure to obtain/maintain an acceptable closed reduction, after patient and soft-tissue factors are considered.

**Sources**

- [AO Surgery Reference — decision making: choice of exposure](https://surgeryreference.aofoundation.org/orthopedic-trauma/adult-trauma/acetabulum/further-reading/decision-making-choice-of-exposure)
- [AO Surgery Reference — anterior-column/posterior-hemitransverse ORIF through ilioinguinal approach](https://surgeryreference.aofoundation.org/orthopedic-trauma/adult-trauma/acetabulum/anterior-column-and-posterior-hemitransverse/orif-through-ilioinguinal-approach)

**Confidence / ambiguities:** Moderate. Approach selection is fracture-pattern- and surgeon-dependent; “anterior” may mean ilioinguinal, anterior intrapelvic/modified Stoppa, or combined windows. A pelvic/acetabular trauma surgeon should define which patterns this module actually teaches.

**Reviewer checklist:** □ define approach family □ define displacement/congruity threshold used locally □ distinguish combined approaches □ check elderly/fragility-fracture pathways □ confirm no implication that every anterior pattern needs ORIF

### `acetabulum_fracture_orif_posterior`

**Proposed indications bullets**

- Displaced posterior-wall or posterior-column acetabular fracture, or selected transverse/associated patterns, requiring direct posterior visualization and stable fixation.
- Hip instability, articular incongruity, incarcerated fragments, marginal impaction, or failure to obtain/maintain an acceptable reduction, after patient and soft-tissue factors are considered.

**Sources**

- [AO Surgery Reference — decision making: Kocher-Langenbeck indications](https://surgeryreference.aofoundation.org/orthopedic-trauma/adult-trauma/acetabulum/further-reading/decision-making-choice-of-exposure)

**Confidence / ambiguities:** Moderate. The module name should not imply that approach alone determines operative indication. Some transverse and associated patterns need an anterior or combined strategy.

**Reviewer checklist:** □ define instability/incongruity criteria □ confirm posterior wall/column scope □ address femoral-head injury and marginal impaction □ distinguish combined exposure □ review sciatic-nerve and soft-tissue considerations

### `distal_femur_fracture_orif`

**Proposed indications bullets**

- Displaced or unstable distal-femur fracture requiring restoration of articular congruity, limb length, rotation, and mechanical alignment.
- Open fracture, vascular injury, irreducible fracture, or fracture not suitable for acceptable nonoperative management, once damage-control and soft-tissue priorities permit definitive fixation.
- Periprosthetic fracture only if the prosthesis is stable and the fracture pattern/bone stock permit fixation; otherwise use the appropriate revision pathway.

**Sources**

- [AO Surgery Reference — distal femur ORIF compression plate](https://surgeryreference.aofoundation.org/orthopedic-trauma/adult-trauma/distal-femur/extraarticular-fracture-simple/orif-compression-plate)
- [AO Surgery Reference — distal femur fixation principles](https://surgeryreference.aofoundation.org/orthopedic-trauma/adult-trauma/distal-femur/basic-technique/orif-dcs-dynamic-condylar-screw)

**Confidence / ambiguities:** Moderate. “ORIF” does not cover retrograde nailing or minimally invasive bridge plating. The reviewer should decide whether this module is implant-specific or a general operative-fracture module.

**Reviewer checklist:** □ distinguish intra-/extra-articular patterns □ define periprosthetic inclusion □ account for open injury/soft tissues □ separate plating from nailing □ avoid fixed numeric thresholds unsupported by the selected source

### `distal_radius_fracture_orif`

**Proposed indications bullets**

- Acute distal-radius fracture in a non-geriatric adult with unacceptable post-reduction alignment; AAOS/ASSH cites radial shortening greater than 3 mm, dorsal tilt greater than 10°, or intra-articular displacement/step-off greater than 2 mm as parameters associated with improved outcomes from operative treatment.
- Unstable, irreducible, open, articular-rim/shear, or fracture-dislocation pattern when stable acceptable alignment cannot be achieved or maintained nonoperatively.
- In geriatric patients, individualize because operative treatment does not improve long-term patient-reported outcomes over nonoperative treatment on average, despite possible radiographic or early-function differences.

**Sources**

- [AAOS/ASSH — 2020 Management of Distal Radius Fractures CPG fact sheet](https://www.aaos.org/aaos-home/newsroom/press-releases/management-of-distal-radius-fractures-clinical-practice-guidelines-cpg-fact-sheet/)
- [AAOS — Distal Radius Fractures guideline page](https://www.aaos.org/quality/quality-programs/distal-radius-fractures/)

**Confidence / ambiguities:** High for the quoted adult thresholds; moderate for fracture-specific exceptions. “ORIF” should not be used as a synonym for every operative fixation technique.

**Reviewer checklist:** □ preserve age caveat □ confirm post-reduction measurements □ distinguish ORIF from pins/ex-fix □ include patient functional demand □ review open-fracture pathway

### `femoral_shaft_fracture_orif`

**Proposed indications bullets**

- Adult femoral-shaft fracture requiring operative stabilization; most adult shaft fractures are treated surgically after life-threatening conditions are stabilized.
- Open fracture, polytrauma, unstable/displaced pattern, or inability to maintain acceptable length/alignment/rotation nonoperatively.
- Plate ORIF when fracture location/pattern, associated injury, medullary anatomy, existing hardware, or other factors make intramedullary nailing unsuitable.

**Sources**

- [AAOS OrthoInfo — Femoral Shaft Fractures](https://orthoinfo.aaos.org/en/diseases--conditions/femur-shaft-fractures-broken-thighbone/)

**Confidence / ambiguities:** Moderate. The slug says ORIF, while intramedullary nailing is the usual definitive technique for many adult shaft fractures. This likely needs a rename or an explicit plating-only scope.

**Reviewer checklist:** □ decide whether “ORIF” includes IM nail □ define adult/pediatric boundary □ cover damage-control external fixation □ account for open injury □ specify plating-specific indications

### `humeral_shaft_fracture_orif`

**Proposed indications bullets**

- Open humeral-shaft fracture, vascular injury, floating elbow/polytrauma requiring stabilization, pathologic fracture, or inability to obtain/maintain acceptable alignment by functional bracing.
- Symptomatic nonunion or malunion, or selected fracture patterns/patient needs where the expected benefit of fixation outweighs radial-nerve and surgical risks.
- Radial-nerve deficit alone requires pattern- and mechanism-specific assessment; do not present every closed primary palsy as an automatic ORIF indication.

**Sources**

- [AO Surgery Reference — humeral-shaft patient assessment and open-fracture considerations](https://surgeryreference.aofoundation.org/orthopedic-trauma/adult-trauma/humeral-shaft/further-reading/patient-assessment-and-radiology)
- [AAOS OrthoInfo — Humeral Shaft Fractures](https://orthoinfo.aaos.org/en/diseases--conditions/humeral-shaft-fractures)

**Confidence / ambiguities:** Moderate. Operative thresholds vary and many closed fractures heal with functional bracing. A trauma reviewer should refine the nerve-exploration language.

**Reviewer checklist:** □ define acceptable alignment □ review radial-nerve algorithm □ include open/pathologic/nonunion pathways □ account for patient compliance/body habitus □ avoid making surgery routine

### `monteggia_fracture_orif`

**Proposed indications bullets**

- Acute adult Monteggia fracture-dislocation: anatomic reduction and stable fixation of the ulna to restore and maintain radiocapitellar alignment.
- Persistent radial-head dislocation or instability after anatomic ulnar fixation warrants evaluation for ulnar malreduction or interposed annular ligament/capsule and may require direct treatment.

**Sources**

- [AO Surgery Reference — Monteggia ORIF plating](https://surgeryreference.aofoundation.org/orthopedic-trauma/adult-trauma/forearm-shaft/simple-fracture-of-the-ulna-with-dislocation-of-proximal-radioulnar-joint-monteggia/orif-plating)

**Confidence / ambiguities:** High for adult acute injury. Pediatric plastic deformity and chronic/missed Monteggia lesions require different algorithms and should not be silently included.

**Reviewer checklist:** □ declare adult scope □ exclude chronic/pediatric pathways or add them separately □ require radiocapitellar stability check □ confirm ulnar-first sequence □ define open-fracture handling

### `pelvis_ring_fracture_orif`

**Proposed indications bullets**

- Mechanically unstable pelvic-ring injury with displacement or deformity that requires operative stabilization after hemorrhage control and physiologic resuscitation.
- Persistent posterior-ring instability, unacceptable displacement, open pelvic injury, or associated factors that prevent safe mobilization with nonoperative care.
- Choose open versus percutaneous fixation according to ring pattern, reducibility, soft tissues, neurologic injury, patient physiology, and surgeon expertise.

**Sources**

- [AO Surgery Reference — ORIF ilium and unstable hemipelvis](https://surgeryreference.aofoundation.org/orthopedic-trauma/adult-trauma/pelvic-ring/basic-technique/orif-ilium)
- [AO Surgery Reference — pelvic ring module](https://surgeryreference.aofoundation.org/orthopedic-trauma/adult-trauma/pelvic-ring)

**Confidence / ambiguities:** Moderate. “Pelvis ring fracture ORIF” is too broad for one indication list; emergent stabilization, definitive percutaneous fixation, and formal ORIF are distinct.

**Reviewer checklist:** □ map Young–Burgess/AO-OTA patterns □ separate resuscitation from definitive fixation □ define displacement/instability □ address open injury □ distinguish ORIF from percutaneous fixation

### `tibial_shaft_fracture_orif`

**Proposed indications bullets**

- Tibial-shaft fracture requiring operative stabilization because of instability/displacement, open injury, polytrauma, segmental pattern, inability to maintain acceptable alignment, or need for earlier mobilization after individualized risk assessment.
- Plate ORIF for selected reducible simple patterns or when intramedullary nailing is not chosen because of medullary anatomy, existing hardware, fracture extension/location, or other technical constraints.
- Avoid definitive internal fixation through severely compromised or infected soft tissues until an appropriate staged plan is in place.

**Sources**

- [AO Surgery Reference — tibial shaft treatment options and ORIF indications](https://surgeryreference.aofoundation.org/orthopedic-trauma/adult-trauma/tibial-shaft/intact-segmental)
- [AO Surgery Reference — tibial intramedullary nailing principles](https://surgeryreference.aofoundation.org/orthopedic-trauma/adult-trauma/tibial-shaft/basic-technique/infrapatellar-intramedullary-nailing)
- [AO Surgery Reference — open-fracture principles](https://surgeryreference.aofoundation.org/orthopedic-trauma/adult-trauma/tibial-shaft/further-reading/principles-of-management-of-open-fractures)

**Confidence / ambiguities:** Moderate. As with femoral shaft fracture, the ORIF slug risks implying plating where nailing is frequently standard.

**Reviewer checklist:** □ define plating-only scope □ distinguish nail/ex-fix/MIO □ assess soft-tissue envelope □ define alignment criteria □ include infection/contamination staging

---

## Sports, knee, and tendon

### `acl_reconstruction`

**Proposed indications bullets**

- Symptomatic ACL-deficient knee with functional instability in a patient wishing to return to pivoting/cutting sport or work, after shared decision-making about operative and structured nonoperative care.
- Young/active patient or patient with recurrent giving-way, repairable associated meniscal injury, or other intra-articular injury for whom restored stability is important.
- When surgery is indicated for an acute isolated ACL tear, favor reconstruction rather than repair and avoid unnecessary delay; AAOS notes increasing meniscal/cartilage injury risk within 3 months.

**Sources**

- [AAOS — 2022 ACL Injuries CPG overview](https://www.aaos.org/globalassets/quality-and-practice-resources/anterior-cruciate-ligament-injuries/orthoguidelines_infographic_acl-final.pdf)
- [AAOS — ACL Injuries plain-language summary](https://orthoinfo.aaos.org/globalassets/pdfs/pls_acl-injuries_7.28.23.pdf)

**Confidence / ambiguities:** High for instability/activity framing and timing once surgery is chosen. Not every ACL tear requires reconstruction.

**Reviewer checklist:** □ require symptomatic instability/goal alignment □ distinguish skeletally immature technique □ assess concomitant injuries □ avoid universal surgery language □ confirm timing wording

### `meniscus_repair`

**Proposed indications bullets**

- Symptomatic acute meniscal tear with healing potential where repair can preserve functional meniscal tissue.
- Displaced or displacing acute tear, particularly when it restricts knee range of motion, or an acute symptomatic repairable tear for which early intervention may improve repair success.
- Consider after failed nonoperative treatment for selected acute tears; distinguish acute isolated tears from degenerative tears and tears associated with ACL injury.

**Sources**

- [AAOS — 2024 Acute Isolated Meniscal Pathology CPG summary](https://www.aaos.org/aaos-home/newsroom/press-releases/guideline-management-acute-isolated-meniscal-pathology/)
- [AAOS — plain-language summary](https://orthoinfo.aaos.org/globalassets/pdfs/plain-language-summary_meniscus-tears-2024.pdf)

**Confidence / ambiguities:** High for acute isolated repairable tears. The AAOS guideline explicitly does not cover chronic/degenerative tears or concomitant ligament injury.

**Reviewer checklist:** □ define “healing potential” clinically □ identify tear pattern/zone/tissue quality □ separate locked/displaced tears □ exclude degenerative pathway □ address ACL-associated repair separately

### `quadriceps_tendon_repair`

**Proposed indications bullets**

- Complete quadriceps-tendon rupture with loss of extensor-mechanism continuity.
- Large partial tear or symptomatic partial tear associated with tendon degeneration when functional deficit and patient goals favor repair.
- Early repair is generally preferred when surgery is indicated, while chronic/retracted tears may require reconstruction or graft augmentation rather than simple repair.

**Sources**

- [AAOS OrthoInfo — Quadriceps Tendon Tear](https://orthoinfo.aaos.org/diseases--conditions/quadriceps-tendon-tear/)

**Confidence / ambiguities:** High for complete rupture; moderate for partial tears because size, extensor lag, activity, and comorbidity matter.

**Reviewer checklist:** □ document extensor lag/continuity □ distinguish partial vs complete □ define acute vs chronic □ account for tissue quality/systemic disease □ separate repair from reconstruction

---

## Hip and knee arthroplasty

### `hip_hemiarthroplasty`

**Proposed indications bullets**

- Displaced/unstable femoral-neck fracture in an older adult for whom arthroplasty is preferred over fixation and total hip arthroplasty is not the better individualized option.
- Selected impending or completed pathologic femoral-neck/head fracture when durable fixation is unlikely and acetabular replacement is not required.
- Consider prefracture function, cognition, comorbidity, life expectancy, acetabular disease, and complication risk when choosing hemiarthroplasty versus THA.

**Sources**

- [AAOS — Management of Hip Fractures in Older Adults CPG](https://www.aaos.org/globalassets/quality-and-practice-resources/hip-fractures-in-the-elderly/hipfxcpg.pdf)

**Confidence / ambiguities:** High for displaced femoral-neck fracture arthroplasty; moderate for selection of hemiarthroplasty versus THA. Stable/nondisplaced fractures have multiple options.

**Reviewer checklist:** □ specify displaced/unstable fracture □ define THA-selection factors □ assess preinjury function/cognition □ identify pathologic-fracture scope □ exclude routine use for young femoral-neck fracture

### `tha_anterior`

**Proposed indications bullets**

- Symptomatic end-stage hip joint disease (commonly osteoarthritis) with substantial pain and functional limitation despite appropriate nonoperative treatment, when total hip arthroplasty is selected through shared decision-making.
- An anterior approach may be selected based on patient anatomy, surgeon expertise, prior surgery, deformity, and the approach-specific risk/benefit profile; the approach itself is not a separate disease indication.

**Sources**

- [AAOS — 2023 Management of Osteoarthritis of the Hip](https://www.aaos.org/quality/quality-programs/osteoarthritis-of-the-hip/)
- [AAOS — Hip OA CPG overview](https://www.aaos.org/globalassets/quality-and-practice-resources/osteoarthritis-of-the-hip/orthoguidelines_infographic_oah-final.pdf)

**Confidence / ambiguities:** High that anterior and posterior THA share core indications. AAOS finds no preferred approach overall; splitting indication content by approach may create artificial differences.

**Reviewer checklist:** □ confirm underlying diagnoses included □ require symptoms/function and nonoperative trial □ state approach is technique selection □ assess anatomy/prior surgery □ align wording with posterior module

### `tha_posterior`

**Proposed indications bullets**

- Symptomatic end-stage hip joint disease (commonly osteoarthritis) with substantial pain and functional limitation despite appropriate nonoperative treatment, when total hip arthroplasty is selected through shared decision-making.
- A posterior approach may be selected based on patient anatomy, surgeon expertise, prior surgery, deformity, and the approach-specific risk/benefit profile; the approach itself is not a separate disease indication.

**Sources**

- [AAOS — 2023 Management of Osteoarthritis of the Hip](https://www.aaos.org/quality/quality-programs/osteoarthritis-of-the-hip/)
- [AAOS — Hip OA CPG overview](https://www.aaos.org/globalassets/quality-and-practice-resources/osteoarthritis-of-the-hip/orthoguidelines_infographic_oah-final.pdf)

**Confidence / ambiguities:** High. The indications should intentionally match anterior THA unless the product scopes a distinct diagnosis or revision pathway.

**Reviewer checklist:** □ mirror core THA criteria □ avoid claiming approach superiority □ assess instability precautions separately from indications □ identify revision/fracture exclusions □ align with anterior module

### `tka`

**Proposed indications bullets**

- End-stage symptomatic knee joint disease with severe pain or stiffness and meaningful limitation of walking, stairs, transfers, work, or other daily activity despite appropriate nonsurgical treatment.
- Structural joint damage consistent with symptoms and examination, after shared decision-making confirms that expected benefit outweighs operative risk.
- Consider deformity, instability, inflammatory arthritis, osteonecrosis, prior surgery, patient goals, medical optimization, and whether a partial or joint-preserving operation is more appropriate.

**Sources**

- [AAOS OrthoInfo — Total Knee Replacement: when surgery is recommended](https://orthoinfo.aaos.org/en/treatment/total-knee-replacement)
- [AAOS — Surgical Management of Osteoarthritis of the Knee guideline listing](https://www.aaos.org/quality/quality-programs/clinical-practice-guidelines/)

**Confidence / ambiguities:** High for symptom/function/nonoperative-care framing; moderate for the full set of diagnoses because the registry module’s intended scope is unclear.

**Reviewer checklist:** □ require symptom/radiograph concordance □ document failed appropriate nonsurgical care □ evaluate UKA/osteotomy alternatives □ include shared decision/optimization □ define inflammatory/post-traumatic inclusion

---

## Shoulder arthroplasty

### `reverse_shoulder_arthroplasty`

**Proposed indications bullets**

- Painful cuff-tear arthropathy or irreparable massive rotator-cuff tear with loss of shoulder function after appropriate nonsurgical treatment.
- Selected complex proximal-humerus fracture, failed prior shoulder arthroplasty, chronic dislocation, tumor, or glenoid deformity/bone loss when reverse mechanics and fixation are appropriate.
- Confirm a functioning deltoid/axillary nerve and adequate reconstructable bone; distinguish primary arthritis with intact cuff from classic cuff-deficient indications.

**Sources**

- [AAOS OrthoInfo — Reverse Total Shoulder Replacement candidates](https://orthoinfo.aaos.org/en/treatment/reverse-total-shoulder-replacement)
- [AAOS — 2020 Glenohumeral Joint Osteoarthritis CPG](https://www.aaos.org/globalassets/quality-and-practice-resources/glenohumeral/glenohumeral-joint-osteoarthritis-3-18-20.pdf)

**Confidence / ambiguities:** High for cuff-tear arthropathy/irreparable cuff; moderate for expanded indications, which are evolving and diagnosis-specific.

**Reviewer checklist:** □ confirm deltoid/axillary function □ define fracture and revision scope □ assess glenoid bone stock □ distinguish intact-cuff OA controversy □ verify failed conservative care

### `total_shoulder_arthroplasty`

**Proposed indications bullets**

- Symptomatic end-stage glenohumeral arthritis with substantial pain and functional limitation despite appropriate nonsurgical treatment, with an intact or reparable rotator cuff suitable for anatomic total shoulder arthroplasty.
- Selected inflammatory or post-traumatic arthropathy when anatomy, cuff function, glenoid bone stock, and patient factors support an anatomic implant.
- Do not use anatomic TSA wording for an irreparable cuff tear/cuff-tear arthropathy; evaluate reverse arthroplasty instead.

**Sources**

- [AAOS — 2020 Glenohumeral Joint Osteoarthritis CPG](https://www.aaos.org/globalassets/quality-and-practice-resources/glenohumeral/glenohumeral-joint-osteoarthritis-3-18-20.pdf)
- [AAOS — Appropriate Use Criteria for shoulder OA](https://www.aaos.org/aaos-home/newsroom/press-releases/aaos-releases-new-appropriate-use-criteria)

**Confidence / ambiguities:** High for primary OA with intact/reparable cuff; moderate for other arthropathies.

**Reviewer checklist:** □ verify cuff reparability □ assess glenoid morphology/bone stock □ document failed nonsurgical care □ distinguish reverse/hemiarthroplasty □ define non-OA diagnoses

---

## Foot and ankle

### `hallux_valgus_correction`

**Proposed indications bullets**

- Painful hallux-valgus deformity causing difficulty with footwear, walking, or activity despite appropriate shoe modification and other nonsurgical measures.
- Progressive symptomatic deformity with transfer symptoms or associated lesser-toe problems when clinical and weight-bearing radiographic findings support corrective surgery.
- Do not offer correction solely for cosmetic appearance; in adolescents, reserve surgery for severe persistent pain and generally defer until near skeletal maturity because recurrence risk is higher.

**Sources**

- [AAOS OrthoInfo — Bunions / when to consider surgery](https://orthoinfo.aaos.org/en/diseases--conditions/bunions/)

**Confidence / ambiguities:** High for painful failed-conservative-care indication. Procedure choice depends on deformity severity, first-ray stability, arthritis, and skeletal maturity.

**Reviewer checklist:** □ require pain/function, not cosmesis □ review weight-bearing imaging □ document nonsurgical trial □ assess first-MTP arthritis/hypermobility □ apply adolescent caveat

### `lateral_ankle_ligament_repair`

**Proposed indications bullets**

- Chronic symptomatic lateral ankle instability with recurrent sprains/giving way, objective instability, and persistent pain or functional limitation after months of structured rehabilitation, bracing, and activity modification.
- Selected acute injury only when associated pathology or instability creates a specific operative indication; nearly all isolated low ankle sprains, including many grade-3 tears, begin with nonoperative care.
- Choose direct repair versus reconstruction according to tissue quality, generalized laxity, prior surgery, alignment, and associated osteochondral/tendon pathology.

**Sources**

- [AAOS OrthoInfo — Sprained Ankle](https://orthoinfo.aaos.org/en/diseases--conditions/sprained-ankle/)

**Confidence / ambiguities:** High for chronic instability after failed rehabilitation. Repair and reconstruction should not be conflated.

**Reviewer checklist:** □ document mechanical and functional instability □ confirm adequate rehab □ assess cavovarus/laxity □ identify associated lesions □ distinguish repair from graft reconstruction

### `plantar_fasciitis_release`

**Proposed indications bullets**

- Persistent, function-limiting plantar-fasciitis pain after at least 12 months of correctly performed, aggressive nonsurgical treatment and confirmation that plantar fasciitis is the pain generator.
- Consider only after excluding competing causes of heel pain and discussing risks including arch change, lateral-column pain, nerve injury, persistent pain, and the limited need for surgery.

**Sources**

- [AAOS OrthoInfo — Plantar Fasciitis and Bone Spurs](https://orthoinfo.aaos.org/en/diseases--conditions/plantar-fasciitis-and-bone-spurs)

**Confidence / ambiguities:** High for the 12-month conservative-care criterion. The module should specify partial release and avoid implying that a heel spur itself is an indication.

**Reviewer checklist:** □ verify diagnosis/exclude nerve or stress injury □ document ≥12 months care □ list treatments actually tried □ specify partial release □ ensure heel spur is not treated as causal

---

## Pediatrics

### `scfe_pinning`

**Proposed indications bullets**

- Diagnosed stable slipped capital femoral epiphysis: percutaneous in-situ screw fixation is the recommended standard, particularly for mild-to-moderate slips.
- Diagnosed unstable SCFE requires urgent specialist stabilization with meticulous handling; operative strategy is individualized because avascular-necrosis risk is high.
- Consider prophylactic contralateral pinning for selected high-risk patients (for example endocrinopathy, renal disease, prior radiation, marked skeletal immaturity, or unreliable follow-up) after explicit risk/benefit discussion.

**Sources**

- [POSNA Study Guide — Slipped Capital Femoral Epiphysis](https://posna.org/physician-education/study-guide/scfe-%28slipped-capital-femoral-epiphysis%29)

**Confidence / ambiguities:** High for stable-slip in-situ fixation; moderate for unstable and prophylactic strategies, where practice varies. The existing module reportedly mentions modified Dunn; pinning and open realignment should not share one indication bullet without clear separation.

**Reviewer checklist:** □ classify stable/unstable □ grade slip severity □ avoid forceful reduction language □ define prophylactic criteria □ separate modified Dunn pathway

### `supracondylar_humerus_fracture_pediatric`

**Proposed indications bullets**

- Displaced pediatric supracondylar humerus fracture requiring reduction and percutaneous pin fixation to restore and maintain alignment.
- Open fracture, irreducible fracture, or fracture with vascular/nerve compromise requiring exploration is an indication for open reduction as clinically appropriate.
- Nondisplaced/stable fractures are generally treated nonoperatively and should not be presented as routine pinning indications.

**Sources**

- [AAOS — Pediatric Supracondylar Humerus Fractures guideline page](https://www.aaos.org/quality/quality-programs/pediatric-supracondylar-humerus-fractures/)
- [AAOS OrthoInfo — Elbow Fractures in Children](https://orthoinfo.aaos.org/diseases--conditions/elbow-fractures-in-children/)

**Confidence / ambiguities:** High at the displaced-versus-stable level. The reviewer should map exact Gartland/flexion-type and perfusion scenarios to the current AAOS AUC/CPG.

**Reviewer checklist:** □ record Gartland/flexion classification □ document perfusion and nerve exam □ distinguish CRPP from ORIF □ define urgent vascular pathway □ exclude nondisplaced fractures

---

## Spine

### `posterior_lumbar_decompression_fusion`

**Proposed indications bullets**

- Lumbar neural compression producing concordant radiculopathy or neurogenic claudication that persists despite appropriate nonoperative care, when decompression is indicated and clinically meaningful instability, deformity, spondylolisthesis, or expected iatrogenic instability supports adding fusion.
- Progressive neurologic deficit or cauda-equina syndrome may require urgent decompression; fusion is added only when the stability/reconstruction indication is independently established.
- Axial back pain or stenosis without instability should not automatically be treated with fusion.

**Sources**

- [AAOS OrthoInfo — Adult Spondylolisthesis of the Low Back](https://orthoinfo.aaos.org/en/diseases--conditions/adult-spondylolisthesis-in-the-low-back/)
- [AAOS OrthoInfo — PLIF and TLIF](https://orthoinfo.aaos.org/en/treatment/spinal-fusion-plif-tlif/)
- [AAOS position statement — spinal arthrodesis expertise and safety](https://www.aaos.org/globalassets/about/position-statements/position-statement-on-arthrodesis-of-the-spine-by-the-non-spine-surgeon.pdf)

**Confidence / ambiguities:** Moderate. This slug combines two decisions—decompression and fusion—and may cover stenosis, degenerative or isthmic spondylolisthesis, deformity, revision, or other diagnoses. Those should be separated or explicitly scoped by a spine surgeon.

**Reviewer checklist:** □ establish symptom/imaging concordance □ document nonoperative care or urgency □ state independent fusion indication □ distinguish degenerative/isthmic/deformity □ exclude nonspecific back pain alone

---

## Cross-procedure reviewer sign-off (not certification)

Complete only after all 24 sections are reviewed:

- Reviewer name and credentials: ______________________________
- Specialty/subspecialty: _____________________________________
- Date: ______________________________________________________
- Sources opened and edition/currentness checked: □ yes □ no
- All ambiguities resolved or assigned: □ yes □ no
- Procedure names match proposed indication scope: □ yes □ no
- Contraindications/alternatives reviewed for misleading omission: □ yes □ no
- Approved as a proposal for module editing (not clinical certification): □ yes □ no
- Required changes / exclusions:

  ______________________________________________________________________

  ______________________________________________________________________

## Suggested next workflow

1. Assign each section to the appropriate fellowship-trained reviewer (trauma, sports, adult reconstruction, shoulder/elbow, foot/ankle, pediatrics, spine).
2. Resolve slug scope first; several “ORIF” records are broader than the likely standard fixation method.
3. Convert only approved bullets into `modules.json` on a separate clinical-content branch.
4. Run schema/registry tests and produce a transparent diff.
5. Obtain independent clinical content review and then use the project’s established certification process. Do not regenerate hashes as a substitute for review.
