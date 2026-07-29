import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class NewsSentimentAnalyzer:
    def __init__(self, model_name="ProsusAI/finbert"):
        print(f"Loading Sentiment Model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        # FinBERT labels: 0: positive, 1: negative, 2: neutral
        self.labels = ["positive", "negative", "neutral"]

    def analyze_headlines(self, news_items):
        """
        Analyzes a list of news dictionaries (from web_search) 
        and returns the overall sentiment score.
        """
        if not news_items:
            return {"overall_sentiment": "neutral", "score": 0.0, "details": []}

        texts = [item.get('title', '') + ". " + item.get('body', '') for item in news_items]
        
        inputs = self.tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)

        results = []
        total_score = 0.0 # scale: -1 (negative) to 1 (positive)

        for i, text in enumerate(texts):
            probs = predictions[i].tolist()
            pos_prob = probs[0]
            neg_prob = probs[1]
            neu_prob = probs[2]
            
            # Simple scoring mechanism
            score = pos_prob - neg_prob
            total_score += score
            
            sentiment = self.labels[torch.argmax(predictions[i]).item()]
            
            results.append({
                "text": texts[i][:100] + "...",
                "sentiment": sentiment,
                "score": score,
                "probabilities": {"positive": pos_prob, "negative": neg_prob, "neutral": neu_prob}
            })

        avg_score = total_score / len(texts)
        
        if avg_score > 0.2:
            overall = "bullish"
        elif avg_score < -0.2:
            overall = "bearish"
        else:
            overall = "neutral"

        return {
            "overall_sentiment": overall,
            "average_score": avg_score,
            "details": results
        }

if __name__ == "__main__":
    pass
