import json

def _normalize(result):
    if result is None:
        return []
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            return []
    if isinstance(result, dict):
        result = result.get('result', [])
    items = []
    for item in result or []:
        if isinstance(item, dict):
            items.append({'content': str(item.get('content') or ''), 'score': item.get('score') if isinstance(item.get('score'), (int, float)) else None, 'title': str(item.get('title') or '')})
    return items

def _headline(content: str) -> tuple[str, str]:
    first, _, rest = content.partition('\n')
    if '｜' in first and len(first) < 200:
        return (first, rest)
    return ('', content)

def main(result=None) -> dict:
    items = _normalize(result)
    if not items:
        text = '（本次未检索到课程知识条目，不得虚构编号或页码）'
        return {'evidence_text': text, 'evidence_json': '[]'}
    lines = []
    for index, item in enumerate(items, start=1):
        headline, body = _headline(item['content'])
        score = f"（相关度 {item['score']:.2f}）" if item['score'] is not None else ''
        body = ' '.join(body.split())
        lines.append(f"{index}. {headline}\n   {body[:400]}{('…' if len(body) > 400 else '')}{score}")
    return {'evidence_text': '\n'.join(lines), 'evidence_json': json.dumps(items, ensure_ascii=False)}
BUILD = '2026-11-17.2'
