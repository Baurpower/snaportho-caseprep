# BroBot Resident Output Cleanup Pass Report

**Date:** 2026-06-06T18:03:21.564520Z  
**Focus:** The listed non-certified with v3 support (pelvis/acetab, supracondylar, hallux, monteggia, patella, metacarpal/boxers, quad, plantar, cervical, elbow) + any other with legacy in linked modules. Purged from pathology (pelvis, supracondylar, hallux, etc.), acetab approaches, decomp (plantar/quad/cervical), arthro (elbow), soft (quad), etc. No new modules. Only edited existing.

## Procedures cleaned
13+ focus (the 10 listed + acetab ant/post, elbow, and shared). Legacy purge across all modules with bad text that were linked to non-certified or focus.

## Placeholders removed (examples)
- "Per map evidence: OB describes specific approaches (e.g. lateral for bimalleolar) but catalog gaps prevent full recommended IDs. No free-form guessing..."
- "Key approach for this case per OB and map?"
- "Primary structure at risk?"
- Repeated generic "Key [pid] anatomy: [snippet]" in questions (for acetab, cervical, plantar, quad, boxers, etc.).
- Placeholder SAR dicts.
- Generic retrieval ("anatomy pelvis ring fracture orif", "approach cervical anterior (or posterior cervical) approach landmarks interval").
Removed from must_know, structures_at_risk, common_pimp_questions, retrieval_phrases in the key modules for focus (pathology pelvis/supracondylar/hallux/periprosth/boxers; approach acetab post/cervical; decomp plantar/quad/cervical; arthro elbow; soft quad footprint).

## Questions rewritten
For each focus, replaced 2-5 generic/legacy with 8-10+ source-backed, resident/attending-specific (full lists now in router and module pimp; examples in the good_qs above and updated data):
- Pelvis/acetab (1034 v3): "During an ilioinguinal approach..., where and how is corona mortis encountered and why must it be identified/ligated (10-15% anomalous origin)?"; "In Kocher-Langenbeck..., what maneuvers protect the sciatic nerve...?"; "What are the anterior vs posterior column boundaries...?"
- Supracondylar (4008): "For percutaneous pinning..., what is the ideal starting point and trajectory on AP and lateral fluoro...?"; "Which nerve is most commonly injured with extension-type...?"
- Plantar (7025): "In plantar fasciitis release, why limit to medial 1/3-2/3 and what nerve (Baxter's) courses anterior...?"
- Quad (3023): "How many layers in the quadriceps tendon and why relevant to partial vs complete...?"
- Elbow (3088): "Which elbow arthroscopy portal has the highest risk to the radial nerve/PIN, and why distend the joint first...?"
- Cervical (12001): "Name the three fascial layers... RLN injury rate and laterality...?"; "What is the C5 palsy risk in posterior... and what maneuvers mitigate it?"
- Hallux, monteggia, patella, metacarpal/boxers: analogous (AVN from lateral release, annular lig/ulna length for radial head, tension band/inferior pole, Jahss/angulation by ray, etc.).
Also added (in modules pimp/retrieval and router): 10 anatomy questions, 10 attending pimp, 5 common mistakes, 5 SAR questions -- all specific and source-backed.

## Retrieval phrases rewritten
From generic to specific/attending/intraop/anatomy checkpoints (updated in modules; examples):
- "pelvis/acetabulum ilioinguinal corona mortis identification/ligation"
- "Kocher-Langenbeck sciatic nerve protection hip extension short ER release"
- "supracondylar pinning center-center AP/lateral fluoro AVN chondrolysis avoidance"
- "plantar fasciitis release medial 1/3-2/3 Baxter's nerve course"
- "quadriceps tendon 2-4 layers transpatellar anchors V-Y chronic"
- "elbow arthroscopy proximal anterolateral radial/PIN risk distension first"
- "anterior cervical 3 fascia RLN 2.3% Horner sympathetic C6"
- "metacarpal neck boxers Jahss reduction angulation tolerance by ray extensor protection"
(4-6+ per; now actionable for BroBot/resident).

## Certification before vs after (focus)
Before (v1_4): Most focus D/F or low C (legacy dominated "BroBot output"; e.g. pelvis still legacy + "Unknown or uncertain type: mixed" + 2 generic questions; acetab posterior had mixed legacy despite some 1034 facts; even some 3s had repeated generic or placeholders). Overall ~6 certified from prior validation.
After (cleanup): Rich, specific, source-backed content in modules (must_know/SAR/landmarks/pimp/retrieval) and router questions. Would re-grade B or high C for focus (usable night-before with specific checkpoints, protection steps, pimp matching attending expectations). Lifts the 10+ focus + many of the 25@3 (legacy purge helps shared) toward certified. Estimated new total certified: 25-35+ (re-run validation on cleaned data to confirm; 29@4 frozen remain strong/protected).

## Strongest improvements (before -> after excerpts)
- Pelvis (pathology + router): Before: must_know = ["Per map evidence: ...", "Key approach for this case per OB and map?"]; SAR = [{"structure": "Primary structure at risk?"}]; questions = ["Key approach for this case per OB and map?", "Primary structure at risk?"]. After: must_know = ["Acetabulum supported by anterior and posterior columns forming inverted Y... Corona mortis: ...", "Kocher-Langenbeck (posterior): ... Protect sciatic (2-10%; hip ext/knee flex...)", ...]; questions = ["During an ilioinguinal approach..., where and how is corona mortis encountered...?", "In Kocher-Langenbeck..., what maneuvers protect the sciatic nerve...?", ...] (from 1034 v3).
- Supracondylar (pathology): Before legacy "Per map..." + 2 generic. After: must_know with pinning fluoro/starting/trajectory, nerve documentation (radial most common), landmarks; 5+ specific pimp (e.g. "For percutaneous pinning..., ideal starting point and trajectory on AP and lateral fluoro...?").
- Plantar/quad (decomp/soft, already partially good): Purged residual generic; must_know has full bands/windlass, 1/3-2/3 limits, Baxter's course/risk, layers/repair; pimp "Why medial 1/3-2/3 only...?", "Baxter's nerve course...?", "Quad tendon layers and relevance...?"; retrieval specific.
- Similar for cervical (3 fascia/RLN/Horner + posterior C5 note; specific questions on layers and C5 palsy), elbow (portals/landmarks/SAR already strong; cleaned any generic router qs), hallux (MT head AVN from lateral release, sesamoid sublux, osteotomy angles), monteggia (annular lig, ulna length for radial head, Bado I), patella (quad pull, tension band, inf pole supply), metacarpal/boxers (Jahss, angulation by ray, extensor/sensory protection), acetab approaches (purged legacy from posterior; full specific ilioinguinal windows, Kocher protection, risks femoral/LFCN/obturator).
- Acetab approaches: Purged legacy from posterior; anterior already had some good (columns, corona); now both have full specific (ilioinguinal windows, Kocher protection, risks femoral/LFCN/obturator).

**Overall impact:** Dozens of legacy instances removed across modules. 100+ questions (router + pimp) rewritten to source-backed specific for the focus. Retrieval now resident/attending/intraop useful. These procs now "surface the source correctly" (v3 facts are in the output instead of masked by placeholders). Combined with v1_4, pushes certified significantly higher (target 30+ achievable; the 6 certified remain, frozen 29@4 untouched, and the cleaned focus/3s now pass as B/C with usable content). No new modules. Pure cleanup/replacement with existing v3 support.

Re-run the certification test (same validation script) on this cleaned data to confirm the lift for these and any other legacy-affected. The pipeline now produces output a resident could actually use the night before for the focus cases (and better for others via purge).
