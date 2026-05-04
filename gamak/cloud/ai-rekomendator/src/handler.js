'use strict';

const { BedrockRuntimeClient, InvokeModelCommand } = require('@aws-sdk/client-bedrock-runtime');

const REGION = process.env.AWS_REGION || 'eu-central-1';
const MODEL_ID = process.env.BEDROCK_MODEL_ID || 'eu.anthropic.claude-haiku-4-5-20251001-v1:0';

const client = new BedrockRuntimeClient({ region: REGION });

const SYSTEM_PROMPT = `Jestes ekspertem od narzedzi i aplikacji B2B dla malych firm, przedsiebiorcow i freelancerow w Polsce.
Uzytkownik opisuje swoj problem biznesowy. Zaproponuj DOKLADNIE 3 konkretne, realnie istniejace narzedzia.

Zasady:
- Narzedzia dopasowane do SKALI problemu (solo vs zespol) i BUDZETU (jesli user nie poda - preferuj darmowe tiery i niskobudzetowe)
- Uzasadnienie ("why") MUSI odwolywac sie do konkretow z problemu uzytkownika (branza, skala, budzet, jezyk polski, specyficzne wymagania)
- URL musi byc prawdziwy i wskazywac na strone glowna narzedzia
- Opisy po polsku, zwiezlosc

Zwroc TYLKO czysty JSON (bez markdown, bez backticks, bez tekstu wokol), dokladnie w tym formacie:
{
  "recommendations": [
    {
      "name": "Nazwa narzedzia",
      "description": "1 krotkie zdanie co narzedzie robi.",
      "why": "1-2 zdania dlaczego pasuje do TEGO KONKRETNEGO problemu (odwolaj sie do szczegolow).",
      "url": "https://..."
    },
    { ... drugi ... },
    { ... trzeci ... }
  ]
}`;

const CORS_HEADERS = {
  'Content-Type': 'application/json; charset=utf-8',
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};

function respond(statusCode, payload) {
  return {
    statusCode,
    headers: CORS_HEADERS,
    body: JSON.stringify(payload),
  };
}

function extractJson(text) {
  // Haiku czasami dodaje markdown lub tekst wokol - wyciagamy pierwszy obiekt JSON
  const match = text.match(/\{[\s\S]*\}/);
  if (!match) throw new Error('Claude nie zwrocil JSON');
  return JSON.parse(match[0]);
}

function validateRecommendations(recs) {
  if (!Array.isArray(recs) || recs.length !== 3) {
    throw new Error(`Claude zwrocil ${recs?.length ?? 0} rekomendacji zamiast 3`);
  }
  return recs.map((r) => ({
    name: String(r.name || '').trim().slice(0, 100),
    description: String(r.description || '').trim().slice(0, 300),
    why: String(r.why || '').trim().slice(0, 500),
    url: String(r.url || '').trim().slice(0, 300),
  }));
}

async function invokeClaude(problem) {
  const body = {
    anthropic_version: 'bedrock-2023-05-31',
    max_tokens: 1000,
    system: SYSTEM_PROMPT,
    messages: [
      { role: 'user', content: `Problem biznesowy uzytkownika:\n\n${problem}` },
    ],
  };

  const cmd = new InvokeModelCommand({
    modelId: MODEL_ID,
    contentType: 'application/json',
    accept: 'application/json',
    body: JSON.stringify(body),
  });

  const res = await client.send(cmd);
  const raw = new TextDecoder().decode(res.body);
  const parsed = JSON.parse(raw);
  const text = parsed.content?.[0]?.text || '';
  const result = extractJson(text);

  return {
    recommendations: validateRecommendations(result.recommendations),
    usage: parsed.usage,
    stopReason: parsed.stop_reason,
  };
}

exports.recommend = async (event) => {
  let body;
  try {
    body = event.body ? JSON.parse(event.body) : {};
  } catch (err) {
    return respond(400, { error: 'Niepoprawny JSON w body.' });
  }

  const problem = typeof body.problem === 'string' ? body.problem.trim() : '';

  if (problem.length < 10) {
    return respond(400, { error: 'Opisz problem szerzej (min. 10 znakow).' });
  }
  if (problem.length > 2000) {
    return respond(400, { error: 'Opis za dlugi (max 2000 znakow).' });
  }

  const t0 = Date.now();
  try {
    const { recommendations, usage, stopReason } = await invokeClaude(problem);
    const durMs = Date.now() - t0;

    console.log(JSON.stringify({
      event: 'recommend_ok',
      problemLength: problem.length,
      durMs,
      inputTokens: usage?.input_tokens,
      outputTokens: usage?.output_tokens,
      stopReason,
      stage: process.env.STAGE,
    }));

    return respond(200, {
      problem,
      recommendations,
      version: 'bedrock-haiku-v0.2',
      source: 'claude-haiku-4-5',
      stage: process.env.STAGE || 'unknown',
      generatedAt: new Date().toISOString(),
      _meta: {
        durMs,
        inputTokens: usage?.input_tokens,
        outputTokens: usage?.output_tokens,
      },
    });
  } catch (err) {
    const durMs = Date.now() - t0;
    console.error(JSON.stringify({
      event: 'recommend_error',
      message: err.message,
      name: err.name,
      httpStatusCode: err.$metadata?.httpStatusCode,
      durMs,
      problemLength: problem.length,
    }));

    if (err.name === 'ThrottlingException' || err.$metadata?.httpStatusCode === 429) {
      return respond(503, { error: 'Chwilowo za duzo zapytan, sprobuj ponownie za chwile.' });
    }
    if (err.name === 'AccessDeniedException' || err.$metadata?.httpStatusCode === 403) {
      return respond(500, { error: 'Blad uprawnien do modelu (konfiguracja).' });
    }
    return respond(502, { error: 'Nie udalo sie wygenerowac rekomendacji. Sprobuj ponownie.' });
  }
};
