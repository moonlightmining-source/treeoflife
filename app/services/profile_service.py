"""
Profile Service - Constitutional Assessment
"""
import logging
from typing import Dict, Any

from app.config import CONSTITUTIONAL_QUESTIONS

logger = logging.getLogger(__name__)


class ProfileService:
    """Service for health profile and constitutional assessment"""
    
    def __init__(self):
        """Initialize profile service"""
        logger.info("Profile service initialized")
    
    def calculate_dosha(self, answers: Dict[str, str]) -> Dict[str, Any]:
        """
        Calculate Ayurvedic dosha from questionnaire answers
        
        Args:
            answers: Dict of question_id -> dosha_answer
            
        Returns:
            Dict with primary dosha and scores
        """
        scores = {"vata": 0, "pitta": 0, "kapha": 0}
        
        # Count answers for each dosha
        for answer in answers.values():
            if answer in scores:
                scores[answer] += 1
        
        # Determine primary dosha
        primary_dosha = max(scores, key=scores.get)
        total = sum(scores.values())
        
        # Calculate percentages
        percentages = {
            dosha: round((score / total * 100) if total > 0 else 0, 1)
            for dosha, score in scores.items()
        }
        
        # Check if dual dosha (close scores)
        sorted_doshas = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if sorted_doshas[0][1] - sorted_doshas[1][1] <= 1:
            primary_dosha = f"{sorted_doshas[0][0]}-{sorted_doshas[1][0]}"
        
        logger.info(f"Calculated dosha: {primary_dosha} (scores: {scores})")
        
        return {
            "primary_dosha": primary_dosha,
            "scores": scores,
            "percentages": percentages
        }
    
    def get_questions(self) -> Dict[str, Any]:
        """
        Get constitutional assessment questions
        
        Returns:
            Dict with questions for assessment
        """
        return CONSTITUTIONAL_QUESTIONS
    
    def get_dosha_recommendations(self, dosha: str) -> Dict[str, Any]:
        """
        Get recommendations based on dosha
        
        Args:
            dosha: Ayurvedic dosha type
            
        Returns:
            Dict with dietary, lifestyle, and herbal recommendations
        """
        recommendations = {
            "vata": {
                "diet": [
                    "Warm, cooked foods",
                    "Healthy fats (ghee, olive oil)",
                    "Sweet, sour, salty tastes",
                    "Avoid: cold, raw, dry foods"
                ],
                "lifestyle": [
                    "Regular daily routine",
                    "Adequate rest and sleep",
                    "Calming activities (yoga, meditation)",
                    "Stay warm"
                ],
                "herbs": [
                    "Ashwagandha",
                    "Brahmi",
                    "Ginger",
                    "Cinnamon"
                ]
            },
            "pitta": {
                "diet": [
                    "Cooling foods",
                    "Sweet, bitter, astringent tastes",
                    "Plenty of water",
                    "Avoid: spicy, acidic, fried foods"
                ],
                "lifestyle": [
                    "Avoid overheating",
                    "Moderate exercise",
                    "Relaxation and leisure",
                    "Time in nature"
                ],
                "herbs": [
                    "Aloe vera",
                    "Coriander",
                    "Fennel",
                    "Rose"
                ]
            },
            "kapha": {
                "diet": [
                    "Light, warm, spicy foods",
                    "Pungent, bitter, astringent tastes",
                    "Reduce: dairy, sweets, heavy foods",
                    "Favor: vegetables, legumes"
                ],
                "lifestyle": [
                    "Regular vigorous exercise",
                    "Stay active and engaged",
                    "Avoid oversleeping",
                    "Stimulating activities"
                ],
                "herbs": [
                    "Ginger",
                    "Turmeric",
                    "Black pepper",
                    "Cinnamon"
                ]
            }
        }
        
        # Handle dual doshas
        if "-" in dosha:
            primary = dosha.split("-")[0]
            return recommendations.get(primary, {})
        
        return recommendations.get(dosha, {})


# Singleton instance
profile_service = ProfileService()
