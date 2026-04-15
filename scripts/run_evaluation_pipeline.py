from dotenv import load_dotenv

load_dotenv()

import json
from app.services.agent import fitting_agent
from app.services.langfuse_client import create_trace, score


def evaluate():
    with open("data/evaluation_data/eval_data.json") as f:
        eval_data = json.load(f)

    for case in eval_data:
        print(f"\nRunning {case['id']} - {case['description']}")

        input_data = case["input"]
        expected = case["expected_recommendations"]

        result = fitting_agent.run_sync(input_data)
        response = result.output

        predicted = {
            item.item_id: item.recommended_size
            for item in response.recommendations
        }

        correct = 0
        total = len(expected)

        for item_id, expected_size in expected.items():
            pred_size = predicted.get(item_id)
            if pred_size == expected_size:
                correct += 1

        accuracy = correct / total

        print(f"Accuracy: {accuracy:.2f} ({correct}/{total})")

        trace_id = create_trace(
            name="fitting_room_recommendation",
            input=input_data,
        )

        score(
            trace_id=trace_id,
            name="accuracy",
            value=accuracy,
        )


if __name__ == "__main__":
    evaluate()