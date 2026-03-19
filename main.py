import os
import random
import anthropic
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cards import TAROT_CARDS

app = FastAPI()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

POSITIONS = ["과거", "현재", "미래"]

SPREAD_MEANINGS = {
    "과거": "이 상황의 배경과 원인",
    "현재": "지금 이 순간의 상태",
    "미래": "앞으로 나아갈 방향",
}


def draw_three_cards():
    return random.sample(TAROT_CARDS, 3)


def build_claude_prompt(question: str, cards: list) -> str:
    card_info = ""
    for i, (card, position) in enumerate(zip(cards, POSITIONS)):
        card_info += f"- {position} ({SPREAD_MEANINGS[position]}): {card['name_kr']} ({card['name']}) — 키워드: {card['keywords']}\n"

    prompt = f"""당신은 따뜻하고 통찰력 있는 타로 리더입니다.
사용자의 질문에 대해 쓰리카드 스프레드로 타로 해석을 해주세요.

질문: {question}

뽑힌 카드:
{card_info}

다음 형식으로 한국어로 답해주세요:

🃏 타로 리딩 결과

⬅️ 과거 — {cards[0]['name_kr']}
(이 카드가 과거 위치에서 질문과 어떤 의미인지 2~3문장으로 따뜻하게 해석)

🔮 현재 — {cards[1]['name_kr']}
(이 카드가 현재 위치에서 질문과 어떤 의미인지 2~3문장으로 따뜻하게 해석)

➡️ 미래 — {cards[2]['name_kr']}
(이 카드가 미래 위치에서 질문과 어떤 의미인지 2~3문장으로 따뜻하게 해석)

✨ 종합 메시지
(세 카드를 연결하여 전체적인 흐름과 조언을 3~4문장으로 마무리)

답변은 공감적이고 희망적인 톤으로 작성해주세요. 너무 단정 짓지 말고 가능성을 열어두는 표현을 사용하세요."""

    return prompt


def get_tarot_reading(question: str, cards: list) -> str:
    prompt = build_claude_prompt(question, cards)
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
            "outputs": [
                {"simpleText": {"text": text}}
            ],
            "quickReplies": [
                {
                    "label": "🔮 다시 뽑기",
                    "action": "message",
                    "messageText": "타로 카드 뽑기",
                },
                {
                    "label": "❓ 질문하기",
                    "action": "message",
                    "messageText": "질문 타로",
                },
            ],
        },
    }


def kakao_error_response(message: str) -> dict:
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {"simpleText": {"text": message}}
            ]
        },
    }


@app.post("/tarot")
async def tarot_webhook(request: Request):
    try:
        body = await request.json()
        utterance = body.get("userRequest", {}).get("utterance", "").strip()

        # 질문 타로: "질문 타로 [질문내용]" 형식
        if utterance.startswith("질문 타로"):
            question = utterance.replace("질문 타로", "").strip()
            if not question:
                return JSONResponse(
                    kakao_error_response(
                        "질문을 입력해주세요.\n예시: 질문 타로 요즘 연애운이 어떤가요?"
                    )
                )
        else:
            # 기본: 일반 타로 뽑기
            question = "오늘 나의 하루는 어떤가요?"

        cards = draw_three_cards()
        reading = get_tarot_reading(question, cards)

        card_names = " | ".join(
            [f"{pos}: {card['name_kr']}" for pos, card in zip(POSITIONS, cards)]
        )
        full_text = f"🎴 {card_names}\n\n{reading}"

        return JSONResponse(kakao_text_response(full_text))

    except Exception as e:
        return JSONResponse(
            kakao_error_response("타로 리딩 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        )


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "타로봇 서버 정상 작동 중"}
