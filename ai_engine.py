"""
AI Engine — Core intelligence layer powered by Groq (ultra-fast inference).

Handles recipe generation, matching, and substitution suggestions
in a SINGLE API call for maximum speed.
"""

import json
import re
import time
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

# We initialize the client lazily to prevent crashing the server on boot if the key is missing
_client = None

def get_client():
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set. Please add it to the environment variables.")
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def _call_groq(system_prompt, user_prompt, temperature=0.4, max_tokens=8000, retries=3):
    """Call Groq API with automatic retry on rate-limit errors."""
    for attempt in range(retries):
        try:
            response = get_client().chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content.strip()
            # Clean up any stray markdown fences
            result_text = re.sub(r"^```(?:json)?\s*", "", result_text)
            result_text = re.sub(r"\s*```$", "", result_text)
            return json.loads(result_text)

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate_limit" in error_str.lower():
                wait_time = (attempt + 1) * 5  # 5s, 10s, 15s (Groq resets fast)
                print(f"[AI Engine] Rate limited. Waiting {wait_time}s (attempt {attempt + 1}/{retries})...")
                time.sleep(wait_time)
                continue
            raise e

    raise Exception("Rate limit exceeded after retries. Please try again shortly.")


# ── Single unified prompt — recipes + substitutions in one call ──

SYSTEM_PROMPT = """You are an expert chef and food scientist.
You help users find recipes based on ingredients they have, identify what's missing,
and suggest practical substitutes — all in one response.

CRITICAL RULES:
1. Respond with ONLY valid JSON.
2. Return exactly 4 recipes.
3. Rank by match_score (% of essential ingredients the user has).
4. Include diverse cuisines.
5. Every recipe must have complete cooking steps.
6. For EACH missing essential ingredient, include 1-2 substitute suggestions.
7. Be practical — real recipes, real substitutes."""

PROMPT_TEMPLATE = """The user has these ingredients: {ingredients}

Find 4 recipes. For each recipe:
- Calculate match_score = (available essential ingredients / total essential ingredients) * 100
- Only include recipes with match_score >= 40
- Mark each ingredient as available or missing
- For each MISSING essential ingredient, suggest 1-2 substitutes with suitability_score (1-10)

Return this exact JSON:
{{
  "recipes": [
    {{
      "name": "Recipe Name",
      "cuisine_type": "Indian/Chinese/Italian/Continental/Mexican/etc",
      "description": "Brief 1-2 sentence description",
      "match_score": 85,
      "prep_time_minutes": 10,
      "cooking_time_minutes": 20,
      "total_time_minutes": 30,
      "difficulty_level": "Easy/Medium/Hard",
      "servings": 2,
      "ingredients": [
        {{
          "name": "Ingredient Name",
          "amount": 2.0,
          "unit": "tablespoons",
          "original_string": "2 tablespoons",
          "is_optional": false,
          "is_available": true
        }}
      ],
      "substitutions": {{
        "Missing Ingredient Name": [
          {{
            "name": "Substitute Name",
            "suitability_score": 8,
            "adjustment_note": "Brief usage note"
          }}
        ]
      }},
      "steps": [
        "Step 1 in clear, simple language.",
        "Step 2..."
      ]
    }}
  ]
}}

IMPORTANT:
- "is_available": true if ingredient is in user's list, false otherwise
- Sort by match_score descending
- "amount" MUST be a pure number (e.g. 2.5, 1) or null if "to taste"
- "unit" MUST be the unit string (e.g. "cups", "tbsp") or empty string
- Write beginner-friendly steps with timing info
- substitutions only for missing NON-optional ingredients
- If an ingredient has no good substitute, omit it from substitutions"""


def process_pipeline(ingredients: list[str]) -> dict:
    """
    Run the complete 5-module pipeline in a SINGLE API call:
    1. Validate ingredients
    2. Find matching recipes
    3. Identify missing ingredients
    4. Suggest substitutions
    5. Return enriched data for display
    """
    prompt = PROMPT_TEMPLATE.format(
        ingredients=", ".join(ingredients)
    )

    try:
        return _call_groq(SYSTEM_PROMPT, prompt, temperature=0.4, max_tokens=8000)
    except json.JSONDecodeError as e:
        print(f"[AI Engine] JSON parse error: {e}")
        return {"recipes": [], "error": "Failed to parse AI response"}
    except Exception as e:
        print(f"[AI Engine] API error: {e}")
        return {"recipes": [], "error": str(e)}
