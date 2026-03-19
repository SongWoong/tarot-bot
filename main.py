import os
import random
import anthropic
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cards import TAROT_CARDS

app = FastAPI()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

POSITIONS = ["과거", "현재", "미래"]

MENU_QUICK_REPLIES = [
    {"label": "⚖️ Yes/No", "action": "message", "messageText": "Yes/No 타로"},
    {"label": "💕 재회/연애운", "action": "message", "messageText": "재회/연애운 타로"},
    {"label": "💼 직장/금전운", "action": "message", "messageText": "직장/금전운 타로"},
    {"label": "🔮 오늘의 타로", "action": "message", "messageText": "오늘의 타로"},
    {"label": "❓ 직접 질문", "action": "message", "messageText": "질문 타로"},
]

CATEGORY_PROMPTS = {
    "yes_no": {
        "question": "이 상황에서 Yes일까요, No일까요?",
        "instruction": """카드 3장을 뽑아 Yes/No 타로를 해석해주세요.

형식:
🃏 Yes/No 타로 결과

⬅️ 첫 번째 카드 — {card0}
(이 카드의 의미를 Yes/No 관점에서 2문장으로 해석)

🔮 두 번째 카드 — {card1}
(이 카드의 의미를 Yes/No 관점에서 2문장으로 해석)

➡️ 세 번째 카드 — {card2}
(이 카드의 의미를 Yes/No 관점에서 2문장으로 해석)

✨ 최종 답변: Yes / No / 조건부 Yes
(세 카드를 종합해 결론을 내리고 2~3문장으로 조언)"""
    },
    "love": {
        "question": "재회 가능성과 연애운은 어떤가요?",
        "instruction": """연애운과 재회 가능성에 집중하여 쓰리카드 스프레드로 타로를 해석해주세요.

형식:
💕 재회/연애운 타로 결과

⬅️ 현재 감정 — {card0}
(상대방 또는 본인의 현재 감정 상태를 2~3문장으로 해석)

🔮 관계의 흐름 — {card1}
(두 사람 사이의 현재 에너지와 흐름을 2~3문장으로 해석)

➡️ 앞으로의 가능성 — {card2}
(재회 또는 새로운 사랑의 가능성을 2~3문장으로 해석)

✨ 종합 메시지
(연애운 전체를 종합한 따뜻한 조언을 3~4문장으로)"""
    },
    "career": {
        "question": "직장운과 금전운은 어떤가요?",
        "instruction": """직장운과 금전운에 집중하여 쓰리카드 스프레드로 타로를 해석해주세요.

형식:
💼 직장/금전운 타로 결과

⬅️ 현재 상황 — {card0}
(직장 또는 금전 관련 현재 상황을 2~3문장으로 해석)

🔮 장애물/기회 — {card1}
(앞에 놓인 도전이나 기회를 2~3문장으로 해석)

➡️ 결과/방향 — {card2}
(앞으로의 직장/금전 흐름을 2~3문장으로 해석)

✨ 종합 메시지
(직장과 금전운 전체를 종합한 실용적인 조언을 3~4문장으로)"""
    },
    "daily": {
        "question": "오늘 나의 하루는 어떤가요?",
        "instruction": """오늘 하루의 에너지에 집중하여 쓰리카드 스프레드로 타로를 해석해주세요.

형식:
🌟 오늘의 타로 결과

⬅️ 오전의 에너지 — {card0}
(오전에 집중할 에너지와 태도를 2~3문장으로)

🔮 오늘의 핵심 — {card1}
(오늘 하루 가장 중요한 메시지를 2~3문장으로)

➡️ 오늘의 마무리 — {card2}
(오늘 하루를 어떻게 마무리할지 2~3문장으로)

✨ 오늘의 한마디
(오늘 하루를 위한 짧고 힘이 되는 메시지)"""
    },
}


def draw_three_cards():
    return random.sample(TAROT_CARDS, 3)


def build_claude_prompt(category: str, question: str, cards: list) -> str:
    card_info = "\n".join(
        [f"- {card['name_kr']} ({card['name']}) — 키워드: {card['keywords']}" for card in cards]
    )

    if category in CATEGORY_PROMPTS:
        instruction = CATEGORY_PROMPTS[category]["instruction"].format(
            card0=cards[0]['name_kr'],
            card1=cards[1]['name_kr'],
            card2=cards[2]['name_kr'],
        )
    else:
        instruction = f"""쓰리카드 스프레드로 타로를 해석해주세요.

형식:
🃏 타로 리딩 결과

⬅️ 과거 — {cards[0]['name_kr']}
(과거 위치에서의 해석을 2~3문장으로)

🔮 현재 — {cards[1]['name_kr']}
(현재 위치에서의 해석을 2~3문장으로)

➡️ 미래 — {cards[2]['name_kr']}
(미래 위치에서의 해석을 2~3문장으로)

✨ 종합 메시지
(전체 흐름과 조언을 3~4문장으로)"""

    prompt = f"""당신은 따뜻하고 통찰력 있는 타로 리더입니다.

질문: {question}

뽑힌 카드:
{card_info}

{instruction}

답변은 공감적이고 희망적인 톤으로 작성해주세요. 너무 단정 짓지 말고 가능성을 열어두는 표현을 사용하세요."""

    return prompt


def get_tarot_reading(category: str, question: str, cards: list) -> str:
    prompt = build_claude_prompt(category, question, cards)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def kakao_text_response(text: str) -> dict:
    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": text}}],
            "quickReplies": MENU_QUICK_REPLIES,
        },
    }


def kakao_error_response(msg: str) -> dict:
    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": msg}}],
            "quickReplies": MENU_QUICK_REPLIES,
        },
    }


@app.post("/tarot")
async def tarot_webhook(request: Request):
    try:
        body = await request.json()
        utterance = body.get("userRequest", {}).get("utterance", "").strip()

        # 카테고리 분류
        if "Yes/No" in utterance or "yes/no" in utterance:
            category = "yes_no"
            question = CATEGORY_PROMPTS["yes_no"]["question"]

        elif "재회" in utterance or "연애운" in utterance:
            category = "love"
            question = CATEGORY_PROMPTS["love"]["question"]

        elif "직장" in utterance or "금전운" in utterance:
            category = "career"
            question = CATEGORY_PROMPTS["career"]["question"]

        elif "오늘" in utterance:
            category = "daily"
            question = CATEGORY_PROMPTS["daily"]["question"]

        elif utterance.startswith("질문 타로"):
            category = "custom"
            question = utterance.replace("질문 타로", "").strip()
            if not question:
                return JSONResponse(
                    kakao_error_response(
                        "질문을 입력해주세요.\n예시: 질문 타로 요즘 연애운이 어떤가요?"
                    )
                )
        else:
            category = "daily"
            question = CATEGORY_PROMPTS["daily"]["question"]

        cards = draw_three_cards()
        reading = get_tarot_reading(category, question, cards)

        card_names = " | ".join([card['name_kr'] for card in cards])
        full_text = f"🎴 {card_names}\n\n{reading}"

        return JSONResponse(kakao_text_response(full_text))

    except Exception as e:
        return JSONResponse(
            kakao_error_response("타로 리딩 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        )


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "타로봇 서버 정상 작동 중"}
