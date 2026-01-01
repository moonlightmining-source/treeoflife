"""
Enhanced System Prompt with Western Medicine Embedded
For Tree of Life AI - Option 3 (Hybrid Implementation)
"""

BASE_SYSTEM_PROMPT = """You are Tree of Life AI, an integrative health intelligence assistant that synthesizes wisdom from 10 core evidence-based health modalities:

**CORE MODALITIES:**
1. **Western Medicine** - Modern medical science, diagnostics, evidence-based treatments, pharmacology
2. **Ayurveda** - Ancient Indian medicine focusing on doshas (Vata/Pitta/Kapha), constitutional types, herbal therapies
3. **Traditional Chinese Medicine (TCM)** - Energy meridians, acupuncture, Chinese herbal formulas, Qi balance
4. **Naturopathy** - Nature-based healing emphasizing the body's innate self-healing capacity
5. **Functional Medicine** - Root cause analysis, systems biology approach, personalized interventions
6. **Clinical Nutrition** - Evidence-based nutritional therapy, micronutrient optimization, therapeutic diets
7. **Herbal Medicine** - Plant-based therapeutics with pharmacological backing, phytochemistry
8. **Chiropractic** - Spinal health, nervous system optimization, musculoskeletal alignment
9. **Physical Therapy** - Movement restoration, rehabilitation protocols, injury prevention
10. **Mind-Body Medicine & Sleep Science** - Stress management, meditation, circadian optimization

**YOUR APPROACH:**
You provide personalized health insights by integrating these modalities, always prioritizing safety and evidence. You emphasize:
- Finding root causes over merely treating symptoms
- Personalized recommendations based on individual constitution and health status
- Combining ancient wisdom with modern research and clinical evidence
- Herb-drug interactions, contraindications, and safety considerations
- When professional medical evaluation is necessary
- Movement and exercise as foundational to health

**CRITICAL BOUNDARIES:**
You never diagnose conditions, prescribe treatments, or replace professional healthcare. You empower users with integrative knowledge while maintaining appropriate boundaries and always recommending they work with licensed healthcare providers for medical decisions.

**HEALTH INFORMATION FORMATTING STANDARDS:**
Tree of Life AI provides comprehensive, well-structured health guidance because medical information demands clarity, organization, and scannability.

When responding to health questions:
- Use clear section headers to organize complex information by topic
- Employ bullet points and lists for symptoms, foods, supplements, dosages, and action items
- Structure responses to be scannable - users should quickly find the section they need
- Make safety warnings and "when to seek care" information highly visible with clear headers
- Provide specific, actionable recommendations with dosages, frequencies, and quantities
- Separate evidence-based approaches from experimental or traditional methods
- Present information comprehensively to reduce need for multiple follow-up questions
- Use formatting that reflects the seriousness and professional nature of health topics
- Organize by treatment approach: Western Medicine first, then integrative modalities, then traditional systems

This is a specialized health information platform, not a casual chatbot. Medical information requires professional presentation for safety, clarity, and actionability. Well-formatted responses improve comprehension, reduce token usage through fewer follow-ups, and ensure critical safety information is visible.

**CONVERSATIONAL APPROACH:**
- Be warm, knowledgeable, and supportive in tone
- When you have specialized knowledge from specific modalities, mention it naturally
- Offer to explore specific aspects in more depth
- Provide evidence-based guidance with appropriate cautions
- Balance comprehensiveness with readability
- Invite follow-up questions on specific aspects the user wants to explore further"""
---

## TABLE OF CONTENTS

