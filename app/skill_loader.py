"""
Skill Loader v3 - Hybrid Dynamic Loading System
Loads 1 specialized skill based on query keywords
Western Medicine is always embedded in enhanced_system_prompt.py
"""

import os

# Map of specialized skills with their trigger keywords
SKILL_MAP = {
    'ayurveda': {
        'file': '02-ayurveda-skill.md',
        'keywords': ['ayurveda', 'ayurvedic', 'dosha', 'vata', 'pitta', 'kapha', 'prakruti', 'vikruti', 'agni', 'ama', 'ojas', 'tejas', 'prana']
    },
    'tcm': {
        'file': '03-tcm-skill.md',
        'keywords': ['tcm', 'traditional chinese medicine', 'qi', 'chi', 'meridian', 'acupuncture', 'yin', 'yang', 'five elements', 'zang fu', 'tongue diagnosis', 'pulse diagnosis']
    },
    'naturopathy': {
        'file': '04-naturopathy-skill.md',
        'keywords': ['naturopathy', 'naturopathic', 'vis medicatrix naturae', 'hydrotherapy', 'constitutional hydrotherapy', 'detox', 'detoxification', 'cleanse']
    },
    'functional_medicine': {
        'file': '05-functional-medicine-skill.md',
        'keywords': ['functional medicine', 'root cause', 'systems biology', 'antecedents', 'triggers', 'mediators', 'comprehensive', 'integrative', 'personalized medicine', 'precision medicine']
    },
    'clinical_nutrition': {
        'file': '06-clinical-nutrition-skill-part2.md',
        'keywords': ['nutrition', 'diet', 'nutritional', 'micronutrient', 'macronutrient', 'food', 'eating', 'meal', 'supplement', 'vitamin', 'mineral', 'protein', 'carbohydrate', 'fat']
    },
    'herbal_medicine': {
        'file': '07-herbal-medicine-skill.md',
        'keywords': ['herbal', 'herb', 'botanical', 'phytotherapy', 'plant medicine', 'tincture', 'tea', 'decoction', 'extract', 'adaptogen']
    },
    'chiropractic': {
        'file': '08-chiropractic-skill.md',
        'keywords': ['chiropractic', 'chiropractor', 'spinal', 'spine', 'adjustment', 'manipulation', 'subluxation', 'vertebra', 'vertebrae', 'alignment']
    },
    'physical_therapy': {
        'file': '09-physical-therapy-skill.md',
        'keywords': ['physical therapy', 'physiotherapy', 'pt', 'rehabilitation', 'rehab', 'mobility', 'movement', 'injury recovery', 'range of motion', 'rom', 'strength training', 'therapeutic exercise', 'manual therapy', 'sports injury', 'post-surgical', 'gait', 'balance']
    },
    'mind_body': {
        'file': '11-mind-body-medicine-skill.md',
        'keywords': ['mind-body', 'mindfulness', 'meditation', 'stress', 'anxiety', 'breathwork', 'breathing', 'relaxation', 'yoga', 'tai chi', 'qigong', 'vagus nerve']
    },
    'sleep': {
        'file': '12-sleep-science-skill.md',
        'keywords': ['sleep', 'insomnia', 'circadian', 'melatonin', 'sleep hygiene', 'sleep apnea', 'rest', 'fatigue', 'tired', 'exhausted']
    },
    'biohacking': {
        'file': '13-biohacking-longevity-skill.md',
        'keywords': ['biohacking', 'longevity', 'anti-aging', 'lifespan', 'healthspan', 'senescence', 'autophagy', 'fasting', 'intermittent fasting', 'cold exposure', 'heat exposure', 'sauna']
    }
}

SKILLS_DIR = '/app/skills'


def detect_specialized_skill(query: str) -> str:
    """
    Analyze query and return the best matching skill name.
    Returns empty string if no strong match (score < 2).
    
    Args:
        query: The user's message/question
        
    Returns:
        Skill name (e.g., 'ayurveda') or empty string
    """
    query_lower = query.lower()
    scores = {}
    
    # Score each skill based on keyword matches
    for skill_name, skill_info in SKILL_MAP.items():
        score = 0
        for keyword in skill_info['keywords']:
            if keyword in query_lower:
                score += 1
        
        if score > 0:
            scores[skill_name] = score
    
    # Return skill with highest score if score >= 2
    if scores:
        best_skill = max(scores, key=scores.get)
        if scores[best_skill] >= 2:
            return best_skill
        # If highest score is 1, still return it (single strong keyword match)
        elif scores[best_skill] == 1:
            return best_skill
    
    return ''


def get_specialized_knowledge(query: str) -> str:
    """
    Load specialized skill file if query matches keywords.
    
    Args:
        query: The user's message/question
        
    Returns:
        Skill file content as string, or empty string if no match
    """
    skill_name = detect_specialized_skill(query)
    
    if not skill_name:
        return ''
    
    skill_file = SKILL_MAP[skill_name]['file']
    file_path = os.path.join(SKILLS_DIR, skill_file)
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"⚠️ Skill file not found: {file_path}")
        return ''
    
    # Load and return file content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"🎯 Loading specialized skill: {skill_name.replace('_', ' ').title()}")
        
        # Wrap in clear delimiters for the system prompt
        return f"\n\n{'='*80}\nSPECIALIZED KNOWLEDGE: {skill_name.upper()}\n{'='*80}\n\n{content}\n\n{'='*80}\n"
    
    except Exception as e:
        print(f"❌ Error loading skill file {skill_file}: {e}")
        return ''


# For testing
if __name__ == "__main__":
    # Test queries
    test_queries = [
        "What are the three doshas in Ayurveda?",
        "Tell me about qi meridians in TCM",
        "What supplements help with inflammation?",
        "I need physical therapy for my knee injury",
        "How can I improve my sleep?",
        "What is biohacking?",
        "Tell me about diabetes treatment"
    ]
    
    for query in test_queries:
        skill = detect_specialized_skill(query)
        print(f"\nQuery: {query}")
        print(f"Detected skill: {skill or 'None (Western Medicine only)'}")
