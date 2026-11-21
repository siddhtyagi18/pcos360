"""PCOS360 Medical Knowledge Base & Reference Configurations.

Curated clinical evidence, reference intervals, and educational decision-support
guidelines sourced from international clinical consensus:
- 2023 International Evidence-based Guideline for the Assessment and Management
  of Polycystic Ovary Syndrome (Monash University, ESHRE, ASRM).
- Rotterdam ESHRE/ASRM-Sponsored Consensus on PCOS (2003, 2018, 2023).
- Androgen Excess and PCOS Society (AE-PCOS) Guidelines.
- Endocrine Society Clinical Practice Guidelines on PCOS.

NOTE: Reference ranges are configurable and vary by reporting laboratory, assay
methodology, patient age, and menstrual cycle phase. They are provided for
educational decision-support and must never be treated as universal diagnostic
thresholds or automated medical diagnoses.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class EvidenceGrade(str, Enum):
    GRADE_A = "Grade A (High-quality randomized clinical trials / systematic reviews)"
    GRADE_B = "Grade B (Moderate-quality clinical trials or cohort studies)"
    GRADE_C = "Grade C (Observational studies or case-control evidence)"
    CONSENSUS = "Clinical Consensus Recommendation (International guideline committee)"


class RotterdamPillar(str, Enum):
    OVULATORY_DYSFUNCTION = "Ovulatory Dysfunction (Oligo- or Anovulation)"
    HYPERANDROGENISM = "Hyperandrogenism (Biochemical or Clinical)"
    POLYCYSTIC_MORPHOLOGY = "Polycystic Ovarian Morphology (PCOM on Ultrasound)"


@dataclass(frozen=True)
class MedicalReferenceSource:
    source_id: str
    title: str
    organization: str
    year: int
    doi_or_url: str
    summary: str


@dataclass(frozen=True)
class BiomarkerReferenceRange:
    biomarker_name: str
    standard_unit: str
    canonical_aliases: List[str]
    normal_low: Optional[float]
    normal_high: Optional[float]
    borderline_low: Optional[float] = None
    borderline_high: Optional[float] = None
    elevated_threshold: Optional[float] = None
    low_threshold: Optional[float] = None
    clinical_significance: str = ""
    primary_source: str = "Monash 2023 / ACOG / Standard Clinical Chemistry"
    cycle_phase_dependent: bool = False
    caveats: str = (
        "Assay-dependent; compare with reference intervals provided on the patient's "
        "specific diagnostic laboratory report."
    )


# Curated, verifiable medical guideline sources
MEDICAL_SOURCES: Dict[str, MedicalReferenceSource] = {
    "monash_2023": MedicalReferenceSource(
        source_id="monash_2023",
        title="Recommendations from the 2023 International Evidence-based Guideline for the Assessment and Management of Polycystic Ovary Syndrome",
        organization="Monash University / ESHRE / ASRM / International PCOS Network",
        year=2023,
        doi_or_url="https://doi.org/10.1016/j.fertnstert.2023.07.025",
        summary=(
            "Primary international evidence consensus establishing Rotterdam diagnostic "
            "criteria application, insulin resistance assessment, cardiovascular risk screening, "
            "first-line lifestyle pacing, and evidence-based pharmacotherapies."
        ),
    ),
    "rotterdam_2004": MedicalReferenceSource(
        source_id="rotterdam_2004",
        title="Revised 2003 consensus on diagnostic criteria and long-term health risks related to polycystic ovary syndrome",
        organization="The Rotterdam ESHRE/ASRM-Sponsored PCOS Consensus Workshop Group",
        year=2004,
        doi_or_url="https://doi.org/10.1016/j.fertnstert.2003.10.004",
        summary=(
            "Defined the Rotterdam criteria requiring 2 out of 3 features: oligo/anovulation, "
            "clinical/biochemical hyperandrogenism, and polycystic ovarian morphology, with "
            "exclusion of related endocrine etiologies."
        ),
    ),
    "endocrine_society_2013": MedicalReferenceSource(
        source_id="endocrine_society_2013",
        title="Diagnosis and Treatment of Polycystic Ovary Syndrome: An Endocrine Society Clinical Practice Guideline",
        organization="The Endocrine Society",
        year=2013,
        doi_or_url="https://doi.org/10.1210/jc.2013-2350",
        summary=(
            "Established metabolic screening recommendations, oral glucose tolerance testing "
            "standards for at-risk women, and hirsutism/androgen assessment protocols."
        ),
    ),
    "aepcos_2009": MedicalReferenceSource(
        source_id="aepcos_2009",
        title="The Androgen Excess and PCOS Society criteria for the polycystic ovary syndrome: the complete task force report",
        organization="Androgen Excess and PCOS Society",
        year=2009,
        doi_or_url="https://doi.org/10.1016/j.fertnstert.2008.06.013",
        summary=(
            "Evaluated phenotypic heterogeneity in PCOS and underscored the central role "
            "of hyperandrogenism in long-term metabolic risk stratification."
        ),
    ),
}


# Baseline configurable biomarker reference ranges (Adult Female non-pregnant)
DEFAULT_BIOMARKER_RANGES: Dict[str, BiomarkerReferenceRange] = {
    "glucose_fasting": BiomarkerReferenceRange(
        biomarker_name="Fasting Blood Glucose",
        standard_unit="mg/dL",
        canonical_aliases=["fasting blood glucose", "fasting glucose", "fbs", "glucose fasting", "fbg"],
        normal_low=70.0,
        normal_high=99.0,
        borderline_low=100.0,
        borderline_high=125.0,
        elevated_threshold=126.0,
        clinical_significance=(
            "Screens for impaired fasting glucose and metabolic dysfunction secondary to "
            "peripheral insulin resistance in PCOS."
        ),
    ),
    "hba1c": BiomarkerReferenceRange(
        biomarker_name="HbA1c (Glycated Hemoglobin)",
        standard_unit="%",
        canonical_aliases=["hba1c", "glycated hemoglobin", "a1c", "hemoglobin a1c"],
        normal_low=4.0,
        normal_high=5.6,
        borderline_low=5.7,
        borderline_high=6.4,
        elevated_threshold=6.5,
        clinical_significance=(
            "Measures mean glycemia over the previous 90-120 days. Values between 5.7% and 6.4% "
            "indicate prediabetes / impaired glucose tolerance requiring lifestyle review."
        ),
    ),
    "insulin_fasting": BiomarkerReferenceRange(
        biomarker_name="Fasting Insulin",
        standard_unit="μIU/mL",
        canonical_aliases=["fasting insulin", "serum insulin", "insulin fasting", "basal insulin"],
        normal_low=2.0,
        normal_high=10.0,
        borderline_low=10.1,
        borderline_high=24.9,
        elevated_threshold=25.0,
        clinical_significance=(
            "Assesses compensatory hyperinsulinemia. Circulating insulin directly stimulates "
            "ovarian theca cell androgen production and reduces hepatic SHBG synthesis."
        ),
    ),
    "lh_fsh_ratio": BiomarkerReferenceRange(
        biomarker_name="LH / FSH Ratio",
        standard_unit="ratio",
        canonical_aliases=["lh / fsh ratio", "lh:fsh", "lh/fsh ratio", "lh to fsh ratio", "lh/fsh"],
        normal_low=0.8,
        normal_high=1.5,
        borderline_low=1.6,
        borderline_high=2.0,
        elevated_threshold=2.1,
        cycle_phase_dependent=True,
        clinical_significance=(
            "Elevated early follicular LH relative to FSH reflects altered GnRH pulsatility, "
            "commonly observed in neuroendocrine presentations of PCOS."
        ),
        caveats="Must be measured in the early follicular phase (Day 2-5 of menstrual bleeding) to be clinically interpretable.",
    ),
    "testosterone_total": BiomarkerReferenceRange(
        biomarker_name="Total Testosterone",
        standard_unit="ng/dL",
        canonical_aliases=["total testosterone", "serum testosterone", "testosterone total", "testosterone"],
        normal_low=15.0,
        normal_high=45.0,
        borderline_low=45.1,
        borderline_high=55.0,
        elevated_threshold=55.1,
        clinical_significance=(
            "Key biochemical marker for hyperandrogenism under Rotterdam criteria. "
            "Supports assessment of ovarian androgen excess."
        ),
    ),
    "testosterone_free": BiomarkerReferenceRange(
        biomarker_name="Free Testosterone",
        standard_unit="pg/mL",
        canonical_aliases=["free testosterone", "testosterone free", "calculated free testosterone"],
        normal_low=1.0,
        normal_high=6.5,
        borderline_low=6.6,
        borderline_high=8.0,
        elevated_threshold=8.1,
        clinical_significance=(
            "Bioavailable circulating androgen fraction; highly sensitive in hyperinsulinemic "
            "women where low SHBG increases free androgen fraction despite normal total testosterone."
        ),
    ),
    "dhea_s": BiomarkerReferenceRange(
        biomarker_name="DHEA-S (Dehydroepiandrosterone Sulfate)",
        standard_unit="μg/dL",
        canonical_aliases=["dhea-s", "dheas", "dhea sulfate", "dehydroepiandrosterone sulfate"],
        normal_low=65.0,
        normal_high=380.0,
        elevated_threshold=381.0,
        clinical_significance="Evaluates adrenal contributions to androgen excess in PCOS presentations.",
    ),
    "tsh": BiomarkerReferenceRange(
        biomarker_name="TSH (Thyroid Stimulating Hormone)",
        standard_unit="mIU/L",
        canonical_aliases=["tsh", "thyroid stimulating hormone", "serum tsh"],
        normal_low=0.4,
        normal_high=4.0,
        low_threshold=0.39,
        elevated_threshold=4.1,
        clinical_significance=(
            "Mandatory exclusionary panel: subclinical or overt hypothyroidism can mimic "
            "PCOS menstrual irregularities and ovulatory dysfunction."
        ),
    ),
    "vitamin_d_25_oh": BiomarkerReferenceRange(
        biomarker_name="25-OH Vitamin D",
        standard_unit="ng/mL",
        canonical_aliases=["25-oh vitamin d", "vitamin d", "25 hydroxy vitamin d", "vit d"],
        normal_low=30.0,
        normal_high=100.0,
        borderline_low=20.0,
        borderline_high=29.9,
        low_threshold=19.9,
        clinical_significance=(
            "Assesses vitamin D status. Deficiency (<20 ng/mL) is prevalent in metabolic PCOS "
            "and correlates with heightened insulin resistance and ovulatory delays."
        ),
    ),
    "cholesterol_total": BiomarkerReferenceRange(
        biomarker_name="Total Cholesterol",
        standard_unit="mg/dL",
        canonical_aliases=["total cholesterol", "cholesterol", "cholesterol total"],
        normal_low=120.0,
        normal_high=199.0,
        borderline_low=200.0,
        borderline_high=239.0,
        elevated_threshold=240.0,
        clinical_significance="Evaluates overall atherogenic circulating lipid risk.",
    ),
    "triglycerides": BiomarkerReferenceRange(
        biomarker_name="Triglycerides",
        standard_unit="mg/dL",
        canonical_aliases=["triglycerides", "serum triglycerides", "tg"],
        normal_low=40.0,
        normal_high=149.0,
        borderline_low=150.0,
        borderline_high=199.0,
        elevated_threshold=200.0,
        clinical_significance=(
            "Elevated triglycerides alongside lower HDL characterize atherogenic dyslipidemia "
            "driven by hepatic insulin resistance."
        ),
    ),
    "hdl_cholesterol": BiomarkerReferenceRange(
        biomarker_name="HDL Cholesterol",
        standard_unit="mg/dL",
        canonical_aliases=["hdl", "hdl cholesterol", "high density lipoprotein"],
        normal_low=50.0,
        normal_high=90.0,
        low_threshold=49.9,
        clinical_significance="Cardioprotective high-density lipoprotein fraction. In women, levels below 50 mg/dL signal increased cardiometabolic risk.",
    ),
    "ldl_cholesterol": BiomarkerReferenceRange(
        biomarker_name="LDL Cholesterol",
        standard_unit="mg/dL",
        canonical_aliases=["ldl", "ldl cholesterol", "low density lipoprotein"],
        normal_low=50.0,
        normal_high=99.0,
        borderline_low=100.0,
        borderline_high=129.0,
        elevated_threshold=130.0,
        clinical_significance="Atherogenic low-density lipoprotein. Optimal target is below 100 mg/dL for metabolic health maintenance.",
    ),
}


# Educational Phenotypic Framework (Rotterdam Consensus, not automated diagnosis)
EDUCATIONAL_PHENOTYPES = {
    "Phenotype A (Classic)": {
        "description": "Demonstrates all three Rotterdam criteria: Hyperandrogenism, Ovulatory dysfunction, and Polycystic ovarian morphology.",
        "required_criteria": [
            RotterdamPillar.HYPERANDROGENISM,
            RotterdamPillar.OVULATORY_DYSFUNCTION,
            RotterdamPillar.POLYCYSTIC_MORPHOLOGY,
        ],
        "metabolic_profile": "Highest prevalence of insulin resistance, central adiposity, and metabolic syndrome risk.",
    },
    "Phenotype B (Non-PCOM)": {
        "description": "Hyperandrogenism and Ovulatory dysfunction without polycystic morphology on pelvic ultrasound.",
        "required_criteria": [
            RotterdamPillar.HYPERANDROGENISM,
            RotterdamPillar.OVULATORY_DYSFUNCTION,
        ],
        "metabolic_profile": "Moderate-to-high metabolic risk similar to Phenotype A.",
    },
    "Phenotype C (Ovulatory)": {
        "description": "Hyperandrogenism and Polycystic ovarian morphology with regular, ovulatory menstrual intervals.",
        "required_criteria": [
            RotterdamPillar.HYPERANDROGENISM,
            RotterdamPillar.POLYCYSTIC_MORPHOLOGY,
        ],
        "metabolic_profile": "Mild-to-moderate metabolic profile; intermediate androgen excess.",
    },
    "Phenotype D (Non-Hyperandrogenic)": {
        "description": "Ovulatory dysfunction and Polycystic ovarian morphology without clinical or biochemical androgen excess.",
        "required_criteria": [
            RotterdamPillar.OVULATORY_DYSFUNCTION,
            RotterdamPillar.POLYCYSTIC_MORPHOLOGY,
        ],
        "metabolic_profile": "Mildest metabolic profile; requires careful exclusionary diagnostic screening for hypothalamic amenorrhea.",
    },
}


# Emergency / Urgent Red-Flag Clinical Signs (Mandates emergency in-person medical evaluation)
URGENT_RED_FLAGS: List[Dict[str, str]] = [
    {
        "id": "acute_pelvic_pain",
        "pattern": r"\b(severe|acute|unbearable|excruciating|sharp)\b.*\b(pelvic pain|ovary pain|abdominal pain|lower belly)\b",
        "concern": "Possible ovarian cyst rupture, ovarian torsion, or pelvic infection requiring immediate surgical/emergency triage.",
        "urgency": "Emergency Medical Evaluation",
        "action": "Seek immediate emergency department or urgent gynecological medical evaluation.",
    },
    {
        "id": "menorrhagia_hemorrhage",
        "pattern": r"\b(bleeding through|soaking through|filling|saturating)\b.*\b(2 pads|two pads|tampon.*hour|clots.*golf ball|huge clots)\b",
        "concern": "Heavy abnormal uterine bleeding / hemorrhagic menorrhagia risking acute anemia or hemodynamic instability.",
        "urgency": "Urgent Clinical Attention",
        "action": "Contact a physician or visit urgent care if saturating more than 2 pads per hour for 2 consecutive hours.",
    },
    {
        "id": "fainting_syncope",
        "pattern": r"\b(fainted|passed out|blacked out|syncope|lightheaded.*bleed)\b",
        "concern": "Hemodynamic compromise or orthostatic instability possibly associated with severe bleeding or acute intra-abdominal pathology.",
        "urgency": "Emergency Medical Evaluation",
        "action": "Call emergency medical services immediately if consciousness was lost or severe dizziness persists.",
    },
]

