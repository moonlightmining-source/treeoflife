"""
Simplified Skill Loader for Tree of Life AI - Option 3 (Hybrid)
Loads ONE additional specialized skill when needed
Western Medicine is always included in base system prompt
"""

import os
from typing import Optional

SKILLS_DIR = os.path.join(os.path.dirname(__file__), 'skills')

# Skill metadata with trigger keywords
SKILL_MAP = {
    '02-ayurveda-skill.md': {
        'name': 'Ayurveda',
        'keywords': ['ayurveda', 'ayurvedic', 'dosha', 'vata', 'pitta', 'kapha', 'prakriti',
                    'agni', 'ama', 'panchakarma', 'constitution', 'pulse', 'tongue diagnosis']
    },
    '03-tcm-skill.md': {
        'name': 'Traditional Chinese Medicine',
        'keywords': ['tcm', 'chinese medicine', 'acupuncture', 'qi', 'meridian', 'yin', 'yang',
                    'five elements', 'dampness', 'wind', 'cold', 'heat']
    },
    '04-naturopathy-skill.md': {
        'name': 'Naturopathy',
        'keywords': ['naturopathy', 'naturopathic', 'natural healing', 'holistic', 'detox',
                    'hydrotherapy', 'nature cure']
    },
    '05-functional-medicine-skill.md': {
        'name': 'Functional Medicine',
        'keywords': ['functional medicine', 'root cause', 'systems biology', 'autoimmune',
                    'leaky gut', 'microbiome', 'thyroid', 'adrenal', 'hormones']
    },
    '06-clinical-nutrition-skill-part2.md': {
        'name': 'Clinical Nutrition',
        'keywords': ['nutrition', 'diet', 'vitamin', 'mineral', 'supplement', 'nutrient',
                    'eating', 'food', 'keto', 'paleo', 'vegan', 'mediterranean']
    },
    '07-herbal-medicine-skill.md': {
        'name': 'Herbal Medicine',
        'keywords': ['herb', 'herbal', 'botanical', 'plant medicine', 'tincture',
                    'ashwagandha', 'turmeric', 'ginseng', 'chamomile', 'ginger']
    },
    '08-chiropractic-skill.md': {
        'name': 'Chiropractic',
        'keywords': ['chiropractic', 'spine', 'spinal', 'adjustment', 'vertebra',
                    'alignment', 'back pain', 'neck pain', 'posture']
    },
    '11-mind-body-medicine-skill.md': {
        'name': 'Mind-Body Medicine',
        'keywords': ['meditation', 'mindfulness', 'stress', 'anxiety', 'depression',
                    'mental health', 'yoga', 'breathing', 'nervous system', 'trauma']
    },
    '12-sleep-science-skill.md': {
        'name': 'Sleep Science',
        'keywords': ['sleep', 'insomnia', 'circadian', 'melatonin', 'sleep apnea',
                    'rem', 'deep sleep', 'tired', 'fatigue']
    },
    '13-biohacking-longevity-skill.md': {
        'name': 'Biohacking & Longevity',
        'keywords': ['biohacking', 'longevity', 'anti-aging', 'aging', 'lifespan',
                    'optimization', 'nootropic', 'mitochondria', 'nad']
    }
}


def load_skill_file(skill_file: str) -> str:
    """Load a single skill file"""
    filepath = os.path.join(SKILLS_DIR, skill_file)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"⚠️ Error loading {skill_file}: {e}")
        return ""


def detect_specialized_skill(query: str) -> Optional[str]:
    """
    Detect if query needs specialized knowledge beyond Western Medicine
    Returns skill filename or None
    """
    query_lower = query.lower()
    
    # Score each skill
    best_skill = None
    best_score = 0
    
    for skill_file, metadata in SKILL_MAP.items():
        score = 0
        for keyword in metadata['keywords']:
            if keyword in query_lower:
                # Weight longer keywords higher
                score += len(keyword.split())
        
        if score > best_score:
            best_score = score
            best_skill = skill_file
    
    # Only load if we found strong matches (score >= 2)
    if best_score >= 2:
        return best_skill
    
    return None


def get_specialized_knowledge(query: str) -> str:
    """
    Load specialized skill if query requires it
    Returns formatted skill content or empty string
    """
    skill_file = detect_specialized_skill(query)
    
    if not skill_file:
        return ""  # No specialized skill needed
    
    content = load_skill_file(skill_file)
    
    if not content:
        return ""
    
    skill_name = SKILL_MAP[skill_file]['name']
    
    formatted = f"""

{'='*80}
SPECIALIZED KNOWLEDGE - {skill_name.upper()}
{'='*80}

{content}

"""
    
    print(f"🎯 Loading specialized skill: {skill_name}")
    return formatted
