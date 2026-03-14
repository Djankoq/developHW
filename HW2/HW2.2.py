from typing import Optional
from pydantic import BaseModel


class NestedDataModel(BaseModel):
    data: str
    child: Optional['NestedDataModel'] = None


def get_recursive_model():
    return NestedDataModel


if __name__ == "__main__":
    raw_json = {
        "data": "level_1",
        "child": {
            "data": "level_2",
            "child": {
                "data": "level_3",
                "child": None
            }
        }
    }

    RecursiveModel = get_recursive_model()
    instance = RecursiveModel(**raw_json)

    print("\nРекурсивная модель успешно создана:")
    print(instance.model_dump_json(indent=4))