import os
import random
import anthropic
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cards import TAROT_CARDS

app = FastAPI()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MENU_QUICK_REPLIES = [
    {"label": "Yes/No", "action": "message", "messageText": "Yes/No 타로"},
    {"label": "재회/연애운", "action": "message", "messageText": "재회/연애운 타로"},
    {"label": "직장/금전운", "action": "message", "messageText": "직장/금전운 타로"},
    {"label": "오늘의 타로", "action": "message", "messageText": "오늘의 타로"},
    {"label": "직접 질문", "action": "message", "messageText": "질문 타로"},
]


def draw_three_cards():
    return random.sample(TAROT_CARDS, 3)


def build_claude_prompt(category: str, question: str, cards: list) -> str:
    card_info = "\n".join(
        [f"- {card['name_kr']} ({card['name']}) / 키워드: {card['keywords']}" for card in cards]
    )

    c0 = cards[0]['name_kr']
    c1 = cards[1]['name_kr']
    c2 = cards[2]['name_kr']

    if category == "yes_no":
        format_guide = (
            "[ Yes/No 타로 결과 ]\n\n"
            f"첫 번째 카드 - {c0}\n"
            "(이 카드의 의미를 Yes/No 관점에서 2문장으로 해석)\n\n"
            f"두 번째 카드 - {c1}\n"
            "(이 카드의 의미를 Yes/No 관점에서 2문장으로 해석)\n\n"
            f"세 번째 카드 - {c2}\n"
            "(이 카드의 의미를 Yes/No 관점에서 2문장으로 해석)\n\n"
            "최종 답변: Yes / No / 조건부 Yes\n"
            "(세 카드를 종합해 결론을 내리고 2~3문장으로 조언)"
        )

    elif category == "love":
        format_guide = (
            "[ 재회/연애운 타로 결과 ]\n\n"
            f"현재 감정 - {c0}\n"
            "(상대방 또는 본인의 현재 감정 상태를 2~3문장으로 해석)\n\n"
            f"관계의 흐름 - {c1}\n"
            "(두 사람 사이의 현재 에너지와 흐름을 2~3문장으로 해석)\n\n"
            f"앞으로의 가능성 - {c2}\n"
            "(재회 또는 새로운 사랑의 가능성을 2~3문장으로 해석)\n\n"
            "종합 메시지\n"
            "(연애운 전체를 종합한 따뜻한 조언을 3~4문장으로)"
        )

    elif category == "career":
        format_guide = (
            "[ 직장/금전운 타로 결과 ]\n\n"
            f"현재 상황 - {c0}\n"
            "(직장 또는 금전 관련 현재 상황을 2~3문장으로 해석)\n\n"
            f"장애물/기회 - {c1}\n"
            "(앞에 놓인 도전이나 기회를 2~3문장으로 해석)\n\n"
            f"결과/방향 - {c2}\n"
            "(앞으로의 직장/금전 흐름을 2~3문장으로 해석)\n\n"
            "종합 메시지\n"
            "(직장과 금전운 전체를 종합한 실용적인 조언을 3~4문장으로)"
        )

    elif category == "daily":
        format_guide = (
            "[ 오늘의 타로 결과 ]\n\n"
            f"오전의 에너지 - {c0}\n"
            "(오전에 집중할 에너지와 태도를 2~3문장으로)\n\n"
            f"오늘의 핵심 - {c1}\n"
            "(오늘 하루 가장 중요한 메시지를 2~3문장으로)\n\n"
            f"오늘의 마무리 - {c2}\n"
            "(오늘 하루를 어떻게 마무리할지 2~3문장으로)\n\n"
            "오늘의 한마디\n"
            "(오늘 하루를 위한 짧고 힘이 되는 메시지)"
        )

    else:
        format_guide = (
            "[ 타로 리딩 결과 ]\n\n"
            f"과거 - {c0}\n"
            "(과거 위치에서의 해석을 2~3문장으로)\n\n"
            f"현재 - {c1}\n"
            "(현재 위치에서의 해석을 2~3문장으로)\n\n"
            f"미래 - {c2}\n"
            "(미래 위치에서의 해석을 2~3문장으로)\n\n"
            "종합 메시지\n"
            "(전체 흐름과 조언을 3~4문장으로)"
        )

    prompt = (
        "당신은 따뜻하고 통찰력 있는 타로 리더입니다.\n\n"
        f"질문: {question}\n\n"
        f"뽑힌 카드:\n{card_info}\n\n"
        f"다음 형식으로 한국어로 답해주세요:\n\n{format_guide}\n\n"
        "답변은 공감적이고 희망적인 톤으로 작성해주세요. "
        "너무 단정 짓지 말고 가능성을 열어두는 표현을 사용하세요."
    )

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

        if "Yes/No" in utterance or "yes/no" in utterance:
            category = "yes_no"
            question = "이 상황에서 Yes일까요, No일까요?"

        elif "재회" in utterance or "연애운" in utterance:
            category = "love"
            question = "재회 가능성과 연애운은 어떤가요?"

        elif "직장" in utterance or "금전운" in utterance:
            category = "career"
            question = "직장운과 금전운은 어떤가요?"

        elif "오늘" in utterance:
            category = "daily"
            question = "오늘 나의 하루는 어떤가요?"

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
            question = "오늘 나의 하루는 어떤가요?"

        cards = draw_three_cards()
        reading = get_tarot_reading(category, question, cards)

        card_names = " | ".join([card['name_kr'] for card in cards])
        full_text = f"{card_names}\n\n{reading}"

        return JSONResponse(kakao_text_response(full_text))

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return JSONResponse(
            kakao_error_response("타로 리딩 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        )


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "타로봇 서버 정상 작동 중"}
