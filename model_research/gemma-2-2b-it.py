import os

import pandas as pd
import torch
from transformers import pipeline
from datasets import load_dataset
from evaluate import load
from tqdm import tqdm
import pytesseract
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("HUGGING_FACE_TOKEN")
model_name = "google/gemma-2-2b-it"
task = "text-generation"

dataset = load_dataset("nielsr/docvqa_1200_examples_donut", split="train[:5%]")
print("Sample data:", dataset[0])
print("Question:", dataset[0]['query']['en'])
print("Answer:", dataset[0]['answer']['text'])
metric = load("rouge")

def evaluate_qa(model_name, dataset):
    print("Start evaluating QA")
    pipe = pipeline(
        task,
        model=model_name,
        model_kwargs={"torch_dtype": torch.bfloat16},
        device_map="auto",
        token=token
    )
    pipe.model.eval()

    references = []
    answers = []

    for data in tqdm(dataset, total=len(dataset)):
        image = data['image']
        question = data['query']['en']
        text = pytesseract.image_to_string(image)

        message = [
            {"role": "user", "content": f"너는 주어진 Context를 이용해서 사용자의 질문에 대답해주는 질의응답 어시스턴트야. You are a assistant that helps users by using given Context.\n\nContext: {text}\nQuestion: {question}\n"}
        ]

        prompt = pipe.tokenizer.apply_chat_template(
            message,
            tokenize=False,
            add_generation_prompt=True
        )

        terminators = [
            pipe.tokenizer.eos_token_id,
            pipe.tokenizer.convert_tokens_to_ids("<end_of_turn>")
        ]

        answer = pipe(
            prompt,
            max_new_tokens=2048,
            eos_token_id=terminators,
            do_sample=True,
            temperature=0.3,
            top_p=0.9
        )
        print("answer:", answer[0]['generated_text'][len(prompt):])

        answers.append(answer[0]['generated_text'][len(prompt):])
        references.append(data['answer']['text'])

    df = pd.DataFrame(list(zip(answers, references)), columns=['Question-Answering', 'Answer'])
    print("Processing to make dataframe to csv...")
    df.to_csv(f'./{model_name.split("/")[0]}.csv')
    print("Process completed.")
    score = metric.compute(predictions=answers, references=references)

    return score

score = evaluate_qa(model_name, dataset)
print("Model:", model_name)
print("Score:", score)
with open(f"{model_name.split('/')[0]}.txt", "w") as f:
    f.write(f"{score}")
print(f"Complete to save {model_name} rouge score in {model_name.split('/')[0]}.txt")