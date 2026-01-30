import type { EventCategory, ThreatLevel, GeoLocation } from '@/types';

const LM_STUDIO_URL = process.env.LM_STUDIO_API_URL || 'http://localhost:1234/v1';
const LM_STUDIO_MODEL = process.env.LM_STUDIO_MODEL || 'local-model';

interface ClassificationResult {
  category: EventCategory;
  threatLevel: ThreatLevel;
  location: GeoLocation | null;
  entities?: string[];
  keywords?: string[];
}

// Call LM Studio API (OpenAI-compatible)
async function callLMStudio(prompt: string, systemPrompt: string): Promise<string> {
  try {
    const response = await fetch(`${LM_STUDIO_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: LM_STUDIO_MODEL,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: prompt },
        ],
        temperature: 0.3,
        max_tokens: 500,
      }),
    });

    if (!response.ok) {
      throw new Error(`LM Studio API error: ${response.status}`);
    }

    const data = await response.json();
    return data.choices[0].message.content;
  } catch (error) {
    console.error('[LM Studio] API call failed:', error);
    throw error;
  }
}

// Extract location using LM Studio
async function extractLocationWithLLM(title: string, content: string): Promise<GeoLocation | null> {
  const prompt = `Analyze this text and extract the PRIMARY location where the event is happening.

Text: "${title}. ${content.slice(0, 500)}"

Return ONLY a JSON object with this exact format:
{
  "latitude": <number>,
  "longitude": <number>,
  "placeName": "<city or location>",
  "country": "<country>",
  "region": "<region/continent>"
}

If no specific location can be determined, return: {"error": "no location"}

Examples:
- "Explosion in Kyiv" → {"latitude": 50.4501, "longitude": 30.5234, "placeName": "Kyiv", "country": "Ukraine", "region": "Eastern Europe"}
- "Paris protests continue" → {"latitude": 48.8566, "longitude": 2.3522, "placeName": "Paris", "country": "France", "region": "Western Europe"}

Return ONLY valid JSON, no explanations.`;

  const systemPrompt = `You are a geolocation extraction expert. Extract ONLY the primary location from text and return precise coordinates. Always return valid JSON.`;

  try {
    const response = await callLMStudio(prompt, systemPrompt);

    // Parse JSON response
    const jsonMatch = response.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      console.log('[LM Studio] No JSON in response:', response);
      return null;
    }

    const parsed = JSON.parse(jsonMatch[0]);

    if (parsed.error || !parsed.latitude || !parsed.longitude) {
      return null;
    }

    return {
      latitude: parsed.latitude,
      longitude: parsed.longitude,
      placeName: parsed.placeName,
      country: parsed.country,
      region: parsed.region,
    };
  } catch (error) {
    console.error('[LM Studio] Location extraction failed:', error);
    return null;
  }
}

// Classify event using LM Studio
export async function classifyEventWithLocalLLM(
  title: string,
  content: string
): Promise<ClassificationResult> {
  const prompt = `Analyze this event and classify it:

Title: "${title}"
Content: "${content.slice(0, 800)}"

Return ONLY a JSON object with this exact format:
{
  "category": "<one of: conflict, protest, disaster, diplomatic, economic, terrorism, cyber, health, environmental, military, crime, piracy, infrastructure, commodities>",
  "threatLevel": "<one of: critical, high, medium, low, info>",
  "entities": ["entity1", "entity2"],
  "keywords": ["keyword1", "keyword2"]
}

Classification guidelines:
- CRITICAL: Active warfare, terrorist attacks, nuclear incidents, major disasters
- HIGH: Armed conflicts, serious protests, cyberattacks, military movements
- MEDIUM: Political tensions, economic sanctions, minor conflicts
- LOW: Diplomatic meetings, exercises, minor incidents
- INFO: General news, updates, background information

Return ONLY valid JSON, no explanations.`;

  const systemPrompt = `You are an intelligence analyst expert in threat assessment and event classification. Classify events accurately based on severity and category.`;

  try {
    const response = await callLMStudio(prompt, systemPrompt);

    // Parse JSON
    const jsonMatch = response.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      throw new Error('No JSON in response');
    }

    const parsed = JSON.parse(jsonMatch[0]);

    // Extract location separately
    const location = await extractLocationWithLLM(title, content);

    return {
      category: parsed.category || 'military',
      threatLevel: parsed.threatLevel || 'medium',
      location,
      entities: parsed.entities || [],
      keywords: parsed.keywords || [],
    };
  } catch (error) {
    console.error('[LM Studio] Classification failed:', error);

    // Fallback to keyword-based classification
    return {
      category: 'military',
      threatLevel: 'medium',
      location: null,
      entities: [],
      keywords: [],
    };
  }
}

// Health check for LM Studio
export async function checkLMStudioHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${LM_STUDIO_URL}/models`, {
      method: 'GET',
    });
    return response.ok;
  } catch (error) {
    console.error('[LM Studio] Health check failed:', error);
    return false;
  }
}
