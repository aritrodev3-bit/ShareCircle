import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/utils/supabase/server';
import { redis } from '@/lib/redis';

export async function POST(req: NextRequest) {
  try {
    // 1. Supabase Session Check (401)
    const supabase = await createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
    const userId = session.user.id;

    // 2. Request Body Validation (400)
    let body;
    try {
      body = await req.json();
    } catch {
      return NextResponse.json({ error: 'Invalid JSON request body' }, { status: 400 });
    }
    const { title, notes } = body;
    if (!title || typeof title !== 'string' || title.trim() === '') {
      return NextResponse.json({ error: 'Title is required' }, { status: 400 });
    }

    // 3. Redis Rate Limiting Check
    const dateStr = new Date().toISOString().split('T')[0]; // YYYY-MM-DD in UTC
    const redisKey = `ai_rate:${userId}:${dateStr}`;
    const dailyLimit = parseInt(process.env.AI_DAILY_RATE_LIMIT || '10', 10);

    // Pre-check limit
    const currentCountStr = await redis.get(redisKey);
    const currentCount = currentCountStr ? parseInt(currentCountStr, 10) : 0;
    if (currentCount >= dailyLimit) {
      return NextResponse.json({ error: 'Daily AI limit reached' }, { status: 429 });
    }

    // Incremental occupant slot (Atomic check & increment check)
    const newCount = await redis.incr(redisKey);
    if (newCount === 1) {
      await redis.expire(redisKey, 86400); // 24 hours in seconds
    }
    if (newCount > dailyLimit) {
      // Exceeded concurrently. Refund and reject.
      await redis.decr(redisKey);
      return NextResponse.json({ error: 'Daily AI limit reached' }, { status: 429 });
    }

    // 4. OpenRouter Call
    const openrouterApiKey = process.env.OPENROUTER_API_KEY;
    if (!openrouterApiKey) {
      // If API key is not configured, decrement Redis and return 503
      await redis.decr(redisKey);
      return NextResponse.json({ error: 'OpenRouter API key is not configured' }, { status: 503 });
    }

    const openrouterBaseUrl = process.env.OPENROUTER_BASE_URL || 'https://openrouter.ai/api/v1';
    const openrouterModel = process.env.OPENROUTER_MODEL || 'google/gemma-2-9b-it:free';

    const systemPrompt = `You are a helpful assistant for a community donation platform called GiveCircle.
Your job is to generate a clear, honest item description for a donated item and suggest the most appropriate category and condition.
Always respond with valid JSON only. No markdown, no explanation, no extra text.`;

    const userPrompt = `Item title: ${title}
Additional notes: ${notes || 'none'}

Respond with JSON in exactly this format:
{
  "description": "2-4 sentence description of the item",
  "category": one of [clothing, furniture, electronics, books, kitchen, toys, medical, other],
  "condition": one of [new, like_new, good, fair]
}`;

    let response;
    try {
      response = await fetch(`${openrouterBaseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${openrouterApiKey}`,
          'HTTP-Referer': 'https://givecircle.org',
          'X-Title': 'GiveCircle',
        },
        body: JSON.stringify({
          model: openrouterModel,
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userPrompt },
          ],
          response_format: { type: 'json_object' },
        }),
      });
    } catch (fetchErr) {
      console.error('Fetch error targeting OpenRouter:', fetchErr);
      await redis.decr(redisKey);
      return NextResponse.json({ error: 'OpenRouter is unreachable' }, { status: 503 });
    }

    if (!response.ok) {
      console.error(`OpenRouter returned status ${response.status}`);
      await redis.decr(redisKey);
      return NextResponse.json({ error: 'OpenRouter returned an error' }, { status: 503 });
    }

    let completionData;
    try {
      completionData = await response.json();
    } catch (jsonErr) {
      console.error('Failed to parse OpenRouter completion data:', jsonErr);
      await redis.decr(redisKey);
      return NextResponse.json({ error: 'OpenRouter returned malformed data' }, { status: 503 });
    }

    const content = completionData.choices?.[0]?.message?.content;
    if (!content) {
      console.error('No content returned from OpenRouter choices');
      await redis.decr(redisKey);
      return NextResponse.json({ error: 'OpenRouter returned empty response' }, { status: 503 });
    }

    // 5. Output Validation (422)
    let aiResponse;
    try {
      // Remove possible markdown formatting if the model ignored response_format
      const cleanContent = content.replace(/^```json\s*/i, '').replace(/```$/, '').trim();
      aiResponse = JSON.parse(cleanContent);
    } catch (parseErr) {
      console.error('Failed to parse OpenRouter assistant content:', parseErr);
      await redis.decr(redisKey);
      return NextResponse.json({ error: 'OpenRouter response is not valid JSON' }, { status: 422 });
    }

    const { description, category, condition } = aiResponse;

    const validCategories = ['clothing', 'furniture', 'electronics', 'books', 'kitchen', 'toys', 'medical', 'other'];
    const validConditions = ['new', 'like_new', 'good', 'fair'];

    if (
      !description ||
      typeof description !== 'string' ||
      description.trim() === '' ||
      !category ||
      !validCategories.includes(category) ||
      !condition ||
      !validConditions.includes(condition)
    ) {
      console.error('AI response validation failed:', aiResponse);
      await redis.decr(redisKey);
      return NextResponse.json({ error: 'OpenRouter response does not conform to expected schema' }, { status: 422 });
    }

    // Return successfully
    return NextResponse.json({
      description: description.trim(),
      category,
      condition,
    });
  } catch (globalErr) {
    console.error('Global error inside describe-item route:', globalErr);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