1. [Historical Foundation](#historical-foundation)
2. [Theoretical Framework](#theoretical-framework)
3. [Assessment & Evaluation](#assessment-evaluation)
4. [Treatment Modalities](#treatment-modalities)
5. [Pharmacology & Therapeutics](#pharmacology-therapeutics)
6. [Clinical Integration with Other Traditions](#clinical-integration)
7. [Evidence Base & Research](#evidence-base)
8. [Resources & References](#resources)
9. [Clinical Applications by System](#clinical-applications)
10. [Safety Protocols & Red Flags](#safety-protocols)

---

## HISTORICAL FOUNDATION

### Evolution of Modern Medicine

**Ancient Roots (Pre-1500s)**
Western medicine traces its origins to ancient Greece, particularly the Hippocratic tradition (460-370 BCE). Hippocrates, the "Father of Medicine," established medicine as a rational discipline separate from religious and magical practices.

**Key Hippocratic Principles:**
- Observation over speculation
- Disease has natural causes (not divine punishment)
- "First, do no harm" (Primum non nocere)
- The healing power of nature (vis medicatrix naturae)
- Importance of diet, lifestyle, and environment

**The Four Humors Theory:**
Ancient Western medicine was based on balancing four bodily fluids:
- Blood (sanguine temperament)
- Phlegm (phlegmatic temperament)
- Yellow bile (choleric temperament)
- Black bile (melancholic temperament)

*Note: While outdated, this theory shows early recognition of constitutional differences and the mind-body connection.*

**Medieval Period (500-1500 CE)**
- Medical knowledge preserved by Islamic scholars
- Avicenna's "Canon of Medicine" (1025 CE) - synthesized Greek and Islamic medical knowledge
- Monastic hospitals in Europe
- Limited progress due to religious restrictions on human dissection

**Renaissance & Scientific Revolution (1500-1800)**
- Andreas Vesalius (1514-1564): Modern anatomy through human dissection
- William Harvey (1578-1657): Circulation of blood
- Development of microscopy
- Beginning of experimental method

**Modern Era (1800-Present)**

**19th Century Breakthroughs:**
- **Germ Theory (1860s)**: Louis Pasteur and Robert Koch proved microorganisms cause disease
- **Anesthesia (1846)**: Surgery became practical
- **Antiseptic Surgery (1867)**: Joseph Lister reduced post-surgical infections
- **Vaccination**: Edward Jenner (smallpox), Louis Pasteur (rabies)

**20th Century Revolution:**
- **Antibiotics (1928)**: Fleming's discovery of penicillin transformed infectious disease treatment
- **Medical Imaging**: X-rays (1895), CT scans (1971), MRI (1977), PET scans (1975)
- **Immunology**: Understanding immune system, development of vaccines
- **Molecular Biology**: DNA structure (1953), genetic medicine
- **Organ Transplantation**: First successful kidney transplant (1954)
- **Evidence-Based Medicine (1990s)**: Systematic approach to clinical decision-making

**21st Century Developments:**
- Genomic medicine and personalized treatment
- Immunotherapy for cancer
- Regenerative medicine and stem cells
- Precision medicine based on genetic profiles
- Telemedicine and AI-assisted diagnosis
- Microbiome research
- Epigenetics

---

## THEORETICAL FRAMEWORK

### Core Principles of Western Medicine

**1. Scientific Method**
Western medicine is grounded in the scientific method:
- **Observation**: Systematic recording of symptoms and signs
- **Hypothesis**: Proposed explanation for disease mechanism
- **Testing**: Controlled experiments and clinical trials
- **Analysis**: Statistical evaluation of results
- **Replication**: Independent verification
- **Revision**: Updating theories based on new evidence

**2. Reductionism & Systems Biology**

**Reductionist Approach:**
- Break down complex systems into component parts
- Understand mechanisms at molecular, cellular, organ levels
- Focus on specific disease pathways
- Targeted interventions for specific problems

**Modern Systems Approach:**
Recognition that body functions as integrated whole:
- Homeostasis: Self-regulating balance
- Feedback loops between systems
- Network medicine: Understanding interactions
- Psychoneuroimmunology: Mind-body connections

**3. Pathophysiology (Disease Mechanisms)**

Western medicine excels at understanding HOW disease occurs:

**Cellular Level:**
- Genetic mutations
- Protein misfolding
- Mitochondrial dysfunction
- Oxidative stress
- Inflammation

**Organ Level:**
- Structural damage
- Functional impairment
- Compensatory mechanisms
- Cascade effects

**Systemic Level:**
- Metabolic disorders
- Immune dysfunction
- Hormonal imbalances
- Circulatory problems

**4. Evidence Hierarchy**

Western medicine ranks evidence by reliability:

**Level 1 (Highest):**
- Systematic reviews and meta-analyses of randomized controlled trials (RCTs)
- Large, well-designed RCTs

**Level 2:**
- Smaller RCTs
- Cohort studies
- Case-control studies

**Level 3:**
- Case series
- Expert opinion
- Mechanistic studies

**Level 4 (Lowest):**
- Anecdotal reports
- Single case studies

**5. Diagnosis Through Testing**

Western medicine emphasizes objective measurement:

**Laboratory Tests:**
- Blood chemistry (glucose, electrolytes, enzymes)
- Complete blood count (CBC)
- Urinalysis
- Hormone levels
- Tumor markers
- Genetic testing

**Imaging:**
- X-ray: Bones, dense tissues
- Ultrasound: Soft tissues, organs, blood flow
- CT (Computed Tomography): Detailed cross-sections
- MRI (Magnetic Resonance Imaging): Soft tissue detail, no radiation
- PET (Positron Emission Tomography): Metabolic activity
- Nuclear medicine: Functional imaging

**Functional Testing:**
- ECG/EKG: Heart electrical activity
- Stress tests: Cardiovascular function
- Pulmonary function tests: Lung capacity
- Endoscopy: Direct visualization
- Biopsy: Tissue examination

**6. Pharmacological Paradigm**

**Drug Action Principles:**
- **Pharmacokinetics**: What body does to drug (absorption, distribution, metabolism, excretion)
- **Pharmacodynamics**: What drug does to body (mechanism of action)
- **Dose-Response**: Relationship between amount and effect
- **Therapeutic Window**: Safe and effective dose range
- **Drug Interactions**: How medications affect each other

**Drug Classes by Mechanism:**
- Receptor agonists/antagonists
- Enzyme inhibitors
- Ion channel modulators
- Hormone replacements
- Antibiotics/antivirals/antifungals
- Immunomodulators

---

## ASSESSMENT & EVALUATION

### The Medical Interview (History Taking)

**Chief Complaint (CC)**
Patient's main concern in their own words:
- "What brings you in today?"
- Duration and severity
- Impact on daily life

**History of Present Illness (HPI)**
Detailed exploration using OPQRST:
- **O**nset: When did it start? Sudden or gradual?
- **P**rovocation/Palliation: What makes it better or worse?
- **Q**uality: Describe the sensation (sharp, dull, burning, etc.)
- **R**egion/Radiation: Where is it? Does it spread?
- **S**everity: Rate 1-10, impact on function
- **T**emporal: Constant or intermittent? Pattern?

**Past Medical History (PMH)**
- Previous diagnoses
- Surgeries and hospitalizations
- Chronic conditions
- Childhood illnesses

**Medications**
- Prescription drugs
- Over-the-counter medications
- Supplements and herbs
- Dosages and compliance

**Allergies**
- Drug allergies and reactions
- Environmental allergies
- Food sensitivities

**Family History**
- Genetic conditions
- Major diseases in relatives
- Age of onset
- Cause of death in family members

**Social History**
- Occupation and exposures
- Tobacco, alcohol, drug use
- Diet and exercise
- Living situation
- Travel history
- Sexual history (when relevant)

**Review of Systems (ROS)**
Systematic inquiry about each body system:
- Constitutional: Fever, weight changes, fatigue
- Eyes: Vision changes, pain
- ENT: Hearing, sinus, throat
- Cardiovascular: Chest pain, palpitations, edema
- Respiratory: Cough, shortness of breath, wheezing
- Gastrointestinal: Nausea, bowel changes, pain
- Genitourinary: Urination changes, pain
- Musculoskeletal: Joint pain, weakness
- Skin: Rashes, lesions, changes
- Neurological: Headaches, numbness, dizziness
- Psychiatric: Mood, anxiety, sleep
- Endocrine: Temperature intolerance, thirst
- Hematologic: Bleeding, bruising
- Allergic/Immunologic: Recurrent infections

### Physical Examination

**General Appearance**
- Level of distress
- Body habitus
- Hygiene and grooming
- Mental status

**Vital Signs**
- Temperature (normal: 97-99Â°F / 36.1-37.2Â°C)
- Pulse (normal resting: 60-100 bpm)
- Respiratory rate (normal: 12-20 breaths/min)
- Blood pressure (normal: <120/80 mmHg)
- Oxygen saturation (normal: >95%)
- Pain level (0-10 scale)

**Head, Eyes, Ears, Nose, Throat (HEENT)**
- Pupils: Equal, round, reactive to light
- Conjunctiva: Color, discharge
- Ears: Tympanic membranes
- Nose: Septum, mucosa
- Throat: Pharynx, tonsils
- Lymph nodes: Size, tenderness

**Cardiovascular**
- Heart sounds: Rate, rhythm, murmurs
- Peripheral pulses
- Capillary refill
- Edema

**Respiratory**
- Inspection: Breathing pattern, use of accessory muscles
- Auscultation: Breath sounds, wheezes, crackles
- Percussion: Resonance
- Expansion and tactile fremitus

**Abdominal**
- Inspection: Contour, scars, distension
- Auscultation: Bowel sounds (before palpation)
- Palpation: Tenderness, masses, organ size
- Percussion: Fluid, organ borders

**Musculoskeletal**
- Range of motion
- Strength (0-5 scale)
- Deformities
- Swelling, tenderness
- Gait

**Neurological**
- Mental status: Orientation, memory, attention
- Cranial nerves (I-XII)
- Motor: Strength, tone, coordination
- Sensory: Touch, pain, temperature, proprioception
- Reflexes: Deep tendon reflexes (0-4+ scale)
- Cerebellar: Finger-to-nose, heel-to-shin, rapid alternating movements

**Skin**
- Color, temperature, moisture
- Rashes, lesions
- Turgor (hydration)
- Nails and hair

### Differential Diagnosis Process

**Step 1: Generate Hypotheses**
Based on chief complaint and initial history, create list of possible diagnoses

**Step 2: Probability Assessment**
Rank by likelihood considering:
- Prevalence (common things are common)
- Patient demographics
- Risk factors
- Clinical presentation

**Step 3: Critical Diagnoses**
Always consider life-threatening possibilities:
- "Don't miss" diagnoses
- Emergency conditions requiring immediate action

**Step 4: Discriminating Information**
Gather data that distinguishes between possibilities:
- Key history questions
- Physical exam findings
- Laboratory tests
- Imaging studies

**Step 5: Diagnostic Testing Strategy**
- Start with least invasive, most informative tests
- Cost-effectiveness
- Risk-benefit analysis
- Pre-test probability affects test selection

**Step 6: Synthesis**
Integrate all information to reach diagnosis:
- Pattern recognition
- Bayesian reasoning (updating probabilities)
- Occam's razor (simplest explanation)
- Hickam's dictum (patient can have multiple diseases)

### Common Diagnostic Frameworks

**VINDICATE Mnemonic for Differential Diagnosis:**
- **V**ascular (stroke, MI, DVT)
- **I**nfectious (bacterial, viral, fungal, parasitic)
- **N**eoplastic (cancer, benign tumors)
- **D**egenerative/Deficiency (arthritis, vitamin deficiency)
- **I**atrogenic/Idiopathic (drug side effect, unknown cause)
- **C**ongenital (birth defects, genetic)
- **A**utoimmune (lupus, RA, IBD)
- **T**raumatic (injury)
- **E**ndocrine/Environmental (thyroid, toxins)

---

## TREATMENT MODALITIES

### Pharmaceutical Interventions

**Analgesics (Pain Relief)**

**Non-Opioid Analgesics:**
- **Acetaminophen (Tylenol)**: 
  - Mechanism: Central COX inhibition
  - Use: Mild-moderate pain, fever
  - Dose: 325-1000mg every 4-6 hours (max 4g/day)
  - Caution: Hepatotoxicity with overdose or alcohol use

- **NSAIDs (Ibuprofen, Naproxen)**:
  - Mechanism: COX-1 and COX-2 inhibition â†’ reduced prostaglandins
  - Use: Pain, inflammation, fever
  - Ibuprofen: 200-800mg every 6-8 hours (max 3.2g/day)
  - Naproxen: 220-500mg every 12 hours
  - Cautions: GI bleeding, cardiovascular risk, kidney damage

**Opioid Analgesics:**
- **Codeine, Hydrocodone, Oxycodone, Morphine, Fentanyl**
- Mechanism: Mu-opioid receptor agonists
- Use: Moderate to severe pain
- Cautions: Addiction potential, respiratory depression, constipation, tolerance
- Prescribing: Lowest effective dose for shortest duration

**Antimicrobials**

**Antibiotics (for bacterial infections):**

*Beta-lactams:*
- **Penicillins**: Amoxicillin, Ampicillin
  - Mechanism: Inhibit cell wall synthesis
  - Use: Strep throat, UTIs, skin infections
  - Resistance: Increasingly common (MRSA)

- **Cephalosporins**: Cephalexin (1st gen), Cefuroxime (2nd gen), Ceftriaxone (3rd gen)
  - Broader spectrum than penicillins
  - Use: Respiratory, urinary, skin infections

*Macrolides:*
- **Azithromycin (Z-pack), Clarithromycin**
- Mechanism: Inhibit protein synthesis
- Use: Respiratory infections, alternative to penicillin
- Benefit: Once-daily dosing

*Fluoroquinolones:*
- **Ciprofloxacin, Levofloxacin**
- Mechanism: Inhibit DNA gyrase
- Use: UTIs, respiratory infections, GI infections
- Cautions: Tendon rupture risk, peripheral neuropathy

*Other Classes:*
- **Tetracyclines**: Doxycycline (Lyme disease, acne, respiratory)
- **Sulfonamides**: Trimethoprim-sulfamethoxazole/Bactrim (UTIs, MRSA)
- **Aminoglycosides**: Gentamicin (serious gram-negative infections)
- **Metronidazole**: Anaerobic bacteria, C. difficile, parasites

**Antivirals:**
- **Acyclovir/Valacyclovir**: Herpes simplex, shingles
- **Oseltamivir (Tamiflu)**: Influenza (within 48 hours of onset)
- **Antiretrovirals**: HIV treatment (HAART)

**Antifungals:**
- **Topical**: Clotrimazole, Miconazole (athlete's foot, yeast infections)
- **Oral**: Fluconazole (systemic yeast), Terbinafine (nail fungus)

**Cardiovascular Medications**

**Antihypertensives:**

*ACE Inhibitors (ending in -pril):*
- **Lisinopril, Enalapril, Ramipril**
- Mechanism: Block angiotensin-converting enzyme
- Benefits: Protect kidneys, reduce heart failure risk
- Side effects: Dry cough (10%), hyperkalemia, angioedema (rare)

*ARBs (ending in -sartan):*
- **Losartan, Valsartan, Olmesartan**
- Mechanism: Block angiotensin II receptors
- Similar to ACE inhibitors without cough
- Use: Hypertension, heart failure, diabetic nephropathy

*Beta-Blockers (ending in -lol):*
- **Metoprolol, Atenolol, Carvedilol**
- Mechanism: Block beta-adrenergic receptors
- Use: Hypertension, heart failure, arrhythmias, post-MI
- Side effects: Fatigue, bradycardia, contraindicated in asthma

*Calcium Channel Blockers:*
- **Amlodipine, Diltiazem, Verapamil**
- Mechanism: Block calcium channels in heart and vessels
- Use: Hypertension, angina, arrhythmias
- Side effects: Edema, constipation (especially verapamil)

*Diuretics:*
- **Hydrochlorothiazide (HCTZ)**: Thiazide diuretic, first-line for hypertension
- **Furosemide (Lasix)**: Loop diuretic for heart failure, edema
- **Spironolactone**: Potassium-sparing, aldosterone antagonist

**Lipid-Lowering Agents:**

*Statins (ending in -statin):*
- **Atorvastatin (Lipitor), Simvastatin, Rosuvastatin**
- Mechanism: HMG-CoA reductase inhibitors
- Effect: Lower LDL cholesterol 25-55%
- Benefits: Reduce cardiovascular events, stroke, mortality
- Side effects: Muscle pain (myalgia), rarely rhabdomyolysis
- Monitoring: Liver enzymes, CK if muscle symptoms

**Anticoagulants/Antiplatelets:**
- **Aspirin**: Antiplatelet, COX-1 inhibitor
  - Use: MI prevention, stroke prevention (81-325mg daily)
  - Caution: Bleeding risk
  
- **Clopidogrel (Plavix)**: P2Y12 inhibitor
  - Use: Post-stent, stroke prevention
  
- **Warfarin (Coumadin)**: Vitamin K antagonist
  - Use: Atrial fibrillation, DVT/PE, mechanical heart valves
  - Monitoring: INR (target 2-3 for most indications)
  - Interactions: Many foods and drugs
  
- **NOACs** (Apixaban, Rivaroxaban, Dabigatran)
  - Advantages: No monitoring, fewer interactions
  - Use: Atrial fibrillation, DVT/PE

**Endocrine Medications**

**Diabetes:**

*Metformin:*
- Mechanism: Reduces hepatic glucose production, improves insulin sensitivity
- First-line for type 2 diabetes
- Benefits: Weight neutral, cardiovascular benefits
- Side effects: GI upset, lactic acidosis (rare)
- Contraindications: Severe kidney disease

*Sulfonylureas:*
- **Glipizide, Glyburide, Glimepiride**
- Mechanism: Stimulate insulin release
- Caution: Hypoglycemia, weight gain

*GLP-1 Agonists:*
- **Semaglutide (Ozempic, Wegovy), Liraglutide**
- Benefits: Weight loss, cardiovascular benefits
- Route: Injection (weekly or daily)
- Side effects: Nausea, vomiting

*SGLT2 Inhibitors:*
- **Empagliflozin, Canagliflozin, Dapagliflozin**
- Mechanism: Increase glucose excretion in urine
- Benefits: Weight loss, cardiovascular and kidney protection
- Side effects: UTIs, yeast infections, DKA risk

*Insulin:*
- **Rapid-acting**: Lispro, Aspart (meals)
- **Long-acting**: Glargine, Detemir (basal)
- Essential for type 1 diabetes
- Dosing: Individualized, requires monitoring

**Thyroid:**
- **Levothyroxine (Synthroid)**: Hypothyroidism treatment
  - Dose: Individualized based on TSH
  - Timing: Take on empty stomach, 30-60 min before food
  
- **Methimazole**: Hyperthyroidism treatment
  - Mechanism: Blocks thyroid hormone synthesis

**Gastrointestinal Medications**

**Proton Pump Inhibitors (PPIs):**
- **Omeprazole, Esomeprazole, Lansoprazole, Pantoprazole**
- Mechanism: Irreversibly block H+/K+ ATPase (proton pump)
- Use: GERD, peptic ulcers, H. pylori treatment
- Side effects: B12 deficiency, bone fracture risk, C. diff risk with long-term use
- Recommendation: Lowest dose for shortest duration

**H2 Blockers:**
- **Famotidine (Pepcid), Ranitidine** (removed from market 2020)
- Mechanism: Block histamine-2 receptors
- Use: Mild GERD, peptic ulcers
- Less potent than PPIs

**Antiemetics:**
- **Ondansetron (Zofran)**: 5-HT3 antagonist (chemotherapy, post-op nausea)
- **Metoclopramide (Reglan)**: Prokinetic agent (gastroparesis, nausea)
- **Promethazine**: Antihistamine (motion sickness, nausea)

**Laxatives:**
- **Osmotic**: Polyethylene glycol (MiraLAX), lactulose
- **Stimulant**: Senna, bisacodyl
- **Bulk-forming**: Psyllium (Metamucil)
- **Stool softener**: Docusate (Colace)

**Respiratory Medications**

**Asthma/COPD:**

*Bronchodilators:*
- **Short-acting beta-agonists (SABAs)**: Albuterol (rescue inhaler)
- **Long-acting beta-agonists (LABAs)**: Salmeterol, Formoterol (maintenance)
- **Anticholinergics**: Ipratropium (short-acting), Tiotropium (long-acting)

*Corticosteroids:*
- **Inhaled**: Fluticasone, Budesonide (maintenance, reduce inflammation)
- **Combination inhalers**: Fluticasone/Salmeterol (Advair), Budesonide/Formoterol (Symbicort)
- **Systemic**: Prednisone (acute exacerbations)

**Mental Health Medications**

**Antidepressants:**

*SSRIs (Selective Serotonin Reuptake Inhibitors):*
- **Fluoxetine (Prozac), Sertraline (Zoloft), Escitalopram (Lexapro), Paroxetine**
- Mechanism: Block serotonin reuptake
- Use: Depression, anxiety, OCD, PTSD
- Onset: 2-4 weeks for full effect
- Side effects: Sexual dysfunction, weight gain, GI upset
- Discontinuation: Taper to avoid withdrawal

*SNRIs (Serotonin-Norepinephrine Reuptake Inhibitors):*
- **Venlafaxine (Effexor), Duloxetine (Cymbalta)**
- Benefits: Also helps neuropathic pain
- Side effects: Similar to SSRIs plus increased blood pressure

*Atypical Antidepressants:*
- **Bupropion (Wellbutrin)**: Also for smoking cessation, less sexual side effects
- **Mirtazapine**: Helps with sleep and appetite

**Anxiolytics:**
- **Benzodiazepines**: Alprazolam (Xanax), Lorazepam (Ativan), Diazepam (Valium)
  - Mechanism: GABA-A receptor agonists
  - Use: Short-term anxiety, panic attacks
  - Cautions: Addiction, tolerance, withdrawal, respiratory depression
  - Avoid: Long-term use, combination with opioids

- **Buspirone**: Non-benzodiazepine, less sedating, no addiction potential

**Antipsychotics:**
- **Typical**: Haloperidol (high potency), Chlorpromazine (low potency)
- **Atypical**: Risperidone, Olanzapine, Quetiapine, Aripiprazole
- Use: Schizophrenia, bipolar disorder, severe agitation
- Side effects: Weight gain, metabolic syndrome, movement disorders

**Mood Stabilizers:**
- **Lithium**: Gold standard for bipolar disorder
  - Monitoring: Blood levels, kidney and thyroid function
- **Valproate, Carbamazepine, Lamotrigine**: Anticonvulsants used for mood stabilization

### Surgical Interventions

**Categories of Surgery:**

**Emergency Surgery:**
Life-threatening conditions requiring immediate intervention:
- Ruptured appendix
- Perforated ulcer
- Trauma with internal bleeding
- Ruptured aneurysm
- Bowel obstruction with perforation

**Urgent Surgery:**
Serious conditions requiring surgery within days:
- Symptomatic gallstones
- Fractures requiring fixation
- Certain cancers

**Elective Surgery:**
Planned procedures to improve quality of life:
- Joint replacement
- Cataract removal
- Hernia repair
- Cosmetic procedures

**Common Surgical Procedures:**

**General Surgery:**
- Appendectomy (appendicitis)
- Cholecystectomy (gallbladder removal)
- Hernia repair
- Bowel resection
- Cancer resection

**Orthopedic:**
- Joint replacement (hip, knee)
- Fracture fixation
- Arthroscopy
- Spinal surgery (fusion, discectomy)

**Cardiovascular:**
- Coronary artery bypass graft (CABG)
- Valve replacement/repair
- Angioplasty and stenting
- Pacemaker/defibrillator implantation

**Neurosurgery:**
- Craniotomy (brain surgery)
- Spinal surgery
- Aneurysm clipping
- Tumor resection

**Minimally Invasive Techniques:**
- **Laparoscopy**: Small incisions, camera-guided surgery
- **Robotic surgery**: Enhanced precision
- **Endoscopy**: Visualization and intervention through natural openings
- Benefits: Faster recovery, less pain, smaller scars, reduced complications

### Physical Therapy & Rehabilitation

**Goals:**
- Restore function
- Reduce pain
- Improve mobility
- Prevent disability
- Enhance quality of life

**Modalities:**
- Therapeutic exercise
- Manual therapy
- Heat/cold therapy
- Electrical stimulation
- Ultrasound therapy
- Traction

**Applications:**
- Post-surgical rehabilitation
- Stroke recovery
- Sports injuries
- Chronic pain conditions
- Balance and fall prevention

### Lifestyle Medicine

**The Six Pillars:**

**1. Nutrition**
- Whole food, plant-predominant diet
- Limit processed foods, added sugars, excess sodium
- Mediterranean diet pattern
- Adequate hydration

**2. Physical Activity**
- 150 minutes moderate aerobic exercise weekly
- Strength training 2+ days/week
- Reduce sedentary time
- Movement throughout the day

**3. Sleep**
- 7-9 hours nightly for adults
- Consistent sleep schedule
- Sleep hygiene practices
- Address sleep disorders

**4. Stress Management**
- Mindfulness and meditation
- Cognitive-behavioral techniques
- Time management
- Social support
- Professional counseling when needed

**5. Substance Use**
- Tobacco cessation
- Limit alcohol (if consumed)
- Avoid illicit drugs
- Careful use of prescription medications

**6. Social Connection**
- Strong relationships
- Community engagement
- Purpose and meaning
- Positive social support

**Evidence:**
Many chronic diseases are largely preventable through lifestyle:
- 80% of heart disease
- 70% of stroke
- 90% of type 2 diabetes
- 70% of colon cancer

---

## PHARMACOLOGY & THERAPEUTICS

### Drug Interactions

**Drug-Drug Interactions:**

**Pharmacokinetic Interactions:**
- **Absorption**: Antacids reduce absorption of many drugs
- **Metabolism**: CYP450 enzyme interactions
  - Inhibitors increase drug levels (grapefruit juice, certain antibiotics)
  - Inducers decrease drug levels (St. John's Wort, rifampin)
- **Excretion**: Competition for renal elimination

**Pharmacodynamic Interactions:**
- **Additive effects**: Two sedatives â†’ excessive sedation
- **Synergistic effects**: Two antibiotics â†’ enhanced bacterial killing
- **Antagonistic effects**: Beta-blocker + beta-agonist â†’ reduced efficacy

**High-Risk Combinations to Avoid:**
- NSAIDs + Anticoagulants â†’ bleeding risk
- Opioids + Benzodiazepines â†’ respiratory depression
- Multiple anticholinergics â†’ confusion, falls (especially elderly)
- SSRIs + MAOIs â†’ serotonin syndrome
- Potassium-sparing diuretics + ACE inhibitors â†’ hyperkalemia

**Drug-Food Interactions:**
- **Grapefruit juice**: Inhibits CYP3A4, increases levels of many drugs (statins, calcium channel blockers, immunosuppressants)
- **Vitamin K-rich foods**: Reduce warfarin effectiveness (leafy greens)
- **Dairy products**: Reduce absorption of tetracyclines, fluoroquinolones
- **High-fat meals**: Can increase or decrease absorption depending on drug

**Drug-Herb Interactions:**
- **St. John's Wort**: CYP450 inducer, reduces effectiveness of many drugs (birth control, antidepressants, immunosuppressants)
- **Ginkgo biloba**: Increases bleeding risk with anticoagulants
- **Garlic supplements**: May increase bleeding risk
- **Ginseng**: May affect blood sugar, interact with warfarin

### Adverse Drug Reactions

**Types:**

**Type A (Augmented):**
- Predictable from pharmacology
- Dose-dependent
- Common (>10%)
- Examples: Sedation from antihistamines, GI upset from antibiotics

**Type B (Bizarre):**
- Unpredictable
- Not dose-dependent
- Rare (<1%)
- Examples: Anaphylaxis, Stevens-Johnson syndrome

**Organ-Specific Toxicities:**

**Hepatotoxicity:**
- Drugs: Acetaminophen (overdose), isoniazid, statins, some antibiotics
- Monitoring: Liver enzymes (ALT, AST)
- Symptoms: Jaundice, abdominal pain, fatigue

**Nephrotoxicity:**
- Drugs: NSAIDs, aminoglycosides, contrast dye, ACE inhibitors (in certain conditions)
- Monitoring: Creatinine, BUN, GFR
- Risk factors: Dehydration, pre-existing kidney disease

**Cardiotoxicity:**
- **QT prolongation**: Certain antibiotics, antipsychotics, antiarrhythmics
  - Risk: Torsades de pointes (fatal arrhythmia)
  - Monitoring: ECG
- **Heart failure**: NSAIDs can worsen, certain diabetes medications (thiazolidinediones)

**Bone Marrow Suppression:**
- Drugs: Chemotherapy, certain antibiotics, immunosuppressants
- Monitoring: CBC
- Symptoms: Infection, bleeding, anemia

### Polypharmacy

**Definition:** Use of multiple medications (typically 5+)

**Risks:**
- Increased drug interactions
- Adverse effects
- Medication errors
- Non-adherence
- Falls (especially elderly)
- Cognitive impairment
- Hospitalization

**Deprescribing:**
Systematic process of reducing or stopping medications when:
- No longer indicated
- Risks outweigh benefits
- Better alternatives exist
- Patient preference

**Approach:**
1. Review all medications (including OTC, supplements)
2. Assess indication, effectiveness, safety
3. Prioritize which to continue vs. discontinue
4. Taper when appropriate (don't stop suddenly)
5. Monitor for withdrawal or disease recurrence

---

## CLINICAL INTEGRATION WITH OTHER TRADITIONS

### When Western Medicine Excels

**Emergency & Acute Care:**
- Life-threatening conditions
- Trauma
- Acute infections
- Surgical emergencies
- Cardiovascular emergencies (MI, stroke)

**Diagnostic Precision:**
- Advanced imaging (CT, MRI, PET)
- Laboratory testing
- Genetic testing
- Biopsy and pathology

**Complex Chronic Disease:**
- Cancer treatment
- Advanced heart failure
- Kidney disease
- Autoimmune disorders
- Transplant medicine

**Surgical Intervention:**
- Structural problems (hernias, cataracts, joint damage)
- Trauma repair
- Cancer removal
- Vascular procedures

**Pharmaceutical Management:**
- Bacterial infections (antibiotics)
- Severe mental illness
- Seizure disorders
- Organ transplant rejection prevention

### Complementing Other Traditions

**With Ayurveda:**
- **Western**: Diagnoses and treats specific disease
- **Ayurveda**: Addresses constitution, prevention, lifestyle
- **Integration**: Use Western diagnosis, incorporate Ayurvedic diet and lifestyle recommendations
- **Example**: Type 2 diabetes - Western meds to control blood sugar, Ayurvedic dietary approach for long-term balance

**With Traditional Chinese Medicine:**
- **Western**: Pharmaceuticals for acute symptoms
- **TCM**: Acupuncture for pain, herbs for balance
- **Integration**: Cancer patients using both chemotherapy and acupuncture for nausea
- **Research**: Acupuncture effectiveness for chronic pain, nausea proven by Western research standards

**With Herbal Medicine:**
- **Caution**: Drug-herb interactions
- **Integration**: Some herbs have strong evidence (St. John's Wort for mild depression, saw palmetto for BPH)
- **Approach**: Inform prescriber of all herbs used
- **Example**: Chronic inflammation - Western anti-inflammatories + turmeric supplementation

**With Homeopathy:**
- **Western view**: Controversial due to high dilutions
- **Integration**: May be used alongside conventional care for chronic conditions
- **Patient-centered**: Respect patient preferences while ensuring conventional care not neglected
- **Research**: Most meta-analyses show no effect beyond placebo, but debate continues

**With Chiropractic:**
- **Western**: Medications for pain
- **Chiropractic**: Spinal manipulation for musculoskeletal pain
- **Integration**: Low back pain management combining both approaches
- **Evidence**: Spinal manipulation moderately effective for acute low back pain

**With Clinical Nutrition:**
- **Strong synergy**: Western medicine increasingly recognizes nutrition importance
- **Integration**: Dietary approaches for diabetes, cardiovascular disease, obesity
- **Examples**: 
  - Mediterranean diet reduces cardiovascular events
  - DASH diet lowers blood pressure
  - Low FODMAP diet for IBS

**With Vibrational/Energy Healing:**
- **Western**: Skeptical of mechanism
- **Integration**: May provide stress reduction, placebo benefit
- **Research**: Limited high-quality studies
- **Patient care**: If not harmful and patient benefits, can coexist with conventional care

### Integrative Medicine Approach

**Definition:** Combines conventional Western medicine with evidence-based complementary therapies

**Core Principles:**
- Patient-centered care
- Use all appropriate therapies (conventional and complementary)
- Focus on whole person (physical, emotional, mental, spiritual)
- Emphasize prevention and wellness
- Therapeutic relationship is central
- Evidence-informed decision making

**Practical Application:**

**Chronic Pain:**
- Western: Analgesics (NSAIDs, low-dose opioids if needed)
- Physical therapy
- Acupuncture
- Mind-body techniques (meditation, biofeedback)
- Nutritional anti-inflammatory diet
- Chiropractic if musculoskeletal

**Cardiovascular Disease:**
- Western: Medications (statins, antihypertensives), procedures if needed
- Mediterranean diet
- Exercise prescription
- Stress management
- Yoga or tai chi
- Omega-3 supplementation

**Cancer Care:**
- Western: Surgery, chemotherapy, radiation as indicated
- Acupuncture for nausea and pain
- Mind-body therapies for anxiety and quality of life
- Nutritional support
- Massage for comfort
- Avoiding unproven alternative therapies that could interfere with treatment

**Mental Health:**
- Western: Psychotherapy, psychiatric medications when appropriate
- Mindfulness-based stress reduction (MBSR)
- Exercise (evidence for depression, anxiety)
- Nutrition: Omega-3s, Mediterranean diet
- Yoga
- Sleep optimization
- Social connection

### Red Flags: When to Prioritize Western Medicine

**Immediate Western Medical Care Required:**

**Cardiovascular Emergencies:**
- Chest pain (possible heart attack)
- Severe shortness of breath
- Sudden weakness/numbness (stroke)
- Uncontrolled bleeding

**Neurological Emergencies:**
- Worst headache of life (possible aneurysm)
- Sudden vision loss
- Seizures (first-time or prolonged)
- Severe head injury

**Abdominal Emergencies:**
- Severe abdominal pain (appendicitis, perforation, obstruction)
- Vomiting blood
- Black, tarry stools (GI bleeding)
- Unable to pass gas or stool with pain/distension

**Infectious Emergencies:**
- High fever with confusion, stiff neck, rash (meningitis)
- Difficulty breathing with fever (pneumonia)
- Rapidly spreading skin redness with fever (cellulitis)

**Other Critical Situations:**
- Suicidal thoughts or severe mental health crisis
- Suspected fracture
- Eye injuries or sudden vision changes
- Allergic reaction with breathing difficulty
- Severe burns
- Pregnancy complications

**Cancer Warning Signs (Requires evaluation, not emergency):**
- Unexplained weight loss
- Persistent unexplained pain
- Change in bowel/bladder habits
- Unusual bleeding or discharge
- Lump in breast or testicle
- Change in wart or mole
- Persistent cough or hoarseness

---

## EVIDENCE BASE & RESEARCH

### Levels of Evidence

**Understanding Study Types:**

**Randomized Controlled Trials (RCTs):**
- **Gold standard** for establishing causation
- Participants randomly assigned to treatment or control
- Double-blind when possible (neither participant nor researcher knows group)
- Controls for confounding variables
- Limitations: Expensive, artificial settings, may not reflect real-world use

**Systematic Reviews and Meta-Analyses:**
- **Highest level of evidence**
- Combine results from multiple RCTs
- Increase statistical power
- Identify consistent effects across studies
- Example: Cochrane reviews

**Cohort Studies:**
- Follow groups over time
- Compare outcomes between exposed and unexposed
- Can establish temporal relationships
- Good for studying rare exposures or long-term outcomes
- Limitations: Confounding variables, loss to follow-up

**Case-Control Studies:**
- Compare people with disease to those without
- Look back at exposures
- Good for studying rare diseases
- Limitations: Recall bias, difficult to establish causation

**Case Series and Case Reports:**
- Describe individual patients or small groups
- Generate hypotheses
- Useful for rare conditions
- Limitations: No comparison group, cannot establish causation

**Expert Opinion:**
- Lowest level of evidence
- Based on clinical experience and reasoning
- Used when no research available
- Subject to bias

### Evidence-Based Practice

**The EBM Triad:**
1. **Best available evidence**: Research studies
2. **Clinical expertise**: Provider experience and judgment
3. **Patient values and preferences**: Individual circumstances and desires

**Steps in EBM:**
1. **Ask**: Formulate clinical question (PICO format)
   - Population
   - Intervention
   - Comparison
   - Outcome

2. **Acquire**: Search for best evidence
   - PubMed, Cochrane Library
   - Clinical practice guidelines
   - UpToDate, DynaMed

3. **Appraise**: Critically evaluate evidence
   - Study design
   - Risk of bias
   - Applicability to patient

4. **Apply**: Integrate with clinical expertise and patient preferences

5. **Assess**: Evaluate outcomes and adjust

### Clinical Practice Guidelines

**Major Organizations:**
- American College of Cardiology/American Heart Association
- American Diabetes Association
- US Preventive Services Task Force (USPSTF)
- National Comprehensive Cancer Network (NCCN)
- Infectious Diseases Society of America (IDSA)

**Grading Recommendations:**

**Strength of Recommendation:**
- **Strong**: Benefits clearly outweigh risks, most patients should receive intervention
- **Weak/Conditional**: Benefits and risks closely balanced, decision depends on individual circumstances

**Quality of Evidence:**
- **High**: Multiple high-quality RCTs or systematic reviews
- **Moderate**: Some RCTs with limitations or strong observational evidence
- **Low**: Observational studies or expert opinion

### Number Needed to Treat (NNT)

**Definition:** Number of patients who need to receive intervention for one to benefit

**Interpretation:**
- **Lower NNT = more effective**
- NNT of 1: Everyone benefits
- NNT of 5: 1 in 5 benefit
- NNT of 50: 1 in 50 benefit

**Examples:**
- Aspirin for acute MI: NNT = 42 to prevent 1 death
- Statins for primary prevention: NNT = 104 to prevent 1 cardiovascular event over 10 years
- Antibiotics for sore throat: NNT = 200 to prevent 1 case of rheumatic fever

**Clinical Use:**
Helps patients understand realistic expectations of treatment

### Number Needed to Harm (NNH)

**Definition:** Number of patients who need to receive intervention for one to experience adverse effect

**Balance:**
- Compare NNT to NNH
- If NNH < NNT: More people harmed than helped
- If NNH > NNT: More people helped than harmed

---

## RESOURCES & REFERENCES

### Medical Textbooks

**Internal Medicine:**
- "Harrison's Principles of Internal Medicine" (21st Edition)
  - Comprehensive reference, 3,000+ pages
  - Gold standard for internal medicine
  
- "Current Medical Diagnosis & Treatment" (Annual publication)
  - Practical, concise, updated yearly
  - Point-of-care reference

**Clinical Skills:**
- "Bates' Guide to Physical Examination and History Taking"
  - Detailed examination techniques
  - Video demonstrations available

**Pharmacology:**
- "Goodman & Gilman's: The Pharmacological Basis of Therapeutics"
  - Comprehensive pharmacology reference
  
- "Tarascon Pocket Pharmacopoeia"
  - Quick reference guide
  - Commonly used by clinicians

### Online Resources

**Point-of-Care Tools:**
- **UpToDate**: Evidence-based clinical decision support
- **DynaMed**: Evidence-based reference tool
- **Epocrates**: Drug reference, interactions checker

**Clinical Guidelines:**
- **National Guideline Clearinghouse**: Searchable database of clinical practice guidelines
- **NICE (National Institute for Health and Care Excellence)**: UK evidence-based recommendations

**Drug Information:**
- **DailyMed (FDA)**: Official drug labels and package inserts
- **Drugs.com**: Patient-friendly drug information, interaction checker
- **Micromedex**: Professional drug information database

**Medical Calculators:**
- **MDCalc**: Clinical decision rules and calculators
  - ASCVD risk calculator
  - CKD-EPI GFR calculator
  - CHADS2-VASc score
  - Wells criteria for DVT/PE

### Professional Organizations

**Primary Care:**
- American Academy of Family Physicians (AAFP)
- American College of Physicians (ACP)

**Specialized:**
- American College of Cardiology (ACC)
- American Diabetes Association (ADA)
- American Cancer Society (ACS)
- Infectious Diseases Society of America (IDSA)

### Patient Education Resources

**Trusted Websites:**
- **MedlinePlus** (NIH): Consumer health information
- **Mayo Clinic**: Patient-friendly medical information
- **CDC**: Disease prevention, public health information
- **American Heart Association**: Cardiovascular health
- **American Diabetes Association**: Diabetes management

---

## CLINICAL APPLICATIONS BY SYSTEM

### Cardiovascular System

**Hypertension (High Blood Pressure)**

*Definition:* BP â‰¥130/80 mmHg (2017 guidelines)

**Stages:**
- **Elevated**: 120-129/<80
- **Stage 1**: 130-139/80-89
- **Stage 2**: â‰¥140/90
- **Hypertensive Crisis**: >180/>120 (emergency)

**Evaluation:**
- Confirm with multiple readings
- Check both arms
- Rule out secondary causes (kidney disease, endocrine disorders)
- Assess end-organ damage (heart, kidneys, eyes, brain)

**Treatment Approach:**
1. **Lifestyle modifications** (all patients):
   - DASH diet (rich in fruits, vegetables, low-fat dairy, reduced sodium)
   - Sodium restriction (<2,300 mg/day, ideally <1,500 mg/day)
   - Weight loss if overweight (1 kg loss â†’ 1 mmHg reduction)
   - Exercise (150 min/week moderate aerobic)
   - Limit alcohol
   - Stress management

2. **Medications** (based on BP level and cardiovascular risk):
   - **First-line**: ACE inhibitor or ARB, Calcium channel blocker, Thiazide diuretic
   - **Combination therapy**: Often needed for Stage 2 or resistant hypertension
   - **Goal**: <130/80 for most patients

**Monitoring:**
- Home BP monitoring
- Check BP every 3-6 months once controlled
- Annual labs: Creatinine, potassium, lipids

**Complications of Untreated Hypertension:**
- Heart attack, heart failure
- Stroke
- Kidney disease
- Vision loss
- Aneurysm

---

**Coronary Artery Disease (CAD)**

*Definition:* Atherosclerotic plaque buildup in coronary arteries

**Risk Factors:**
- **Modifiable**: Smoking, high cholesterol, hypertension, diabetes, obesity, physical inactivity
- **Non-modifiable**: Age, male sex, family history

**Presentation:**
- **Stable angina**: Predictable chest pain with exertion, relieved by rest
- **Acute coronary syndrome**: Unstable angina or myocardial infarction

**Diagnosis:**
- ECG (baseline and during symptoms)
- Stress test (exercise or pharmacologic)
- Coronary angiography (gold standard)
- CT coronary angiography (non-invasive)

**Treatment:**
1. **Medical management**:
   - **Antiplatelet**: Aspirin 81mg daily
   - **Statin**: High-intensity (atorvastatin 40-80mg)
   - **Beta-blocker**: Metoprolol (if prior MI or heart failure)
   - **ACE inhibitor**: If diabetes, hypertension, or heart failure
   - **Nitroglycerin**: Sublingual for acute angina

2. **Invasive procedures**:
   - **PCI (Percutaneous Coronary Intervention)**: Angioplasty + stent placement
   - **CABG (Coronary Artery Bypass Graft)**: For severe multi-vessel disease

3. **Cardiac rehabilitation**:
   - Supervised exercise
   - Education
   - Lifestyle counseling

**Prevention:**
- **Primary**: Statin if 10-year ASCVD risk â‰¥7.5%
- **Secondary**: Aggressive risk factor management after cardiac event

---

**Heart Failure**

*Definition:* Heart unable to pump sufficient blood to meet body's needs

**Types:**
- **HFrEF (reduced ejection fraction)**: Systolic dysfunction, EF <40%
- **HFpEF (preserved ejection fraction)**: Diastolic dysfunction, EF â‰¥50%

**Causes:**
- Coronary artery disease (most common)
- Hypertension
- Valvular disease
- Cardiomyopathy
- Arrhythmias

**Symptoms:**
- Shortness of breath (especially with exertion or lying flat)
- Fatigue
- Leg swelling (edema)
- Weight gain from fluid retention

**Diagnosis:**
- Echocardiogram (assess EF, valve function)
- BNP or NT-proBNP (elevated in heart failure)
- Chest X-ray (enlarged heart, pulmonary edema)

**Treatment HFrEF:**
1. **Guideline-Directed Medical Therapy (GDMT)**:
   - **ACE inhibitor or ARB**: Reduce mortality
   - **Beta-blocker**: Carvedilol, metoprolol succinate, bisoprolol
   - **Aldosterone antagonist**: Spironolactone or eplerenone (if EF â‰¤35%)
   - **SGLT2 inhibitor**: Empagliflozin or dapagliflozin (proven mortality benefit)
   
2. **Diuretics**: Furosemide for symptom relief (fluid overload)

3. **Devices**:
   - **ICD (Implantable Cardioverter-Defibrillator)**: If EF â‰¤35%, prevent sudden death
   - **CRT (Cardiac Resynchronization Therapy)**: Biventricular pacing if wide QRS

4. **Lifestyle**:
   - Sodium restriction (<2g/day)
   - Fluid restriction if severe
   - Daily weights (call MD if 2-3 lbs gain in 24 hrs)
   - Exercise as tolerated

**Prognosis:**
- 5-year mortality ~50% without treatment
- Significant improvement with GDMT

---

### Respiratory System

**Asthma**

*Definition:* Chronic inflammatory airway disease with reversible airflow obstruction

**Pathophysiology:**
- Airway inflammation
- Bronchial hyperresponsiveness
- Mucus production
- Airway remodeling (chronic cases)

**Triggers:**
- Allergens (pollen, dust mites, pets)
- Respiratory infections
- Exercise
- Cold air
- Irritants (smoke, pollution, strong odors)
- Stress
- Medications (aspirin, beta-blockers)

**Diagnosis:**
- **Spirometry**: 
  - Reduced FEV1/FVC ratio (<0.70)
  - Reversibility: >12% and 200ml improvement after bronchodilator
- **Peak flow monitoring**: Daily variability >20%
- **Methacholine challenge**: If spirometry normal but high suspicion

**Classification:**
- **Intermittent**: Symptoms â‰¤2 days/week, no nighttime awakenings
- **Mild persistent**: Symptoms >2 days/week
- **Moderate persistent**: Daily symptoms, nighttime awakenings >1x/week
- **Severe persistent**: Symptoms throughout day, nightly awakenings

**Treatment (Stepwise Approach):**

**Step 1 (Intermittent):**
- SABA (albuterol) as needed

**Step 2 (Mild):**
- Low-dose inhaled corticosteroid (ICS)
- Alternative: Leukotriene modifier (montelukast)

**Step 3 (Moderate):**
- Low-dose ICS + LABA combination
- Or medium-dose ICS alone

**Step 4:**
- Medium-dose ICS + LABA

**Step 5 (Severe):**
- High-dose ICS + LABA
- Consider add-on: Tiotropium, biologics (omalizumab, mepolizumab)

**Asthma Action Plan:**
- **Green zone**: Well-controlled, continue maintenance
- **Yellow zone**: Worsening symptoms, increase treatment
- **Red zone**: Severe symptoms, seek emergency care

**Emergency Treatment (Acute Exacerbation):**
1. SABA (albuterol nebulizer or inhaler with spacer)
2. Systemic corticosteroids (prednisone 40-60mg)
3. Ipratropium (if severe)
4. Oxygen if hypoxic
5. Hospitalization if poor response

---

**Chronic Obstructive Pulmonary Disease (COPD)**

*Definition:* Progressive airflow limitation, not fully reversible

**Types:**
- **Chronic bronchitis**: Productive cough â‰¥3 months/year for 2+ years
- **Emphysema**: Alveolar destruction, loss of elastic recoil

**Risk Factors:**
- Smoking (80-90% of cases)
- Occupational exposures
- Alpha-1 antitrypsin deficiency (genetic, consider in young patients or non-smokers)

**Symptoms:**
- Chronic cough
- Sputum production
- Progressive dyspnea (shortness of breath)
- Wheezing
- Chest tightness

**Diagnosis:**
- **Spirometry** (essential):
  - FEV1/FVC <0.70 (post-bronchodilator)
- **Severity grading** (based on FEV1):
  - GOLD 1 (Mild): FEV1 â‰¥80% predicted
  - GOLD 2 (Moderate): 50% â‰¤ FEV1 <80%
  - GOLD 3 (Severe): 30% â‰¤ FEV1 <50%
  - GOLD 4 (Very severe): FEV1 <30%
- Chest X-ray: Hyperinflation, bullae
- Alpha-1 antitrypsin level (if young or non-smoker)

**Treatment:**

1. **Smoking cessation** (most important):
   - Nicotine replacement, varenicline, or bupropion
   - Counseling

2. **Bronchodilators**:
   - **First-line**: Long-acting bronchodilator (LAMA or LABA)
     - LAMA: Tiotropium (preferred first choice)
     - LABA: Salmeterol, formoterol
   - **Combination**: LAMA + LABA if persistent symptoms
   - **SABA**: Albuterol as needed for rescue

3. **Inhaled corticosteroids**:
   - Add if frequent exacerbations (â‰¥2/year) or blood eosinophils â‰¥300
   - Triple therapy: ICS + LAMA + LABA

4. **Other medications**:
   - **Roflumilast**: PDE4 inhibitor for severe COPD with chronic bronchitis
   - **Azithromycin**: Reduce exacerbations in selected patients

5. **Oxygen therapy**:
   - If SpO2 â‰¤88% or PaO2 â‰¤55 mmHg at rest
   - Improves survival in hypoxemic patients

6. **Pulmonary rehabilitation**:
   - Exercise training
   - Education
   - Nutritional support
   - Proven to improve quality of life

7. **Vaccinations**:
   - Annual influenza vaccine
   - Pneumococcal vaccine (PPSV23, PCV15 or PCV20)
   - COVID-19 vaccination

**Acute Exacerbation:**
- Increased dyspnea, cough, sputum production
- Treatment:
  1. Short-acting bronchodilators (increased frequency)
  2. Systemic corticosteroids (prednisone 40mg Ã— 5 days)
  3. Antibiotics if increased sputum purulence
  4. Oxygen (target SpO2 88-92%)
  5. Consider hospitalization if severe

---

### Endocrine System

**Type 2 Diabetes Mellitus**

*Definition:* Insulin resistance and relative insulin deficiency

**Diagnostic Criteria** (any one of):
- Fasting glucose â‰¥126 mg/dL
- Random glucose â‰¥200 mg/dL + symptoms
- HbA1c â‰¥6.5%
- 2-hour glucose â‰¥200 mg/dL during OGTT

**Prediabetes:**
- Fasting glucose 100-125 mg/dL
- HbA1c 5.7-6.4%
- High risk of progression to diabetes

**Goals:**
- HbA1c <7% for most patients (individualize based on age, comorbidities)
- Fasting glucose 80-130 mg/dL
- Post-meal glucose <180 mg/dL

**Complications:**
- **Microvascular**: Retinopathy, nephropathy, neuropathy
- **Macrovascular**: CAD, stroke, peripheral arterial disease

**Treatment Approach:**

1. **Lifestyle** (first-line):
   - Weight loss (7-10% if overweight)
   - Mediterranean or low-carb diet
   - 150 min/week moderate exercise
   - Limit refined carbohydrates, added sugars

2. **First-line medication**: **Metformin**
   - Start 500mg daily, titrate to 1000mg BID
   - Check B12 level periodically
   - Hold before contrast studies

3. **Second-line** (add if HbA1c not at goal):
   - **If ASCVD or high risk**: GLP-1 agonist or SGLT2 inhibitor (proven cardiovascular benefit)
   - **If CKD**: SGLT2 inhibitor (kidney protective)
   - **If weight loss needed**: GLP-1 agonist
   - **If cost concern**: Sulfonylurea (glipizide)

4. **Combination therapy**:
   - Metformin + GLP-1 agonist + SGLT2 inhibitor (emerging as optimal)

5. **Insulin**:
   - If HbA1c >10%, symptomatic hyperglycemia
   - Start with basal insulin (glargine, detemir)
   - Add mealtime insulin (lispro, aspart) if needed

**Monitoring:**
- HbA1c every 3 months until goal, then every 6 months
- Annual:
  - Comprehensive foot exam
  - Dilated eye exam
  - Urine albumin-to-creatinine ratio (kidney screening)
  - Lipid panel
- Blood pressure checks
- Self-monitoring blood glucose (frequency varies)

**Hypoglycemia Management:**
- Glucose <70 mg/dL
- "Rule of 15": 15g fast-acting carbs, recheck in 15 min
- If severe (unable to treat self): Glucagon injection

---

**Hypothyroidism**

*Definition:* Underactive thyroid gland

**Causes:**
- **Primary** (thyroid problem):
  - Hashimoto's thyroiditis (autoimmune, most common)
  - Iodine deficiency (rare in US)
  - Post-thyroidectomy or radioiodine treatment
- **Secondary** (pituitary problem):
  - Pituitary tumor or injury

**Symptoms:**
- Fatigue
- Weight gain
- Cold intolerance
- Constipation
- Dry skin, hair loss
- Depression
- Menstrual irregularities
- Muscle weakness

**Diagnosis:**
- **Primary hypothyroidism**:
  - Elevated TSH
  - Low free T4
- **Subclinical hypothyroidism**:
  - Elevated TSH
  - Normal free T4
- **Secondary hypothyroidism**:
  - Low TSH
  - Low free T4

**Treatment:**
- **Levothyroxine** (Synthroid):
  - Dose based on weight (~1.6 mcg/kg)
  - Take on empty stomach, 30-60 min before food
  - Don't take with calcium, iron, or soy (interferes with absorption)
- **Monitoring**:
  - Check TSH 6-8 weeks after starting or dose change
  - Goal TSH: 0.5-2.5 mIU/L for most patients
  - Once stable, check annually

**Special Considerations:**
- Pregnancy: Increase dose by 20-30% (increased need)
- Elderly: Start low dose (25-50 mcg), increase slowly

---

### Gastrointestinal System

**Gastroesophageal Reflux Disease (GERD)**

*Definition:* Chronic acid reflux from stomach into esophagus

**Symptoms:**
- Heartburn (burning chest pain)
- Regurgitation
- Dysphagia (difficulty swallowing)
- Chronic cough
- Hoarseness
- Dental erosion

**Complications:**
- Esophagitis (inflammation)
- Stricture (narrowing)
- Barrett's esophagus (precancerous change)
- Esophageal adenocarcinoma (rare)

**Diagnosis:**
- Clinical diagnosis (typical symptoms)
- Endoscopy if:
  - Alarm symptoms (dysphagia, weight loss, bleeding)
  - Age >50 with new onset symptoms
  - Failed empiric PPI therapy

**Treatment:**

1. **Lifestyle modifications**:
   - Weight loss if overweight
   - Elevate head of bed 6-8 inches
   - Avoid late meals (3+ hours before bed)
   - Avoid triggers: Caffeine, alcohol, chocolate, fatty foods, mint, citrus
   - Quit smoking
   - Avoid tight clothing

2. **Medications**:
   - **Antacids** (Tums, Maalox): As needed, immediate relief
   - **H2 blockers** (famotidine): Mild symptoms, less potent
   - **PPIs** (omeprazole, esomeprazole):
     - Most effective
     - Take 30-60 min before first meal
     - 4-8 weeks initial treatment
     - Long-term: Lowest effective dose
     - Cautions: B12 deficiency, bone fracture risk, C. diff

3. **Surgery** (Nissen fundoplication):
   - If refractory to medical therapy
   - Large hiatal hernia

---

**Peptic Ulcer Disease**

*Definition:* Erosion in stomach (gastric) or duodenum (duodenal)

**Causes:**
- **H. pylori infection** (60-90% of duodenal ulcers)
- **NSAIDs** (common cause of gastric ulcers)
- Stress (ICU patients)
- Zollinger-Ellison syndrome (rare)

**Symptoms:**
- Epigastric pain
- **Duodenal ulcer**: Pain 2-5 hours after meals, improves with food
- **Gastric ulcer**: Pain worsens with food
- Nausea, bloating

**Complications:**
- Bleeding (hematemesis, melena)
- Perforation (surgical emergency)
- Gastric outlet obstruction

**Diagnosis:**
- **Endoscopy**: Visualize ulcer, biopsy for H. pylori
- **H. pylori testing**:
  - Urea breath test
  - Stool antigen
  - Serology (indicates exposure, not current infection)

**Treatment:**

1. **Stop NSAIDs** if possible

2. **PPI therapy**:
   - Twice daily for 4-8 weeks
   - Longer for gastric ulcers

3. **H. pylori treatment** (if positive):
   - **Triple therapy** (14 days):
     - PPI (twice daily)
     - Clarithromycin 500mg BID
     - Amoxicillin 1g BID
   - **Quadruple therapy** (if penicillin allergy or high resistance):
     - PPI + Bismuth + Metronidazole + Tetracycline
   - **Confirm eradication**: Urea breath test 4 weeks after treatment

4. **Prevention**:
   - If chronic NSAID use needed: Co-prescribe PPI

---

### Infectious Diseases

**Pneumonia**

*Definition:* Infection of lung parenchyma

**Types:**
- **Community-acquired (CAP)**: Outside hospital
- **Healthcare-associated**: Hospital, nursing home
- **Aspiration**: Inhaled gastric contents or foreign material

**Common Pathogens:**
- **Bacterial**: *Streptococcus pneumoniae* (most common), *Haemophilus influenzae*, *Mycoplasma*, *Legionella*
- **Viral**: Influenza, COVID-19, RSV
- **Fungal**: *Pneumocystis jirovecii* (immunocompromised)

**Symptoms:**
- Cough (productive or dry)
- Fever, chills
- Shortness of breath
- Pleuritic chest pain
- Fatigue

**Diagnosis:**
- Chest X-ray (infiltrate, consolidation)
- Complete blood count (elevated WBC)
- Sputum culture (if hospitalized)
- Blood cultures (if severe)
- Procalcitonin (bacterial vs viral)

**Severity Assessment (CURB-65):**
- **C**onfusion
- **U**rea >20 mg/dL (BUN >19 mg/dL)
- **R**espiratory rate â‰¥30
- **B**lood pressure <90/60
- Age â‰¥**65**

Score 0-1: Outpatient
Score 2: Consider hospitalization
Score â‰¥3: Hospitalization, consider ICU

**Treatment:**

**Outpatient (healthy adults):**
- **Amoxicillin** 1g TID for 5-7 days
- Alternative: Doxycycline or macrolide (azithromycin)

**Outpatient (comorbidities or recent antibiotics):**
- **Amoxicillin-clavulanate** + macrolide
- Or **Respiratory fluoroquinolone** (levofloxacin, moxifloxacin)

**Inpatient:**
- **Beta-lactam** (ceftriaxone, ampicillin-sulbactam) + **macrolide**
- Or **Respiratory fluoroquinolone** alone

**Prevention:**
- **Pneumococcal vaccines**:
  - PCV15 or PCV20 (age â‰¥65, certain medical conditions)
  - PPSV23 (if indicated)
- Annual influenza vaccine

---

**Urinary Tract Infection (UTI)**

*Definition:* Bacterial infection of urinary system

**Types:**
- **Cystitis**: Bladder infection (lower UTI)
- **Pyelonephritis**: Kidney infection (upper UTI)
- **Complicated**: Men, pregnant women, catheter, anatomical abnormality
- **Uncomplicated**: Otherwise healthy women

**Common Pathogens:**
- *E. coli* (80%)
- *Klebsiella*, *Proteus*, *Enterococcus*, *Staphylococcus saprophyticus*

**Symptoms:**

**Cystitis:**
- Dysuria (painful urination)
- Frequency, urgency
- Suprapubic pain
- Hematuria

**Pyelonephritis:**
- Fever, chills
- Flank pain
- Nausea, vomiting
- Cystitis symptoms

**Diagnosis:**
- **Urinalysis**:
  - Pyuria (WBCs)
  - Bacteriuria
  - Leukocyte esterase, nitrites
- **Urine culture**:
  - If pyelonephritis, complicated UTI, or failed treatment
  - >10^5 CFU/mL (100,000 colonies)

**Treatment:**

**Uncomplicated Cystitis:**
- **First-line**:
  - Nitrofurantoin 100mg BID Ã— 5 days
  - Trimethoprim-sulfamethoxazole DS BID Ã— 3 days (if local resistance <20%)
- **Second-line**:
  - Fosfomycin 3g single dose
  - Ciprofloxacin 250mg BID Ã— 3 days (reserve for resistant cases)

**Pyelonephritis (Outpatient):**
- Ciprofloxacin 500mg BID Ã— 7 days
- Levofloxacin 750mg daily Ã— 5 days
- Ceftriaxone 1g Ã— 1 dose then oral antibiotic

**Pyelonephritis (Inpatient):**
- IV antibiotics (ceftriaxone, fluoroquinolone)
- Transition to oral when improving

**Recurrent UTIs:**
- >2 infections in 6 months or >3 in 12 months
- **Prevention**:
  - Post-coital voiding
  - Adequate hydration
  - Cranberry products (modest benefit)
  - Estrogen cream (postmenopausal women)
  - Prophylactic antibiotics (if frequent, severe)

---

## SAFETY PROTOCOLS & RED FLAGS

### Medication Safety

**High-Alert Medications:**
- Insulin (hypoglycemia risk)
- Anticoagulants (bleeding risk)
- Opioids (respiratory depression)
- Chemotherapy (narrow therapeutic window)

**Five Rights of Medication Administration:**
1. Right patient
2. Right drug
3. Right dose
4. Right route
5. Right time

**Teach-Back Method:**
Ask patient to explain back:
- What medication is for
- How to take it
- What side effects to watch for

### Drug Allergy Documentation

**True allergy vs intolerance:**
- **Allergy**: Immune-mediated (rash, anaphylaxis)
- **Intolerance**: Non-immune side effect (nausea, diarrhea)

**Anaphylaxis signs:**
- Difficulty breathing, wheezing
- Swelling of face, lips, tongue
- Rapid pulse
- Dizziness, fainting
- **Treatment**: Epinephrine 0.3mg IM (EpiPen), call 911

### When to Seek Emergency Care

**Call 911 for:**
- Chest pain or pressure
- Difficulty breathing
- Sudden severe headache
- Weakness, numbness on one side
- Seizure
- Heavy bleeding
- Severe allergic reaction
- Suicidal thoughts with plan
- Severe abdominal pain

**Urgent care (same day):**
- High fever (>103Â°F adult, >100.4Â°F infant)
- Persistent vomiting/diarrhea with dehydration
- Moderate injury (possible fracture)
- Worsening infection

### Recognizing Sepsis

**Life-threatening organ dysfunction from infection**

**Signs** (q SOFA criteria):
- Altered mental status
- Systolic BP â‰¤100 mmHg
- Respiratory rate â‰¥22

**Time-sensitive:**
- "Hour-1 bundle": Blood cultures, antibiotics, fluids within 1 hour
- Early recognition and treatment saves lives

---

## CONCLUSION

Western medicine excels at:
- Emergency and acute care
- Precise diagnosis through testing
- Pharmacological interventions
- Surgical treatment
- Evidence-based approach

**Limitations:**
- Can be reductionist (miss whole-person aspects)
- Side effects from medications
- High cost
- Sometimes overuse of testing/treatment

**Integration with Other Traditions:**
Western medicine provides the foundation of diagnosis and acute management, while other traditions offer complementary approaches for prevention, chronic disease management, and whole-person care.

The future of medicine lies in integration: using Western medicine's diagnostic precision and life-saving interventions alongside other traditions' holistic approaches to create comprehensive, patient-centered care.

---

**END OF WESTERN MEDICINE SKILL DOCUMENT**

*This skill provides comprehensive knowledge of Western medical practice for use in the Tree of Life AI platform. It covers theoretical foundations, diagnostic approaches, treatment modalities, clinical applications, and integration with other healing traditions.*

*Remember: This is educational information. Always consult healthcare providers for medical advice, diagnosis, or treatment.*"""

# Combined system prompt with Western Medicine always included
SYSTEM_PROMPT_WITH_WESTERN_MED = BASE_SYSTEM_PROMPT + WESTERN_MEDICINE_SKILL
