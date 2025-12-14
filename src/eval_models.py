import json
from textblob import TextBlob
from transformers import pipeline
import pandas as pd
from sklearn.metrics import mean_absolute_error, accuracy_score

def load_golden_set():
    with open("golden_set.json", "r") as f:
        return json.load(f)

def eval_textblob(data):
    predictions = []
    for item in data:
        # TextBlob is -1 to 1. Map to 1-5 scale roughly.
        # -1 -> 1, -0.5 -> 2, 0 -> 3, 0.5 -> 4, 1 -> 5
        score = TextBlob(item['text']).sentiment.polarity
        
        if score <= -0.5: pred = 1
        elif score < 0: pred = 2
        elif score == 0: pred = 3
        elif score < 0.5: pred = 4
        else: pred = 5
        
        predictions.append(pred)
    return predictions

def eval_hf_bert(data, model_name="nlptown/bert-base-multilingual-uncased-sentiment"):
    print(f"Loading {model_name}...")
    sentiment_pipeline = pipeline("sentiment-analysis", model=model_name)
    predictions = []
    
    for item in data:
        # Returns [{'label': '5 stars', 'score': 0.99}]
        result = sentiment_pipeline(item['text'][:512])[0] # Truncate to 512 tokens
        label = result['label']
        # Extract number from "5 stars"
        stars = int(label.split()[0])
        predictions.append(stars)
        
    return predictions

def main():
    data = load_golden_set()
    y_true = [item['label'] for item in data]
    
    results = {}
    
    # 1. TextBlob
    print("Evaluating TextBlob...")
    y_pred_tb = eval_textblob(data)
    results['TextBlob'] = mean_absolute_error(y_true, y_pred_tb)
    
    # 2. BERT (nlptown) - trained on reviews (1-5 stars)
    print("Evaluating BERT (nlptown)...")
    try:
        y_pred_bert = eval_hf_bert(data, "nlptown/bert-base-multilingual-uncased-sentiment")
        results['BERT (nlptown)'] = mean_absolute_error(y_true, y_pred_bert)
    except Exception as e:
        print(f"BERT Failed: {e}")

def eval_roberta(data, model_name="cardiffnlp/twitter-roberta-base-sentiment"):
    print(f"Loading {model_name}...")
    # This model outputs LABEL_0 (Negative), LABEL_1 (Neutral), LABEL_2 (Positive)
    sentiment_pipeline = pipeline("sentiment-analysis", model=model_name)
    predictions = []
    
    for item in data:
        result = sentiment_pipeline(item['text'][:512])[0]
        label = result['label']
        
        # Map labels to 1-5 stars roughly
        if label == "LABEL_0": # Negative
            pred = 1
        elif label == "LABEL_1": # Neutral
            pred = 3
        else: # Positive
            pred = 5
            
        predictions.append(pred)
    return predictions

def main():
    data = load_golden_set()
    y_true = [item['label'] for item in data]
    
    results = {}
    
    # 1. TextBlob
    print("Evaluating TextBlob...")
    y_pred_tb = eval_textblob(data)
    results['TextBlob'] = mean_absolute_error(y_true, y_pred_tb)
    
    # 2. BERT (nlptown)
    print("Evaluating BERT (nlptown)...")
    try:
        y_pred_bert = eval_hf_bert(data, "nlptown/bert-base-multilingual-uncased-sentiment")
        results['BERT (nlptown)'] = mean_absolute_error(y_true, y_pred_bert)
    except Exception as e:
        print(f"BERT Failed: {e}")

    # 3. RoBERTa (Twitter)
    print("Evaluating RoBERTa (Twitter)...")
    try:
        y_pred_roberta = eval_roberta(data)
        results['RoBERTa (Twitter)'] = mean_absolute_error(y_true, y_pred_roberta)
    except Exception as e:
        print(f"RoBERTa Failed: {e}")

    print("\n--- RESULTS (Mean Absolute Error - Lower is Better) ---")
    df = pd.DataFrame(list(results.items()), columns=['Model', 'MAE'])
    print(df.sort_values('MAE'))
    
    print("\nDetailed Predictions (RoBERTa):")
    for i, item in enumerate(data):
        print(f"Text: {item['text'][:30]}... | True: {y_true[i]} | Pred: {y_pred_roberta[i]}")

if __name__ == "__main__":
    main()

